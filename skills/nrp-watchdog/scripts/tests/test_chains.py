#!/usr/bin/env python3
"""Tests for nrp-watchdog chains. No cluster, no S3, no notification, no model: a fake kubectl / aws / osascript / claude
sit first on PATH and a scratch state dir is used (NRP_WATCHDOG_STATE). Run: python3 test_chains.py
Versioned in braindance_proj/tools/nrp-watchdog; install.sh copies the script to ~/.local/bin."""
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SCRIPT = os.environ.get("WATCHDOG", str(HERE / "nrp-watchdog"))    # the versioned copy; WATCHDOG=~/.local/bin/nrp-watchdog tests the installed one
REAL_TPL = HERE / "templates"
USER = "http://cilogon.org/serverE/users/100000"

FAKE_KUBECTL = r'''#!/usr/bin/env python3
import json, os, sys, time
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fake"); a = sys.argv[1:]
if os.path.exists(d + "/kube_fail"):
    sys.stderr.write("Unable to connect to the server\n"); sys.exit(1)
cl = json.load(open(d + "/cluster.json"))
open(d + "/kubectl.log", "a").write(" ".join(a) + "\n")
if a[:2] == ["-n", a[1]]: a = a[2:]
def save(): json.dump(cl, open(d + "/cluster.json", "w"))
if a[:2] == ["get", "jobs"]:
    items = []
    for n, j in cl["jobs"].items():
        m = {"name": n}
        if j.get("ann", True): m["annotations"] = {"nrp.ai/username": "http://cilogon.org/serverE/users/100000"}
        st = {"ok": {"succeeded": 1}, "FAILED": {"failed": 1}, "running": {"active": 1}, "pending": {}}[j["state"]]
        st = dict(st)
        if "succeeded" in j: st["succeeded"] = j["succeeded"]                  # partial Indexed Job: running pods + finished shards
        if j.get("start"): st["startTime"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(j["start"]))
        items.append({"metadata": m, "status": st, "spec": {"completions": j["completions"]} if "completions" in j else {}})
    print(json.dumps({"items": items}))
elif a[:2] == ["get", "pods"]:
    print(json.dumps({"items": []}))
elif a[:2] == ["get", "job"]:
    j = cl["jobs"].get(a[2])
    if not j: sys.stderr.write('Error from server (NotFound): jobs "%s" not found\n' % a[2]); sys.exit(1)
    print("{}/{}/{}/{}/".format(j.get("succeeded", 1 if j["state"] == "ok" else ""), 1 if j["state"] == "FAILED" else "", 1 if j["state"] == "running" else "", j.get("completions", "")), end="")
elif a[0] == "logs":
    print("fake log line 1 for %s\nfake log line 2" % a[1])
elif a[0] == "describe":
    print("fake describe " + " ".join(a[1:]))
elif a[0] == "delete":
    n = a[2]
    if n in cl["jobs"]:
        del cl["jobs"][n]; save(); open(d + "/deleted.log", "a").write(n + "\n")
    else:
        sys.stderr.write('Error from server (NotFound): jobs "%s" not found\n' % n); sys.exit(1)
else:
    sys.stderr.write("fake kubectl: unsupported %s\n" % a); sys.exit(2)
'''
FAKE_AWS = r'''#!/usr/bin/env python3
import json, os, sys
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fake"); a = sys.argv[1:]
if os.path.exists(d + "/aws_fail"): sys.stderr.write("could not connect\n"); sys.exit(255)
if "head-object" in sys.argv:                                          # exact object check (what the watchdog uses)
    u = "s3://%s/%s" % (a[a.index("--bucket") + 1], a[a.index("--key") + 1])
    open(d + "/aws.log", "a").write(" ".join(a) + "\n")
    if os.path.exists(d + "/aws_fail"): sys.stderr.write("Could not connect to the endpoint URL\n"); sys.exit(255)
    if os.path.exists(d + "/aws_403"): sys.stderr.write("An error occurred (403) when calling the HeadObject operation: Forbidden\n"); sys.exit(254)
    if os.path.exists(d + "/aws_garbage"): print("<html>proxy page</html>"); sys.exit(0)
    if u in json.load(open(d + "/s3.json")): print(json.dumps({"ETag": '"x"', "ContentLength": 0})); sys.exit(0)   # EXACT, never a prefix
    sys.stderr.write("An error occurred (404) when calling the HeadObject operation: Not Found\n"); sys.exit(254)
uri = a[-1]
have = json.load(open(d + "/s3.json"))
open(d + "/aws.log", "a").write(" ".join(a) + "\n")
if any(h.startswith(uri) for h in have): print("2026-11-04 12:00:00 1234 " + uri.split("/")[-1]); sys.exit(0)
sys.exit(1)
'''
FAKE_SUBMIT = r'''#!/usr/bin/env python3
"""fake nrp/submit.py: --job NAME [--rc N] [--sleep S] [--apply]. Without --apply it only prints (like the real one)."""
import json, os, sys, time
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fake"); a = sys.argv[1:]
job = a[a.index("--job") + 1]
if "--apply" not in a:
    print("dry run: add --apply to submit", file=sys.stderr); sys.exit(0)
if "--sleep" in a: time.sleep(float(a[a.index("--sleep") + 1]))
open(d + "/submits.log", "a").write(job + " cwd=" + os.getcwd() + " leak=" + str("AWS_SECRET_ACCESS_KEY" in os.environ) + "\n")
if "--rc" in a:
    print("boom: image missing", file=sys.stderr); sys.exit(int(a[a.index("--rc") + 1]))
cl = json.load(open(d + "/cluster.json")); cl["jobs"][job] = {"state": "running", "ann": False, "start": time.time()}
json.dump(cl, open(d + "/cluster.json", "w")); print("submitted Job " + job)
'''
FAKE_OSA = '#!/bin/sh\nD="$(dirname "$0")/../fake"\necho "$@" >> "$D/notifications.log"\n'
FAKE_CLAUDE = ('#!/bin/sh\nD="$(dirname "$0")/../fake"\ncat > "$D/claude_prompt_$$.txt"\necho "$@" >> "$D/claude_args.log"\n'
               'if [ -f "$D/claude_out" ]; then cat "$D/claude_out"; else echo "ok: fake agent done"; fi\n')


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wdtest_"))
        self.fake, self.state, self.work = self.tmp / "fake", self.tmp / "state", self.tmp / "work"
        for p in (self.fake, self.state, self.work, self.tmp / "bin"):
            p.mkdir()
        for n, body in (("kubectl", FAKE_KUBECTL), ("aws", FAKE_AWS), ("osascript", FAKE_OSA), ("claude", FAKE_CLAUDE)):
            (self.tmp / "bin" / n).write_text(body)
            os.chmod(self.tmp / "bin" / n, 0o755)
        (self.work / "submit.py").write_text(FAKE_SUBMIT)
        shutil.copytree(REAL_TPL, self.state / "templates")
        self.cluster({})
        (self.fake / "s3.json").write_text("[]")
        self.env = {"PATH": "%s:/usr/bin:/bin" % (self.tmp / "bin"), "HOME": str(Path.home()), "FAKE_DIR": str(self.fake),
                    "FAKE_USER": USER, "NRP_WATCHDOG_USER_ANNOTATION": USER, "NRP_WATCHDOG_STATE": str(self.state), "NRP_WATCHDOG_POLL_S": "1",
                    "AWS_SECRET_ACCESS_KEY": "must-not-leak", "NRP_WATCHDOG_NO_PUSH": "1",
                    "NRP_WATCHDOG_SLACK_URL": "http://127.0.0.1:9/never"}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # helpers
    def wd(self, *args, env=None, timeout=120):
        e = dict(self.env, **(env or {}))
        r = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, env=e, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()

    def cluster(self, jobs):
        (self.fake / "cluster.json").write_text(json.dumps({"jobs": jobs}))

    def set_job(self, name, state, **kw):
        cl = json.loads((self.fake / "cluster.json").read_text())
        cl["jobs"][name] = dict(cl["jobs"].get(name, {}), state=state, **kw)
        (self.fake / "cluster.json").write_text(json.dumps(cl))

    def digest(self):
        p = self.state / "digest.log"
        return p.read_text().splitlines() if p.exists() else []

    def jobs_in_cluster(self):
        return json.loads((self.fake / "cluster.json").read_text())["jobs"]

    def s3(self, *uris):
        (self.fake / "s3.json").write_text(json.dumps(list(uris)))

    def lines(self, name):
        p = self.fake / name
        return p.read_text().splitlines() if p.exists() else []

    def step(self, sid, job, after=(), **kw):
        d = {"id": sid, "job": job, "cwd": str(self.work), "after": list(after),
             "argv": [sys.executable, str(self.work / "submit.py"), "--job", job, "--apply"]}
        d.update(kw)
        return d

    def add(self, name, steps, **kw):
        spec = dict({"name": name, "owner": "test " + name, "notes": "notes for " + name, "steps": steps}, **kw)
        f = self.tmp / (name + ".json")
        f.write_text(json.dumps(spec))
        return self.wd("chain", "add", str(f))

    def chain(self, name):
        return json.loads((self.state / "chains" / name / "chain.json").read_text())

    def states(self, name):
        return {s["id"]: s["state"] for s in self.chain(name)["steps"]}

    def run_pass(self, n=1, **kw):
        for _ in range(n):
            rc, out, err = self.wd("run", **kw)
            self.assertEqual(rc, 0, err)


class TestChains(Base):
    def test_dag_success(self):
        rc, out, err = self.add("dag", [self.step("plain", "j-plain", done_s3=["s3://b/out/plain.npz"]),
                                        self.step("emb", "j-emb"),
                                        self.step("rc", "j-rc", after=["plain", "emb"], done_s3=["s3://b/out/rc.json"])])
        self.assertEqual(rc, 0, err)
        self.run_pass()
        self.assertEqual(self.states("dag"), {"plain": "running", "emb": "running", "rc": "pending"})
        self.assertEqual(sorted(self.jobs_in_cluster()), ["j-emb", "j-plain"])
        self.assertTrue(all("leak=False" in l for l in self.lines("submits.log")), "secret env leaked to a step")
        self.s3("s3://b/out/plain.npz")
        self.set_job("j-plain", "ok")
        self.run_pass()                                   # plain done, emb still running, rc still waits
        self.assertEqual(self.states("dag"), {"plain": "done", "emb": "running", "rc": "pending"})
        self.assertIn("j-plain", self.lines("deleted.log"))
        log = self.state / "chains/dag/logs/plain.txt"
        self.assertIn("fake log line 1 for job/j-plain", log.read_text())
        self.assertIn("fake describe job j-plain", log.read_text())
        self.set_job("j-emb", "ok")
        self.run_pass()
        self.assertEqual(self.states("dag")["rc"], "running")
        self.assertEqual(self.wd("chain", "wait", "dag", "-m", "2")[0], 3)
        self.s3("s3://b/out/plain.npz", "s3://b/out/rc.json")
        self.set_job("j-rc", "ok")
        self.run_pass()
        self.assertEqual(self.chain("dag")["status"], "finished")
        self.assertEqual(self.wd("chain", "wait", "dag")[0], 0)
        self.assertEqual(sorted(self.lines("deleted.log")), ["j-emb", "j-plain", "j-rc"])
        self.assertEqual(sorted(l.split()[0] for l in self.lines("submits.log")), ["j-emb", "j-plain", "j-rc"])
        self.assertTrue(any("FINISHED" in l for l in self.digest()))
        self.assertFalse(any("FINISHED" in l for l in self.lines("notifications.log")), "success is silent")
        self.assertEqual(self.jobs_in_cluster(), {})
        self.run_pass(2)                                  # a finished chain is never touched again
        self.assertEqual(len(self.lines("submits.log")), 3)

    def test_failure_stops_no_retry_then_resume(self):
        self.add("f", [self.step("a", "j-a"), self.step("b", "j-b", after=["a"]), self.step("c", "j-c", after=["b"])])
        self.run_pass()
        self.set_job("j-a", "ok")
        self.run_pass()
        self.assertEqual(self.states("f"), {"a": "done", "b": "running", "c": "pending"})
        self.set_job("j-b", "FAILED")
        self.run_pass()
        ch = self.chain("f")
        self.assertEqual(ch["status"], "stopped")
        self.assertEqual(self.states("f")["b"], "failed")
        self.assertIn("FAILED", ch["reason"])
        self.assertIn("fake log line 1 for job/j-b", (self.state / "chains/f/logs/b.txt").read_text())
        self.assertIn("j-b", self.jobs_in_cluster(), "failed Job must be left in the cluster")
        self.assertEqual(self.wd("chain", "wait", "f")[0], 1)
        nsub = len(self.lines("submits.log"))
        self.run_pass(3)
        self.assertEqual(len(self.lines("submits.log")), nsub, "no automatic retry")
        self.assertEqual(sum("STOPPED" in l for l in self.lines("notifications.log")), 1, "notify once")
        # a person decides: retry b with an edited deadline
        rc, out, err = self.wd("chain", "resume", "f", "--edit-step", "b", "deadline_s=7200")
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.chain("f")["steps"][1]["deadline_s"], 7200)
        self.run_pass()                                   # deletes the old failed Job by name
        self.assertIn("j-b", self.lines("deleted.log"))
        self.run_pass()                                   # resubmits
        self.assertEqual(self.jobs_in_cluster()["j-b"]["state"], "running")
        self.set_job("j-b", "ok")
        self.run_pass(2)
        self.set_job("j-c", "ok")
        self.run_pass()
        self.assertEqual(self.chain("f")["status"], "finished")

    def test_resume_skip(self):
        self.add("sk", [self.step("a", "j-a"), self.step("b", "j-b", after=["a"])])
        self.run_pass()
        self.set_job("j-a", "FAILED")
        self.run_pass()
        self.assertEqual(self.wd("chain", "resume", "sk", "--skip", "a")[0], 0)
        self.run_pass()
        self.assertEqual(self.states("sk"), {"a": "done", "b": "running"})

    def test_missing_s3_output_stops_and_keeps_job(self):
        self.add("m", [self.step("a", "j-a", done_s3=["s3://b/needed.json"])])
        self.run_pass()
        self.set_job("j-a", "ok")
        self.run_pass()
        self.assertEqual(self.chain("m")["status"], "stopped")
        self.assertIn("needed.json", self.chain("m")["reason"])
        self.assertIn("j-a", self.jobs_in_cluster())
        self.assertEqual(self.lines("deleted.log"), [])
        self.assertTrue((self.state / "chains/m/logs/a.txt").exists())

    def test_s3_tool_error_is_retried_not_fatal(self):
        self.add("e", [self.step("a", "j-a", done_s3=["s3://b/x.json"])])
        self.run_pass()
        self.set_job("j-a", "ok")
        (self.fake / "aws_fail").write_text("")
        self.run_pass(2)
        self.assertEqual(self.chain("e")["status"], "active")
        self.assertIn("j-a", self.jobs_in_cluster())
        (self.fake / "aws_fail").unlink()
        self.s3("s3://b/x.json")
        self.run_pass()
        self.assertEqual(self.chain("e")["status"], "finished")

    def test_manual_gate_then_resume(self):
        self.add("g", [self.step("a", "j-a"), self.step("b", "j-b", after=["a"], gate="manual")])
        self.run_pass()
        self.set_job("j-a", "ok")
        self.run_pass()
        ch = self.chain("g")
        self.assertEqual(ch["status"], "gated")
        self.assertEqual(self.states("g")["b"], "pending")
        self.assertEqual(self.wd("chain", "wait", "g")[0], 4)
        self.run_pass(2)
        self.assertEqual(sum("GATED" in l for l in self.lines("notifications.log")), 1)
        self.assertEqual(self.lines("submits.log").__len__(), 1)
        self.assertEqual(self.wd("chain", "resume", "g")[0], 0)
        self.run_pass()
        self.assertEqual(self.states("g")["b"], "running")
        self.assertEqual(self.chain("g")["status"], "active")

    def test_crash_in_submitting_adopt_and_fail(self):
        self.add("c1", [self.step("a", "j-exists"), self.step("b", "j-gone")])
        p = self.state / "chains/c1/chain.json"
        ch = json.loads(p.read_text())
        for s in ch["steps"]:
            s["state"] = "submitting"                     # as if killed right after saving "submitting"
        p.write_text(json.dumps(ch))
        self.set_job("j-exists", "running", ann=False)
        self.run_pass()
        self.assertEqual(self.states("c1")["a"], "running")
        self.assertTrue(self.chain("c1")["steps"][0].get("adopted"))
        self.assertEqual(self.states("c1")["b"], "failed")
        self.assertEqual(self.chain("c1")["status"], "stopped")
        self.assertEqual(self.lines("submits.log"), [], "never double-submit")
        # after a person resumes, the failed step is submitted once
        self.wd("chain", "resume", "c1")
        self.run_pass()
        self.assertEqual([l.split()[0] for l in self.lines("submits.log")], ["j-gone"])

    def test_submit_command_failure(self):
        s = self.step("a", "j-a")
        s["argv"] += ["--rc", "3"]
        self.add("sf", [s])
        self.run_pass()
        ch = self.chain("sf")
        self.assertEqual(ch["status"], "stopped")
        self.assertIn("submit exited 3", ch["reason"])
        self.assertIn("boom", (self.state / "chains/sf/logs/a.submit.txt").read_text())
        self.assertEqual(self.jobs_in_cluster(), {})

    def test_job_cap(self):
        # one of ours (unfinished) already in the cluster + two of a foreign annotation-less kind that must not count
        self.set_job("other-mine", "running", ann=True)
        self.set_job("someone-else", "running", ann=False)
        self.add("cap", [self.step(str(i), "j-%d" % i) for i in range(4)])
        self.run_pass(env={"NRP_WATCHDOG_MAX_JOBS": "3"})
        sub = [l.split()[0] for l in self.lines("submits.log")]
        self.assertEqual(len(sub), 2, sub)                # 1 existing + 2 new == 3
        self.run_pass(env={"NRP_WATCHDOG_MAX_JOBS": "3"})
        self.assertEqual(len(self.lines("submits.log")), 2)
        self.set_job("j-%s" % sub[0][-1], "ok")           # frees one slot (and is then deleted)
        self.run_pass(env={"NRP_WATCHDOG_MAX_JOBS": "3"})
        self.assertEqual(len(self.lines("submits.log")), 3)

    def shared_policy(self, **kw):
        f = self.tmp / "shared-policy.json"
        f.write_text(json.dumps(dict({"gpu_floor": 0.4, "limit_to_request_tolerance": 0.2, "max_concurrent_jobs": 400}, **kw)))
        return {"NRP_UTIL_POLICY": str(f)}

    def local_policy(self, **kw):
        (self.state / "utilization-policy.local.json").write_text(json.dumps(kw))

    def fill(self, n):
        for i in range(n):
            self.set_job("mine-%d" % i, "running")

    def test_default_cap_is_the_shared_400_not_40(self):
        env = self.shared_policy()
        self.fill(40)
        self.add("cap40", [self.step("a", "j-a")])
        self.run_pass(env=env)
        self.assertEqual(len(self.lines("submits.log")), 1, "40 unfinished Jobs no longer block: the shared cap is 400")

    def test_cap_comes_from_the_shared_policy(self):
        env = self.shared_policy(max_concurrent_jobs=5)
        self.fill(5)
        self.add("cap5", [self.step("a", "j-a")])
        self.run_pass(env=env)
        self.assertEqual(self.lines("submits.log"), [])
        self.set_job("mine-0", "ok")
        self.run_pass(env=env)
        self.assertEqual(len(self.lines("submits.log")), 1)

    def test_local_override_lowers_the_cap(self):
        env = self.shared_policy()
        self.local_policy(max_concurrent_jobs=40, lab_floor=0.4)       # the owner's own rules, default location in the state dir
        self.fill(40)
        self.add("cap40", [self.step("a", "j-a")])
        self.run_pass(env=env)
        self.assertEqual(self.lines("submits.log"), [])
        self.set_job("mine-0", "ok")
        self.run_pass(env=env)
        self.assertEqual(len(self.lines("submits.log")), 1)

    def test_local_override_cannot_raise_the_cap(self):
        env = self.shared_policy(max_concurrent_jobs=5)
        self.local_policy(max_concurrent_jobs=50)
        self.fill(5)
        self.add("cap5", [self.step("a", "j-a")])
        self.run_pass(env=env)
        self.assertEqual(self.lines("submits.log"), [], "a local value above the shared cap is ignored")
        self.assertIn("would loosen the shared 5", (self.state / "watchdog.log").read_text())

    def test_env_can_lower_the_cap_further(self):
        env = dict(self.shared_policy(), NRP_WATCHDOG_MAX_JOBS="2")
        self.fill(2)
        self.add("cap2", [self.step("a", "j-a")])
        self.run_pass(env=env)
        self.assertEqual(self.lines("submits.log"), [])
        env["NRP_WATCHDOG_MAX_JOBS"] = "9999"                            # env cannot loosen either
        self.run_pass(env=dict(env, NRP_UTIL_POLICY=self.shared_policy(max_concurrent_jobs=2)["NRP_UTIL_POLICY"]))
        self.assertEqual(self.lines("submits.log"), [])

    def test_lock_held_means_noop(self):
        self.add("lk", [self.step("a", "j-a")])
        lock = open(self.state / "lock", "w")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.run_pass()
        self.assertEqual(self.lines("submits.log"), [])
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
        self.run_pass()
        self.assertEqual(len(self.lines("submits.log")), 1)

    def test_simultaneous_passes_submit_once(self):
        s = self.step("a", "j-a")
        s["argv"] += ["--sleep", "2"]
        self.add("dup", [s, self.step("b", "j-b")])
        e = dict(self.env)
        ps = [subprocess.Popen([sys.executable, SCRIPT, "run"], env=e, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(3)]
        for p in ps:
            p.communicate(timeout=60)
        self.assertEqual(sorted(l.split()[0] for l in self.lines("submits.log")), ["j-a", "j-b"])

    def test_wait_codes_and_stall(self):
        self.assertEqual(self.wd("chain", "wait", "nope")[0], 2)
        self.add("w", [self.step("a", "j-a")])
        self.run_pass()
        rc, out, _ = self.wd("chain", "wait", "w", "-m", "2")
        self.assertEqual(rc, 3, out)
        self.assertEqual(out.count("\n"), 0)
        self.assertEqual(sum(1 for l in self.lines("kubectl.log") if "wait" in l), 0)
        # heartbeat stale and chain old: STALLED
        old = time.time() - 3 * 3600
        os.utime(self.state / "heartbeat", (old, old))
        p = self.state / "chains/w/chain.json"
        ch = json.loads(p.read_text())
        ch["created"] = old
        p.write_text(json.dumps(ch))
        rc, out, _ = self.wd("chain", "wait", "w", "-m", "5")
        self.assertEqual(rc, 5, out)
        self.assertEqual(self.wd("chain", "cancel", "w")[0], 0)
        self.assertEqual(self.wd("chain", "wait", "w")[0], 1)

    def test_wait_is_woken_by_run(self):
        self.add("ww", [self.step("a", "j-a")])
        self.run_pass()
        w = subprocess.Popen([sys.executable, SCRIPT, "chain", "wait", "ww"], env=self.env, stdout=subprocess.PIPE, text=True)
        time.sleep(1.5)
        self.assertIsNone(w.poll())
        self.set_job("j-a", "ok")
        self.run_pass()
        out, _ = w.communicate(timeout=30)
        self.assertEqual(w.returncode, 0)
        self.assertTrue(out.startswith("FINISHED"))

    def test_deadline_overrun(self):
        self.add("dl", [self.step("a", "j-a", deadline_s=600)])
        self.run_pass()
        self.set_job("j-a", "running", start=time.time() - 3600)
        self.run_pass()
        ch = self.chain("dl")
        self.assertEqual(ch["status"], "stopped")
        self.assertIn("deadline", ch["reason"])
        self.assertIn("j-a", self.jobs_in_cluster(), "an overrunning Job is not deleted")
        self.assertEqual(self.states("dl")["a"], "running")
        self.run_pass(2)
        self.assertEqual(sum("STOPPED" in l for l in self.lines("notifications.log")), 1)

    def test_adopt_existing_running_and_done_steps(self):
        self.set_job("j-a", "ok")
        self.set_job("j-b", "running")
        self.add("ad", [self.step("a", "j-a", state="done"), self.step("b", "j-b", after=["a"], state="running"),
                        self.step("c", "j-c", after=["b"])])
        self.run_pass()
        self.assertEqual(self.lines("submits.log"), [], "adopted steps are never submitted")
        self.assertEqual(self.states("ad"), {"a": "done", "b": "running", "c": "pending"})
        self.set_job("j-b", "ok")
        self.run_pass()
        self.assertEqual(self.states("ad")["c"], "running")

    def test_on_finish_agent_once(self):
        self.add("ag", [self.step("a", "j-a")], on_finish="agent", followup="Run the scorer and report counts.")
        self.run_pass()
        self.set_job("j-a", "ok")
        self.run_pass(3)
        prompts = list(self.fake.glob("claude_prompt_*.txt"))
        self.assertEqual(len(prompts), 1)
        t = prompts[0].read_text()
        self.assertIn("notes for ag", t)
        self.assertIn("Run the scorer", t)
        self.assertIn("chains/ag/logs", t)
        self.assertLess(len(t), 6000)

    def test_kubectl_down_changes_nothing(self):
        self.add("kd", [self.step("a", "j-a")])
        (self.fake / "kube_fail").write_text("")
        self.run_pass(2)
        self.assertEqual(self.lines("submits.log"), [])
        self.assertEqual(self.states("kd")["a"], "pending")
        self.assertEqual(json.loads((self.state / "jobs.json").read_text())["kube_errors"], 2)
        (self.fake / "kube_fail").unlink()
        self.run_pass()
        self.assertEqual(len(self.lines("submits.log")), 1)

    def test_heartbeat_and_status(self):
        rc, out, _ = self.wd("status")
        self.assertEqual(rc, 0, out)                      # nothing active, no heartbeat: fine
        self.add("hb", [self.step("a", "j-a")])
        rc, out, _ = self.wd("status")
        self.assertEqual(rc, 3)
        self.assertIn("WARNING", out)
        self.run_pass()
        self.assertTrue((self.state / "heartbeat").read_text().startswith("20"))
        self.assertEqual(self.wd("status")[0], 0)
        self.assertEqual(self.wd("status", "--quiet")[1], "")
        old = time.time() - 40 * 60
        os.utime(self.state / "heartbeat", (old, old))
        rc, out, _ = self.wd("status", "--quiet")
        self.assertEqual(rc, 3)
        self.assertIn("40 min", out)
        self.wd("chain", "cancel", "hb")
        self.assertEqual(self.wd("status")[0], 0)         # stale but idle

    def test_show_list(self):
        self.add("sl", [self.step("a", "j-a")])
        self.run_pass()
        rc, out, _ = self.wd("chain", "list")
        self.assertIn("sl", out)
        rc, out, _ = self.wd("chain", "show", "sl")
        self.assertIn("j-a", out)
        self.assertIn("running", out)


class TestValidationAndResume(Base):
    def test_cwd_under_desktop_refused(self):
        s = self.step("a", "j-a", cwd=str(Path.home() / "Desktop"))
        rc, out, err = self.add("bad", [s])
        self.assertNotEqual(rc, 0)
        self.assertIn("TCC", err + out)
        self.assertFalse((self.state / "chains/bad").exists())

    def test_validation_problems(self):
        for steps, needle in (([self.step("a", "j-a", after=["zz"])], "unknown step"),
                              ([self.step("a", "j-a", after=["b"]), self.step("b", "j-b", after=["a"])], "cycle"),
                              ([self.step("a", "Bad_Name")], "DNS-1123"),
                              ([self.step("a", "j-a"), self.step("a", "j-b")], "duplicate id"),
                              ([self.step("a", "j-a", done_s3=["http://x"])], "done_s3"),
                              ([self.step("a", "j-a", gate="auto")], "gate"),
                              ([self.step("a", "j-a", deadline_s=-5)], "deadline_s"),
                              ([self.step("a", "j-a", cwd=str(self.tmp / "nope"))], "not a directory")):
            rc, out, err = self.add("v", steps)
            self.assertNotEqual(rc, 0, needle)
            self.assertIn(needle, err + out)
        rc, out, err = self.add("v", [self.step("a", "j-a")], notes="x" * 21000)
        self.assertIn("notes", err)

    def test_duplicate_name_and_job_refused(self):
        self.assertEqual(self.add("d1", [self.step("a", "j-a")])[0], 0)
        self.assertNotEqual(self.add("d1", [self.step("a", "j-z")])[0], 0)
        rc, out, err = self.add("d2", [self.step("a", "j-a")])
        self.assertNotEqual(rc, 0)
        self.assertIn("already belong", err)

    def test_spec_copied_into_state(self):
        self.add("cp", [self.step("a", "j-a")])
        (self.tmp / "cp.json").unlink()
        self.assertTrue((self.state / "chains/cp/spec.original.json").exists())
        self.run_pass()
        self.assertEqual(len(self.lines("submits.log")), 1)

    def test_dry_run_strips_apply_and_never_applies(self):
        f = self.tmp / "dr.json"
        f.write_text(json.dumps({"name": "dr", "steps": [self.step("a", "j-a"),
                                 {"id": "b", "job": "j-b", "cwd": str(self.work), "argv": ["/bin/echo", "no apply flag"], "after": ["a"]}]}))
        rc, out, err = self.wd("chain", "add", str(f), "--dry-run")
        self.assertEqual(rc, 0, out + err)
        self.assertIn("dry-run ok", out)
        self.assertIn("parse-only", out)
        self.assertEqual(self.lines("submits.log"), [], "dry run must not submit")
        self.assertFalse((self.state / "chains/dr").exists(), "dry run stores nothing")
        # failing dry run
        bad = self.step("a", "j-a")
        bad["argv"] = ["/bin/sh", "-c", "echo bad args >&2; exit 2", "--apply"]
        f.write_text(json.dumps({"name": "dr2", "steps": [bad]}))
        rc, out, _ = self.wd("chain", "add", str(f), "--dry-run")
        self.assertEqual(rc, 1)
        self.assertIn("DRY-RUN FAILED", out)

    def test_resume_size_refused_and_copied(self):
        big = self.tmp / "LOG.md"
        big.write_text("x" * (21 * 1024))
        rc, out, err = self.wd("add", "j-big", "--resume", str(big))
        self.assertNotEqual(rc, 0)
        self.assertIn("limit is 20 KB", err)
        self.assertFalse((self.state / "jobs.json").exists() and "j-big" in (self.state / "jobs.json").read_text())
        ok = self.tmp / "notes.md"
        ok.write_text("NOTES: score the output under s3://x/y")
        rc, out, err = self.wd("add", "j-small", "--resume", str(ok), "--label", "toy")
        self.assertEqual(rc, 0, err)
        ok.unlink()                                       # the Desktop original is gone / unreadable at run time
        self.set_job("j-small", "ok")
        (self.fake / "claude_out").write_text("DONE: outputs verified\n")
        rc, out, err = self.wd("run", "--fake-finished", "j-small")
        self.assertEqual(rc, 0, err)
        prompts = list(self.fake.glob("claude_prompt_*.txt"))
        self.assertEqual(len(prompts), 1)
        self.assertIn("score the output under s3://x/y", prompts[0].read_text())
        self.wd("run", "--fake-finished", "j-small")
        self.assertEqual(len(list(self.fake.glob("claude_prompt_*.txt"))), 1, "follow-up runs exactly once")
        self.assertEqual(json.loads((self.state / "jobs.json").read_text())["jobs"]["j-small"]["status"], "handled")

    def test_existing_job_check_notify_only(self):
        self.wd("add", "j-plain", "--label", "no resume")
        self.set_job("j-plain", "FAILED")
        self.run_pass()
        self.assertTrue(any("no resume FAILED" in l for l in self.digest()))
        self.assertEqual(list(self.fake.glob("claude_prompt_*.txt")), [])

    def test_existing_pod_path_dry_run(self):
        util = self.tmp / "util.txt"
        util.write_text("LOW pod-x age 20m, 10m mean: gpu 0% [NRP violation]\n")
        rc, out, err = self.wd("run", "--dry-run", "--fake-util", str(util))
        self.assertEqual(rc, 0, err)
        self.assertIn("[dry-run] nrp-util-check flagged 1 of your pods", out)

    # ---- pod-check strikes (Sam 2026-11-04: resources, not progress; 2nd flag in a row on an NRP violation -> delete)
    def pod_pass(self, flag, agent_says):
        util = self.tmp / "util.txt"
        util.write_text(flag + "\n" if flag else "")
        (self.fake / "claude_out").write_text(agent_says + "\n")
        for f in self.fake.glob("claude_prompt_*.txt"):
            f.unlink()
        rc, out, err = self.wd("run", "--fake-util", str(util))
        self.assertEqual(rc, 0, err)
        return [f.read_text() for f in self.fake.glob("claude_prompt_*.txt")]

    def age_last_check(self, pod, seconds):
        js = json.loads((self.state / "jobs.json").read_text())
        js["pods"][pod] -= seconds
        (self.state / "jobs.json").write_text(json.dumps(js))

    def strikes(self):
        return json.loads((self.state / "jobs.json").read_text()).get("strikes", {})

    FLAG_NRP = "LOW pod-x age 20m, 10m mean: mem 1.1/16.0Gi (7%, max 1.2) [NRP violation]"

    def test_strike_one_oversized_then_strike_two_delete(self):
        # v2 (Sam 2026-11-05): strike 1 is the script's job (resize recorded, silent); no agent
        prompts = self.pod_pass(self.FLAG_NRP, "unused")
        self.assertEqual(len(prompts), 0)
        self.assertIn("pod-x", self.strikes())
        self.assertIn("OVERSIZED: memory", (self.state / "resize.log").read_text())
        self.assertEqual(self.lines("notifications.log"), [], "strike 1 is silent")
        # next pass (10 min later) re-checks at strike 2 even though the 30-min dedupe has not passed
        self.age_last_check("pod-x", 600)
        prompts = self.pod_pass(self.FLAG_NRP, "DELETED: second NRP-violation flag; mem 16Gi peak 1.2Gi -> request 2Gi")
        self.assertEqual(len(prompts), 1)
        self.assertIn("strike: 2", prompts[0])
        self.assertIn("NEVER reasons to call a flagged pod fine", prompts[0])
        self.assertEqual(self.strikes(), {})
        self.assertEqual(len((self.state / "resize.log").read_text().splitlines()), 2)

    def test_account_alarm_needs_two_high_passes(self):
        # 2026-11-05 09:53: one pass saw "account 4" while 21 pods were a minute old, and the push named a lab-rule pod
        lab = "LOW pod-lab age 20m, 10m mean: mem 0.8/2.0Gi (39%, max 0.9) [lab 40% rule]"
        acct = "LOW checked 9 pods (1 low/stuck/failed); account: 4 of 9 running pods outside NRP bands"
        pushes = lambda: [json.loads(d)["msg"] for d in self.digest() if json.loads(d)["kind"] == "push"]
        self.pod_pass(lab + "\n" + acct, "unused")
        self.assertEqual(pushes(), [], "one high pass is not enough")
        self.age_last_check("pod-lab", 600)
        self.pod_pass(lab + "\n" + acct, "unused")
        self.assertEqual(len(pushes()), 1)
        self.assertIn("NRP counts 4", pushes()[0])
        self.assertNotIn("pod-lab", pushes()[0], "lab-rule pods are not NRP violations")
        self.pod_pass(lab + "\n" + acct, "unused")
        self.assertEqual(len(pushes()), 1, "pushed once")

    def test_strike_two_waits_for_next_pass(self):
        self.pod_pass(self.FLAG_NRP, "OVERSIZED: x")
        self.age_last_check("pod-x", 120)                 # a pass 2 min later (terminal loop) does not jump to strike 2
        self.assertEqual(self.pod_pass(self.FLAG_NRP, "DELETED: x"), [])
        self.assertIn("pod-x", self.strikes())

    def test_strike_resets_when_not_flagged(self):
        self.pod_pass(self.FLAG_NRP, "OVERSIZED: x")
        self.pod_pass("", "unused")
        self.assertEqual(self.strikes(), {})

    def test_strike_two_kept_is_loud(self):
        self.pod_pass(self.FLAG_NRP, "OVERSIZED: x")
        self.age_last_check("pod-x", 600)
        self.pod_pass(self.FLAG_NRP, "KEPT: command denied")
        self.assertTrue(any("not deleted at strike 2" in l for l in self.lines("notifications.log")))

    def test_resize_note_reaches_registered_resume(self):
        notes = self.tmp / "notes.md"
        notes.write_text("read the report\n")
        self.wd("add", "job-x", "--resume", str(notes))
        self.set_job("job-x", "running")
        js = json.loads((self.state / "jobs.json").read_text())
        st = {"strikes": {}, "jobs": js["jobs"], "pods": {}}
        # owner comes from my_pods() in real runs; --fake-util has no owner, so call record_resize directly
        code = ("import importlib.machinery, importlib.util, json, sys; "
                "l = importlib.machinery.SourceFileLoader('wd', sys.argv[1]); s = importlib.util.spec_from_loader('wd', l); "
                "m = importlib.util.module_from_spec(s); l.exec_module(m); "
                "m.record_resize(json.loads(sys.argv[2]), 'pod-x', 'job-x', 'LOW flag', 'OVERSIZED: mem -> 2Gi')")
        r = subprocess.run([sys.executable, "-c", code, SCRIPT, json.dumps(st)], env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("WATCHDOG RESIZE NOTE", (self.state / "resume" / "job-x.md").read_text())

    def test_followup_gets_read_only_s3(self):
        notes = self.tmp / "n.md"
        notes.write_text("read s3://b/report.json\n")
        self.wd("add", "j-s3", "--resume", str(notes))
        self.wd("run", "--fake-finished", "j-s3")
        args = "\n".join(self.lines("claude_args.log"))
        self.assertIn("Bash(nrp-s3-read cat:*)", args)
        self.assertNotIn("Bash(aws", args)
        prompt = next(self.fake.glob("claude_prompt_*.txt")).read_text()
        self.assertIn("nrp-s3-read cat s3://bucket/key", prompt)

    def test_s3_read_helper_refuses_writes(self):
        helper = str(HERE / "nrp-s3-read")
        for bad in (["cp", "s3://b/k", "-"], ["rm", "s3://b/k"], ["cat", "/etc/passwd"], ["cat", "s3://b/k", "s3://b/j"], ["ls"]):
            r = subprocess.run([sys.executable, helper, *bad], capture_output=True, text=True, env=self.env)
            self.assertEqual(r.returncode, 2, bad)
        r = subprocess.run([sys.executable, helper, "ls", "s3://b/out/"], capture_output=True, text=True, env=self.env)
        self.assertIn("aws.log", [p.name for p in self.fake.iterdir()])
        self.assertIn("s3 ls s3://b/out/", self.lines("aws.log")[-1])

    def test_add_during_pass_not_lost(self):
        # save_merged keeps a registration written while a pass held an older snapshot
        self.wd("add", "j-one")
        self.assertIn("j-one", json.loads((self.state / "jobs.json").read_text())["jobs"])
        self.wd("add", "j-two")
        self.run_pass()
        self.assertEqual(sorted(json.loads((self.state / "jobs.json").read_text())["jobs"]), ["j-one", "j-two"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

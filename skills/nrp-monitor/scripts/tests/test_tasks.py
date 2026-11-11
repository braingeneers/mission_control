#!/usr/bin/env python3
"""Tests for nrp-monitor v2 tasks (task add, pass, classification, fix agent via nrp-task, escalation, one push).
No cluster, S3, Slack or model: a fake kubectl / aws / osascript / claude sit first on PATH, a scratch state dir is used,
and NRP_MONITOR_NO_PUSH routes pushes to the fake banner log. The fake agent runs the real `nrp-task` commands listed
in fake/agent_plan.json. Run: python3 tests/test_tasks.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_isolation import wake_env

HERE = Path(__file__).resolve().parent.parent
SCRIPT = os.environ.get("MONITOR", str(HERE / "nrp-monitor"))
USER = "http://cilogon.org/serverE/users/100000"

TEST_ORIGIN = {"title": "test chat", "link": "https://example.test/chat/test-thread"}

FAKE_KUBECTL = r'''#!/usr/bin/env python3
import json, os, sys, time
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fake"); a = sys.argv[1:]
open(d + "/kubectl.log", "a").write(" ".join(a) + "\n")
if a[:1] == ["-n"]: a = a[2:]
cl = json.load(open(d + "/cluster.json"))
def save(): json.dump(cl, open(d + "/cluster.json", "w"))
def ts(x): return time.strftime("%%Y-%%m-%%dT%%H:%%M:%%SZ", time.gmtime(x))
def jobobj(n, j):
    st = {"ok": {"succeeded": 1}, "FAILED": {"failed": 1}, "running": {"active": 1}, "pending": {"active": 1}}[j["state"]]
    st = dict(st, startTime=ts(j.get("start", time.time() - 600)))
    if "succeeded" in j: st["succeeded"] = j["succeeded"]                      # partial Indexed Job: running pods + finished shards
    if j.get("reason"): st["conditions"] = [{"type": "Failed", "status": "True", "reason": j["reason"]}]
    return {"metadata": {"name": n, "annotations": {"nrp.ai/username": "%s"}}, "spec": dict({"activeDeadlineSeconds": j.get("deadline", 3600)}, **({"completions": j["completions"]} if "completions" in j else {})), "status": st}
def pods(n, j):
    if not any(k in j for k in ("term", "started", "wait", "node", "pod_status")): return []
    cs = {"state": {}}
    if j.get("term"): cs["state"]["terminated"] = dict(j["term"], startedAt=ts(j.get("started", time.time() - 300)))
    elif j.get("wait"): cs["state"]["waiting"] = {"reason": j["wait"], "message": "fake"}
    elif j.get("started"): cs["state"]["running"] = {"startedAt": ts(j["started"])}
    pod = {"metadata": {"name": n + "-abc"}, "spec": {"nodeName": j["node"]} if j.get("node") else {}, "status": {"containerStatuses": [cs]}}
    pod["status"].update(j.get("pod_status", {}))
    return [pod]
if a[:2] == ["get", "jobs"]:
    print(json.dumps({"items": [jobobj(n, j) for n, j in cl["jobs"].items()]}))
elif a[:2] == ["get", "job"]:
    j = cl["jobs"].get(a[2])
    if not j: sys.stderr.write('Error from server (NotFound): jobs "%%s" not found\n' %% a[2]); sys.exit(1)
    if "-o" in a and a[a.index("-o") + 1] == "json": print(json.dumps(jobobj(a[2], j)))
    else: print("{}/{}/{}/{}/".format(j.get("succeeded", 1 if j["state"] == "ok" else ""), 1 if j["state"] == "FAILED" else "", 1 if j["state"] == "running" else "", j.get("completions", "")), end="")
elif a[:2] == ["get", "pods"]:
    if "-l" in a:
        n = a[a.index("-l") + 1].split("=", 1)[1]; j = cl["jobs"].get(n)
        print(json.dumps({"items": pods(n, j) if j else []}))
    else: print(json.dumps({"items": []}))
elif a[0] == "logs":
    n = a[1].split("/", 1)[1]; j = cl["jobs"].get(n)
    if not j: sys.stderr.write("NotFound\n"); sys.exit(1)
    print(j.get("log", "fake log for " + n))
elif a[0] == "describe":
    print("fake describe " + " ".join(a[1:]))
elif a[0] == "delete":
    n = a[2]
    if n in cl["jobs"]: del cl["jobs"][n]; save(); open(d + "/deleted.log", "a").write(n + "\n")
    else: sys.stderr.write('Error from server (NotFound): jobs "%%s" not found\n' %% n); sys.exit(1)
elif a[0] == "apply":
    f = a[a.index("-f") + 1]
    if os.path.exists(d + "/apply_block"): sys.stderr.write("admission webhook denied the request: Your pods resources utilization is too low\n"); sys.exit(1)
    import yaml
    m = yaml.safe_load(open(f)); n = m["metadata"]["name"]
    if "--dry-run=server" in a: print("job.batch/%%s created (server dry run)" %% n); sys.exit(0)
    if n in cl["jobs"]: sys.stderr.write("field is immutable\n"); sys.exit(1)
    cl["jobs"][n] = {"state": "running", "start": time.time()}; save()
    open(d + "/applied.log", "a").write(n + " " + open(f).read().replace("\n", " ") + "\n"); print("job.batch/%%s created" %% n)
elif a[:2] == ["create", "configmap"]:
    open(d + "/configmaps.log", "a").write(a[2] + "\n"); print("configmap/%%s created" %% a[2])
else:
    sys.stderr.write("fake kubectl: unsupported %%s\n" %% a); sys.exit(2)
''' % USER
FAKE_AWS = r'''#!/usr/bin/env python3
import hashlib, json, os, sys
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fake"); uri = sys.argv[-1]; a = sys.argv[1:]
if "head-object" in sys.argv:                                          # exact object check (what the monitor uses)
    u = "s3://%s/%s" % (a[a.index("--bucket") + 1], a[a.index("--key") + 1])
    open(d + "/aws.log", "a").write(" ".join(a) + "\n")
    if os.path.exists(d + "/aws_fail"): sys.stderr.write("Could not connect to the endpoint URL\n"); sys.exit(255)
    if os.path.exists(d + "/aws_403"): sys.stderr.write("An error occurred (403) when calling the HeadObject operation: Forbidden\n"); sys.exit(254)
    if os.path.exists(d + "/aws_garbage"): print("<html>proxy page</html>"); sys.exit(0)
    if u in json.load(open(d + "/s3.json")): print(json.dumps({"ETag": '"x"', "ContentLength": 0})); sys.exit(0)   # EXACT, never a prefix
    sys.stderr.write("An error occurred (404) when calling the HeadObject operation: Not Found\n"); sys.exit(254)
have = json.load(open(d + "/s3.json"))
if "cp" in sys.argv:                                                   # upload / download against a content store (reship tests)
    src, dst = sys.argv[sys.argv.index("cp") + 1:][:2]
    store = d + "/store"; os.makedirs(store, exist_ok=True)
    key = lambda u: store + "/" + hashlib.md5(u.encode()).hexdigest()
    if dst.startswith("s3://"):
        open(d + "/uploads.log", "a").write(src + " " + dst + "\n")
        try: open(key(dst), "wb").write(sys.stdin.buffer.read() if src == "-" else open(src, "rb").read())
        except OSError: pass
        sys.exit(0)
    if src.startswith("s3://"):
        if not os.path.exists(key(src)): sys.stderr.write("NoSuchKey\n"); sys.exit(1)
        data = open(key(src), "rb").read()
        if dst == "-": sys.stdout.buffer.write(data)
        else: open(dst, "wb").write(data)
        sys.exit(0)
if uri.startswith("s3://nosuchbucket"): sys.stderr.write("An error occurred (NoSuchBucket)\n"); sys.exit(255)
if uri.count("/") == 3 and uri.endswith("/"): sys.exit(0)            # bucket listing
if any(h.startswith(uri) for h in have): print("2026-11-05 12:00:00 12 x"); sys.exit(0)
sys.exit(1)
'''
FAKE_OSA = '#!/bin/sh\necho "$@" >> "$(dirname "$0")/../fake/notifications.log"\n'
FAKE_CLAUDE = r'''#!/usr/bin/env python3
"""Fake agent: for a task prompt, run the next plan entry's commands (real nrp-task), then print claude -p JSON."""
import json, os, subprocess, sys
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fake"); prompt = sys.stdin.read()
n = len([f for f in os.listdir(d) if f.startswith("prompt_")])
open("%s/prompt_%03d.txt" % (d, n), "w").write(prompt)
open(d + "/claude_args.log", "a").write(json.dumps(sys.argv[1:]) + "\n")
if "nrp-monitor" not in prompt or "TASK" not in prompt and "NRP task" not in prompt:
    print(open(d + "/claude_out").read() if os.path.exists(d + "/claude_out") else "ok: fake"); sys.exit(0)
plan = json.load(open(d + "/agent_plan.json")) if os.path.exists(d + "/agent_plan.json") else []
step = plan.pop(0) if plan else {"cmds": [], "result": "STOPPED: no plan"}
json.dump(plan, open(d + "/agent_plan.json", "w"))
outs = []
for c in step.get("cmds", []):
    if c[0] == "sh":
        r = subprocess.run(c[1], shell=True, capture_output=True, text=True)
    else:
        r = subprocess.run(c, capture_output=True, text=True)
    outs.append([c, r.returncode, (r.stdout + r.stderr)[-500:]])
open(d + "/agent_outs.log", "a").write(json.dumps(outs) + "\n")
print(json.dumps({"result": step.get("result", "done"), "permission_denials": step.get("denials", []), "total_cost_usd": 0.12, "num_turns": 5}))
'''

MANIFEST = """apiVersion: batch/v1
kind: Job
metadata: {name: %(job)s}
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 3600
  ttlSecondsAfterFinished: 86400
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: main
        image: python:3.11-slim
        command: ["python", "-c", "print(1)"]
        resources:
          requests: {cpu: "500m", memory: %(mem)s}
          limits: {cpu: "500m", memory: %(mem)s}
"""


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wdtask_"))
        self.fake, self.state, self.bin = self.tmp / "fake", self.tmp / "state", self.tmp / "bin"
        for p in (self.fake, self.state, self.bin):
            p.mkdir()
        for n, body in (("kubectl", FAKE_KUBECTL), ("aws", FAKE_AWS), ("osascript", FAKE_OSA), ("claude", FAKE_CLAUDE)):
            (self.bin / n).write_text(body)
            os.chmod(self.bin / n, 0o755)
        (self.bin / "python3").symlink_to(sys.executable)
        shutil.copy(SCRIPT, self.bin / "nrp-monitor")
        shutil.copy(HERE / "nrp-task", self.bin / "nrp-task")
        shutil.copytree(HERE / "templates", self.state / "templates")
        (self.fake / "cluster.json").write_text('{"jobs": {}}')
        (self.fake / "s3.json").write_text("[]")
        self.env = {"PATH": "%s:/usr/bin:/bin" % self.bin, "HOME": str(self.tmp), "NRP_MONITOR_OWNER_NAME": "Sam", "FAKE_DIR": str(self.fake),
                    "NRP_MONITOR_STATE": str(self.state), "NRP_TASK_CACHE": str(self.tmp / "cache"),
                    "NRP_MONITOR_NO_PUSH": "1", "NRP_MONITOR_SLACK_URL": "http://127.0.0.1:9/never"}
        self.env.update(wake_env(self.tmp))
        # a code repo with a bug
        self.repo = self.tmp / "repo"
        (self.repo / "job").mkdir(parents=True)
        (self.repo / "job" / "run.py").write_text("x = {'size': 1}\nprint(x['sise'])\n")
        for c in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"]):
            subprocess.run(["git", *c], cwd=self.repo, check=True, capture_output=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def wd(self, *args):
        r = subprocess.run([str(self.bin / "nrp-monitor"), *args], capture_output=True, text=True, env=self.env, timeout=120)
        return r.returncode, r.stdout.strip(), r.stderr.strip()

    def tool(self, task, *args):
        e = dict(self.env, NRP_TASK=task)
        r = subprocess.run([str(self.bin / "nrp-task"), *args], capture_output=True, text=True, env=e, timeout=120)
        return r.returncode, (r.stdout + r.stderr).strip()

    def manifest(self, job, mem="512Mi", **over):
        p = self.tmp / ("%s.yaml" % job)
        text = MANIFEST % {"job": job, "mem": mem}
        for k, v in over.items():
            text = text.replace(k, v)
        p.write_text(text)
        return str(p)

    def add(self, name="t1", stages=None, **kw):
        stages = stages or [{"id": "a", "job": name + "-a", "manifest": self.manifest(name + "-a"),
                             "done_s3": ["s3://braingeneersdev/alice/test/%s/a.txt" % name]}]
        kw.setdefault("origin", TEST_ORIGIN)                 # v3: `task add` refuses a task without an origin chat
        spec = dict({"name": name, "goal": "test task " + name, "approved": "Sam 2026-11-05 in chat: go",
                     "notes": "a fake task", "stages": stages}, **kw)
        f = self.tmp / (name + ".json")
        f.write_text(json.dumps(spec))
        return self.wd("task", "add", str(f))

    def add_unattributed(self, name="t1", **kw):
        """A task registered before v3 (no origin): add with one, then strip it, since `task add` now refuses a missing origin."""
        rc, out, err = self.add(name, **kw)
        p = self.state / "tasks" / name / "task.json"
        t = json.loads(p.read_text())
        t["origin"] = None
        p.write_text(json.dumps(t))
        return rc, out, err

    def task(self, n="t1"):
        return json.loads((self.state / "tasks" / n / "task.json").read_text())

    def cl(self):
        return json.loads((self.fake / "cluster.json").read_text())["jobs"]

    def set_job(self, name, **kw):
        c = json.loads((self.fake / "cluster.json").read_text())
        c["jobs"][name] = dict(c["jobs"].get(name, {}), **kw)
        (self.fake / "cluster.json").write_text(json.dumps(c))

    def plan(self, *steps):
        (self.fake / "agent_plan.json").write_text(json.dumps(list(steps)))

    def pushes(self):
        p = self.fake / "notifications.log"
        return [l for l in p.read_text().splitlines()] if p.exists() else []

    def prompts(self):
        return sorted(self.fake.glob("prompt_*.txt"))

    def run_pass(self):
        rc, out, err = self.wd("run", "--tasks-only")
        self.assertEqual(rc, 0, err)
        return out

    def age_submit(self, n="t1"):
        """Make 'submitted' old enough for the vanished-Job grace."""
        p = self.state / "tasks" / n / "task.json"
        t = json.loads(p.read_text())
        for s in t["stages"]:
            if "submitted" in s:
                s["submitted"] -= 3600
        p.write_text(json.dumps(t))

    # ---------------------------------------------------------------- add / validation
    def test_add_refuses_missing_fields_and_bad_bucket(self):
        rc, _, err = self.add(approved="")
        self.assertNotEqual(rc, 0)
        self.assertIn("approved", err)
        rc, _, err = self.add(stages=[{"id": "a", "job": "t1-a", "manifest": self.manifest("t1-a"), "done_s3": ["s3://nosuchbucket/x/y"]}])
        self.assertIn("bucket nosuchbucket", err)
        rc, _, err = self.add(stages=[{"id": "a", "job": "t1-a", "manifest": self.manifest("t1-a"), "done_s3": []}])
        self.assertIn("done_s3", err)

    def test_existing_legacy_clone_branch_remains_usable(self):
        self.assertEqual(self.add(code={"repo": str(self.repo), "subdir": "job"})[0], 0)
        t = self.task()
        clone = t["code"]["clone"]
        subprocess.run(["git", "branch", "-m", "watchdog/t1"], cwd=clone, check=True)
        t["code"]["branch"] = "watchdog/t1"
        (self.state / "tasks/t1/task.json").write_text(json.dumps(t))
        (Path(clone) / "job/new.py").write_text("value = 1\n")
        rc, out = self.tool("t1", "commit", "legacy branch fix")
        self.assertEqual(rc, 0, out)
        self.assertIn("on watchdog/t1", out)

    def test_smoke_cap_reads_custom_shared_policy(self):
        shutil.copy(HERE / "nrp-util-check", self.bin / "nrp-util-check")
        policy = self.tmp / "policy.json"
        policy.write_text(json.dumps({"gpu_floor": .4, "max_concurrent_jobs": 400, "smoke_max_jobs": 1}))
        self.env["NRP_UTIL_POLICY"] = str(policy)
        m = self.manifest("t1-a")
        p = Path(m)
        p.write_text(p.read_text().replace("backoffLimit: 0", "backoffLimit: 0\n  completions: 2"))
        rc, _, err = self.add(stages=[dict(id="a", job="t1-a", manifest=m, done_s3=["s3://braingeneersdev/t/a"], purpose="smoke")])
        self.assertNotEqual(rc, 0)
        self.assertIn("1..1 (smoke_max_jobs)", err)

    def test_smoke_profile_caps_total_completions_and_parallelism(self):
        for mark in ({"purpose": "smoke"}, {"purpose": "profile"}, {"smoke": True}, {"profile": True}):
            for key in ("parallelism", "completions"):
                m = self.manifest("t1-a")
                p = Path(m)
                p.write_text(p.read_text().replace("backoffLimit: 0", "backoffLimit: 0\n  %s: 4" % key))
                stage = dict(id="a", job="t1-a", manifest=m, done_s3=["s3://braingeneersdev/t/a"], **mark)
                rc, _, err = self.add(stages=[stage])
                self.assertNotEqual(rc, 0, err)
                self.assertIn("smoke_max_jobs", err)

    def test_profile_accepts_three_and_preserves_intent(self):
        m = self.manifest("t1-a")
        p = Path(m)
        p.write_text(p.read_text().replace("backoffLimit: 0", "backoffLimit: 0\n  completions: 3\n  parallelism: 2"))
        stage = dict(id="a", job="t1-a", manifest=m, done_s3=["s3://braingeneersdev/t/a"], purpose="profile")
        rc, _, err = self.add(stages=[stage])
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.task()["stages"][0]["purpose"], "profile")

    def test_add_refuses_manifest_breaking_house_rules(self):
        m = self.manifest("t1-a", **{"backoffLimit: 0": "backoffLimit: 3", 'print(1)': 'import time; time.sleep(1)", "sleep 99999'})
        rc, _, err = self.add(stages=[{"id": "a", "job": "t1-a", "manifest": m, "done_s3": ["s3://braingeneersdev/x/a"]}])
        self.assertNotEqual(rc, 0)
        self.assertIn("backoffLimit must be 0", err)
        self.assertIn("no long sleep", err)
        rc, _, err = self.add(stages=[{"id": "a", "job": "t1-a", "manifest": self.manifest("other"), "done_s3": ["s3://braingeneersdev/x/a"]}])
        self.assertIn("metadata.name", err)

    def test_add_warns_on_existing_output(self):
        (self.fake / "s3.json").write_text(json.dumps(["s3://braingeneersdev/alice/test/t1/a.txt"]))
        rc, _, err = self.add()
        self.assertEqual(rc, 0, err)
        self.assertIn("ALREADY exists", err)

    # ---------------------------------------------------------------- happy path
    def test_two_stages_submit_success_chain_silent(self):
        stages = [{"id": "a", "job": "t1-a", "manifest": self.manifest("t1-a"), "done_s3": ["s3://braingeneersdev/t/a.txt"]},
                  {"id": "b", "job": "t1-b", "manifest": self.manifest("t1-b"), "after": ["a"], "done_s3": ["s3://braingeneersdev/t/b.txt"]}]
        self.assertEqual(self.add(stages=stages)[0], 0)
        self.run_pass()
        self.assertIn("t1-a", self.cl())
        self.assertNotIn("t1-b", self.cl())
        self.set_job("t1-a", state="ok")
        (self.fake / "s3.json").write_text(json.dumps(["s3://braingeneersdev/t/a.txt"]))
        self.run_pass()
        self.assertNotIn("t1-a", self.cl(), "finished Job deleted after its logs were saved")
        self.assertTrue((self.state / "tasks/t1/logs/t1-a-a1.txt").exists())
        self.assertIn("t1-b", self.cl(), "next stage submitted by the script, no agent")
        self.set_job("t1-b", state="ok")
        (self.fake / "s3.json").write_text(json.dumps(["s3://braingeneersdev/t/a.txt", "s3://braingeneersdev/t/b.txt"]))
        self.run_pass()
        self.assertEqual(self.task()["status"], "done")
        self.assertEqual(self.pushes(), [], "success is silent")
        self.assertEqual(self.prompts(), [])
        rc, out, _ = self.wd("digest")
        self.assertIn("all 2 stage(s) done", out)

    def test_success_without_output_is_a_failure(self):
        self.add(stages=[{"id": "a", "job": "t1-a", "manifest": self.manifest("t1-a"), "done_s3": ["s3://braingeneersdev/t/a.txt"]}],
                 max_retries=0)
        self.run_pass()
        self.set_job("t1-a", state="ok")
        self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "NEEDS_OWNER")
        self.assertIn("does not exist", t["reason"])

    # ---------------------------------------------------------------- the e2e story (fake): OOM -> code bug -> repeated -> 1 push
    def test_oom_then_code_bug_then_repeated_failure_pushes_once(self):
        self.add(code={"repo": str(self.repo), "subdir": "job"})
        t = self.task()
        clone = t["code"]["clone"]
        man = t["stages"][0]["manifest"]
        self.run_pass()
        # 1) OOM -> resources -> agent doubles memory and resubmits (silent)
        self.set_job("t1-a", state="FAILED", term={"reason": "OOMKilled", "exitCode": 137})
        self.plan({"cmds": [["sh", "sed -i '' 's/512Mi/1Gi/g' %s" % man], ["nrp-task", "submit", "t1-a", "--reason", "OOM at 512Mi -> 1Gi"],
                            ["nrp-task", "report", "RESUBMITTED", "OOM at 512Mi -> 1Gi"]], "result": "RESUBMITTED: OOM -> 1Gi"})
        self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "retrying")
        self.assertEqual(t["attempts"][0]["cls"], "resources")
        self.assertEqual(t["attempts"][0]["sig"], "oom@512Mi")
        self.assertIn("class resources", self.prompts()[0].read_text())
        self.assertIn("1Gi", (self.fake / "applied.log").read_text().splitlines()[-1])
        # 2) code bug -> agent fixes in the clone, commits, rebuilds the ConfigMap, resubmits (silent)
        self.set_job("t1-a", state="FAILED", term={"reason": "Error", "exitCode": 1},
                     log="Traceback (most recent call last):\n  File \"run.py\", line 2\nKeyError: 'sise'")
        self.plan({"cmds": [["sh", "sed -i '' s/sise/size/ %s/job/run.py" % clone], ["nrp-task", "commit", "fix KeyError sise -> size"],
                            ["nrp-task", "configmap", "t1-code-fix1"],
                            ["nrp-task", "submit", "t1-a", "--reason", "KeyError typo -> fixed"],
                            ["nrp-task", "report", "RESUBMITTED", "KeyError typo fixed"]], "result": "RESUBMITTED: typo"})
        self.run_pass()
        t = self.task()
        self.assertEqual([x["cls"] for x in t["attempts"]], ["resources", "code"])
        self.assertTrue(t["attempts"][1]["sig"].startswith("code:keyerror"))
        log = subprocess.run(["git", "log", "--oneline", "monitor/t1"], cwd=clone, capture_output=True, text=True).stdout
        self.assertIn("monitor fix (t1)", log)
        self.assertIn("t1-code-fix1", (self.fake / "configmaps.log").read_text())
        self.assertEqual(self.pushes(), [], "retries are silent")
        # 3) transient error -> agent resubmits unchanged; the same error again -> escalate, no agent, ONE push
        err = "Traceback...\nbotocore.exceptions.EndpointConnectionError: Could not connect to the endpoint URL"
        self.set_job("t1-a", state="FAILED", term={"reason": "Error", "exitCode": 1}, log=err)
        self.plan({"cmds": [["nrp-task", "submit", "t1-a", "--reason", "transient S3 error -> resubmit unchanged"]], "result": "RESUBMITTED"})
        self.run_pass()
        self.assertEqual(self.task()["attempts"][-1]["cls"], "infra")
        self.set_job("t1-a", state="FAILED", term={"reason": "Error", "exitCode": 1}, log=err)
        n_prompts = len(self.prompts())
        self.run_pass()
        self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "NEEDS_OWNER")
        self.assertIn("same way again", t["reason"])
        self.assertEqual(len(self.prompts()), n_prompts, "no agent for a repeated failure")
        self.assertEqual(len(self.pushes()), 1, self.pushes())
        self.assertIn("needs you", self.pushes()[0])
        rc, out, _ = self.wd("status", "--quiet")
        self.assertIn("1 task(s) need the owner", out)

    def test_slow_deadline_enters_the_ladder_not_the_owner(self):
        """v3: a timeout is never a direct page. It goes Tier 1 (Haiku) -> Tier 2 (Sonnet); with no coordinator webhook the end of the
        ladder falls back to NEEDS_OWNER (see test_ladder.py for the coordinator path)."""
        self.add()
        self.run_pass()
        import time
        self.set_job("t1-a", started=time.time() - 3500)
        self.run_pass()                                                   # records pod_started
        self.set_job("t1-a", state="FAILED", reason="DeadlineExceeded", deadline=3600, start=time.time() - 3700)
        self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "NEEDS_OWNER")
        self.assertIn("no coordinator webhook", t["reason"])
        self.assertEqual(len(self.prompts()), 2, "a triage prompt, then the fix agent")
        self.assertIn("class slow", self.prompts()[1].read_text())
        self.assertEqual(len(self.pushes()), 1)

    def test_queue_deadline_is_retryable(self):
        self.add()
        self.run_pass()
        self.set_job("t1-a", state="FAILED", reason="DeadlineExceeded")
        self.plan({"cmds": [["nrp-task", "report", "STOPPED", "need more info"]], "result": "STOPPED: need more info"})
        self.run_pass()
        self.assertIn("class queue", self.prompts()[0].read_text())

    def fix_prompt(self):
        self.add()
        self.run_pass()
        self.set_job("t1-a", state="FAILED", reason="DeadlineExceeded")
        self.plan({"cmds": [["nrp-task", "report", "STOPPED", "need more info"]], "result": "STOPPED: need more info"})
        self.run_pass()
        return self.prompts()[0].read_text()

    def test_skip_limit_defaults_to_5_percent(self):
        txt = self.fix_prompt()
        self.assertIn("more than 5% of items", txt)
        self.assertNotIn("{skip_limit}", txt)

    def test_skip_limit_is_a_setting(self):
        (self.state / "config.json").write_text(json.dumps({"skip_limit_fraction": 0.02}))
        self.assertIn("more than 2% of items", self.fix_prompt())

    def test_skip_limit_env_overrides_config_and_bad_values_fall_back(self):
        (self.state / "config.json").write_text(json.dumps({"skip_limit_fraction": 0.02}))
        self.env["NRP_MONITOR_SKIP_LIMIT_FRACTION"] = "0.1"
        self.assertIn("more than 10% of items", self.fix_prompt())

    def test_skip_limit_bad_value_falls_back_to_the_default(self):
        self.env["NRP_MONITOR_SKIP_LIMIT_FRACTION"] = "1.5"
        self.assertIn("more than 5% of items", self.fix_prompt())

    def test_agent_stop_pushes_its_diagnosis_once(self):
        self.add()
        self.run_pass()
        self.set_job("t1-a", state="FAILED", term={"reason": "Error", "exitCode": 1}, log="ValueError: input shape mismatch")
        self.plan({"cmds": [["nrp-task", "report", "STOPPED", "input file has 3 channels, code expects 4: Sam decides which"]],
                   "result": "STOPPED: input has 3 channels"})
        self.run_pass()
        self.run_pass()
        self.assertEqual(self.task()["status"], "NEEDS_OWNER")
        self.assertEqual(len(self.pushes()), 1)
        self.assertIn("3 channels", self.pushes()[0])

    def test_watch_mode_pushes_on_failure(self):
        self.add(mode="watch")
        self.run_pass()
        self.set_job("t1-a", state="FAILED", term={"reason": "OOMKilled", "exitCode": 137})
        self.run_pass()
        self.assertEqual(self.prompts(), [])
        self.assertEqual(len(self.pushes()), 1)

    def test_denials_are_monitor_faults(self):
        self.add()
        self.run_pass()
        self.set_job("t1-a", state="FAILED", term={"reason": "Error", "exitCode": 1}, log="KeyError: x")
        self.plan({"cmds": [], "result": "could not run kubectl", "denials": [{"tool_name": "Bash", "tool_input": {"command": "kubectl get job"}}]})
        self.run_pass()
        dig = (self.state / "digest.log").read_text()
        self.assertIn("monitor fault", dig)
        self.assertIn("denied 1 tool call", self.task()["reason"])

    # ---------------------------------------------------------------- nrp-task guards
    def test_tool_guards(self):
        self.add(code={"repo": str(self.repo), "subdir": "job"})
        self.run_pass()
        self.set_job("someone-else", state="ok")
        rc, out = self.tool("t1", "logs", "someone-else")
        self.assertNotEqual(rc, 0)
        self.assertIn("one of this task's Jobs", out)
        rc, out = self.tool("t1", "delete", "t1-a")                       # running, no failure
        self.assertNotEqual(rc, 0)
        rc, out = self.tool("t1", "configmap", "other-name")
        self.assertIn("must be t1-", out)
        rc, out = self.tool("t1", "submit", "t1-a", "--reason", "x")      # running
        self.assertIn("nothing to submit", out)
        rc, out = self.tool("nope", "show")
        self.assertIn("NRP_TASK", out)
        rc, out = self.tool("t1", "show")
        self.assertEqual(rc, 0)

    def test_retry_cap_enforced_in_submit(self):
        self.add(max_retries=1)
        self.run_pass()
        self.set_job("t1-a", state="FAILED", term={"reason": "OOMKilled", "exitCode": 137})
        self.plan({"cmds": [["nrp-task", "submit", "t1-a", "--reason", "r1"]], "result": "RESUBMITTED"})
        self.run_pass()
        self.set_job("t1-a", state="FAILED", term={"reason": "Error", "exitCode": 1}, log="KeyError: y")
        self.run_pass()                                                   # cap 1 used -> escalate without agent
        self.assertEqual(self.task()["status"], "NEEDS_OWNER")
        self.assertIn("retry cap", self.task()["reason"])

    def test_blocked_submit_waits_silently_then_goes_on(self):
        self.add()
        (self.fake / "apply_block").write_text("1")
        self.run_pass()
        self.assertEqual(self.task()["status"], "blocked")
        self.run_pass()
        self.assertEqual(self.pushes(), [])
        (self.fake / "apply_block").unlink()
        self.run_pass()
        self.assertIn("t1-a", self.cl())
        self.assertEqual(self.task()["status"], "running")

    def test_resume_after_hunter(self):
        self.add(mode="watch")
        self.run_pass()
        self.set_job("t1-a", state="FAILED", term={"reason": "OOMKilled", "exitCode": 137})
        self.run_pass()
        rc, out, err = self.wd("task", "resume", "t1", "--note", "raised memory by hand")
        self.assertEqual(rc, 0, err)
        self.run_pass()
        self.assertEqual(self.cl()["t1-a"]["state"], "running")
        self.assertEqual(self.task()["status"], "running")
        self.assertIn("the next pass resubmits", out)

    def test_resume_skip_says_skipped_not_resubmitted(self):
        self.add(mode="watch")
        self.run_pass()
        self.set_job("t1-a", state="FAILED", term={"reason": "OOMKilled", "exitCode": 137})
        self.run_pass()
        sid = self.task()["stages"][0]["id"]
        rc, out, err = self.wd("task", "resume", "t1", "--skip", sid, "--note", "outputs verified by hand")
        self.assertEqual(rc, 0, err)
        self.assertIn("skipped (marked done): %s" % sid, out)
        self.assertNotIn("resubmits", out)
        self.assertEqual(self.task()["stages"][0]["state"], "done")

    def test_vanished_job_without_outputs_is_infra(self):
        self.add()
        self.run_pass()
        c = json.loads((self.fake / "cluster.json").read_text())
        del c["jobs"]["t1-a"]
        (self.fake / "cluster.json").write_text(json.dumps(c))
        self.age_submit()
        self.plan({"cmds": [["nrp-task", "submit", "t1-a", "--reason", "vanished -> resubmit"]], "result": "RESUBMITTED"})
        self.run_pass()
        self.assertEqual(self.task()["attempts"][0]["cls"], "infra")
        self.assertIn("t1-a", self.cl())

    # ---------------------------------------------------------------- v2.1: WIP clone, GPU approval, pv3 reship
    def test_clone_carries_untracked_source_files(self):
        (self.repo / "job" / "new_mod.py").write_text("print('wip')\n")
        (self.repo / "job" / "blob.bin").write_bytes(b"x" * 10)
        (self.repo / "job" / "run.py").write_text("x = {'size': 1}\nprint(x['size'])\n")      # tracked, modified
        rc, out, err = self.add(code={"repo": str(self.repo), "subdir": "job"})
        self.assertEqual(rc, 0, err)
        clone = Path(self.task()["code"]["clone"])
        self.assertEqual((clone / "job" / "new_mod.py").read_text(), "print('wip')\n")
        self.assertIn("x['size']", (clone / "job" / "run.py").read_text())
        self.assertFalse((clone / "job" / "blob.bin").exists())
        self.assertIn("1 untracked source file(s)", err)
        self.assertIn("1 untracked file(s)", err)                   # blob.bin reported, not silent
        log = subprocess.run(["git", "log", "--oneline"], cwd=clone, capture_output=True, text=True).stdout
        self.assertIn("untracked source files at task add", log)

    def gpu_manifest(self, job):
        p = self.manifest(job)
        text = Path(p).read_text().replace("memory: 512Mi}", 'memory: 512Mi, nvidia.com/gpu: "1"}')
        Path(p).write_text(text)
        return p

    def test_gpu_stage_needs_an_approval_date(self):
        st = {"id": "a", "job": "t1-a", "manifest": self.gpu_manifest("t1-a"), "done_s3": ["s3://braingeneersdev/t/a"]}
        rc, _, err = self.add(stages=[st])
        self.assertNotEqual(rc, 0)
        self.assertIn("gpu_ok_until", err)
        rc, _, err = self.add(stages=[dict(st, gpu_ok_until="2020-01-01")])
        self.assertIn("already past", err)
        rc, _, err = self.add(stages=[dict(st, gpu_ok_until="2999-01-01")])
        self.assertEqual(rc, 0, err)

    def test_gpu_retry_after_approval_day_escalates_once_without_agent(self):
        st = {"id": "a", "job": "t1-a", "manifest": self.gpu_manifest("t1-a"), "done_s3": ["s3://braingeneersdev/t/a"],
              "gpu_ok_until": "2026-11-06"}
        self.env["NRP_MONITOR_TODAY"] = "2026-11-06"
        self.assertEqual(self.add(stages=[st])[0], 0)
        self.run_pass()
        self.assertIn("t1-a", self.cl())                            # approved day: submitted
        self.set_job("t1-a", state="FAILED", term={"reason": "OOMKilled", "exitCode": 137})
        self.env["NRP_MONITOR_TODAY"] = "2026-11-07"                # the day after Sam's OK
        n = len(self.prompts())
        self.run_pass()
        self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "NEEDS_OWNER")
        self.assertIn("GPU APPROVAL", t["reason"])
        self.assertEqual(len(self.prompts()), n, "no fix agent for an unapproved GPU retry")
        self.assertEqual(len(self.pushes()), 1)
        rc, out, err = self.wd("task", "resume", "t1", "--gpu-ok-until", "2026-11-08")
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.task()["stages"][0]["gpu_ok_until"], "2026-11-08")

    def test_reship_points_spec_at_the_clones_code(self):
        # a pv3-shaped repo: predictor_v3/utils/jobs/codeship.py is the real module (stdlib only)
        real = Path(__file__).resolve().parent / "fixtures" / "codeship_pv3.py"      # vendored real packer
        if not real.exists():
            self.skipTest("codeship.py not found")
        pkg = self.repo / "predictor_v3"
        (pkg / "utils" / "jobs").mkdir(parents=True)
        for d in (pkg, pkg / "utils", pkg / "utils" / "jobs"):
            (d / "__init__.py").write_text("")
        shutil.copy(real, pkg / "utils" / "jobs" / "codeship.py")
        (pkg / "job.py").write_text("print(1/0)\n")
        for c in (["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "pv3"]):
            subprocess.run(["git", *c], cwd=self.repo, check=True, capture_output=True)
        spec_uri = "s3://braingeneersdev/alice/test/pv3/jobs/t1-a/spec.json"
        m = Path(self.manifest("t1-a"))
        m.write_text(m.read_text().replace('["python", "-c", "print(1)"]', '["python", "-m", "e", "gate", "--spec", "%s"]' % spec_uri))
        self.env["NRP_TASK_PYTHON"] = sys.executable
        stage = {"id": "a", "job": "t1-a", "manifest": str(m), "done_s3": ["s3://braingeneersdev/t/a"]}
        self.assertEqual(self.add(stages=[stage], code={"repo": str(self.repo), "subdir": "predictor_v3"})[0], 0)
        import hashlib
        old_uri = "s3://braingeneersdev/alice/test/pv3/code/0000000000000000.tgz"
        store = self.fake / "store"
        store.mkdir()
        (store / hashlib.md5(spec_uri.encode()).hexdigest()).write_text(json.dumps({"module": "m", "code": {"uri": old_uri, "sha256": "0" * 64}}))
        self.run_pass()
        rc, out = self.tool("t1", "reship", "t1-a")
        self.assertNotEqual(rc, 0)
        self.assertIn("still running", out)                          # a running Job is never reshipped
        self.set_job("t1-a", state="FAILED")
        clone = self.task()["code"]["clone"]
        (Path(clone) / "predictor_v3" / "job.py").write_text("print(1)\n")        # the agent's fix
        self.tool("t1", "commit", "fix div by zero")
        rc, out = self.tool("t1", "reship", "t1-a")
        self.assertEqual(rc, 0, out)
        self.assertIn("reshipped", out)
        spec = json.loads((store / hashlib.md5(spec_uri.encode()).hexdigest()).read_text())
        self.assertNotEqual(spec["code"]["sha256"], "0" * 64)
        self.assertEqual(spec["module"], "m")                       # rest of the spec untouched
        self.assertEqual(spec["code"]["uri"], "s3://braingeneersdev/alice/test/pv3/code/%s.tgz" % spec["code"]["sha256"][:16])
        self.assertTrue((store / hashlib.md5(spec["code"]["uri"].encode()).hexdigest()).exists())
        import io, tarfile
        tf = tarfile.open(fileobj=io.BytesIO((store / hashlib.md5(spec["code"]["uri"].encode()).hexdigest()).read_bytes()), mode="r:gz")
        self.assertEqual(tf.extractfile("predictor_v3/job.py").read(), b"print(1)\n")
        rc, out = self.tool("t1", "reship", "t1-a")                 # same code again: nothing to do
        self.assertIn("identical", out)

    def test_reship_refuses_job_without_s3_spec(self):
        self.add(code={"repo": str(self.repo), "subdir": "job"})
        self.set_job("t1-a", state="FAILED")
        rc, out = self.tool("t1", "reship", "t1-a")
        self.assertNotEqual(rc, 0)
        self.assertIn("--spec", out)

    def test_dry_run_changes_nothing(self):
        self.add()
        before = (self.state / "tasks/t1/task.json").read_text()
        rc, out, err = self.wd("run", "--dry-run", "--tasks-only")
        self.assertEqual(rc, 0, err)
        self.assertIn("would submit stage a", out)
        self.assertEqual(before, (self.state / "tasks/t1/task.json").read_text())
        self.assertEqual(self.cl(), {})

    # ---------------------------------------------------------------- after_s3 gate (T71d)
    GATE = "s3://braingeneersdev/alice/test/upstream/done.json"

    def gated(self, extra=None, **kw):
        stages = [{"id": "g", "job": "t1-g", "manifest": self.manifest("t1-g"), "after_s3": [self.GATE],
                   "done_s3": ["s3://braingeneersdev/t/g.txt"]}] + (extra or [])
        return self.add(stages=stages, **kw)

    def test_after_s3_validation(self):
        base = {"id": "a", "job": "t1-a", "manifest": self.manifest("t1-a"), "done_s3": ["s3://braingeneersdev/t/a.txt"]}
        for bad in ("s3://braingeneersdev/x", ["not-a-uri"], ["s3://braingeneersdev/"], [3]):
            rc, _, err = self.add(stages=[dict(base, after_s3=bad)])
            self.assertNotEqual(rc, 0, bad)
            self.assertIn("after_s3", err)
        rc, _, err = self.add(stages=[dict(base, after_s3=["s3://nosuchbucket/k/done.json"])])
        self.assertIn("bucket nosuchbucket", err)
        rc, _, err = self.add(stages=[dict(base, after_s3=base["done_s3"])])
        self.assertIn("repeats one of the stage's own done_s3", err)
        self.assertEqual(self.add(stages=[dict(base, after_s3=[self.GATE])])[0], 0)
        self.assertEqual(self.task()["stages"][0]["after_s3"], [self.GATE])

    def test_after_s3_keeps_stage_pending_until_every_key_exists(self):
        two = "s3://braingeneersdev/alice/test/upstream/second.json"
        stages = [{"id": "g", "job": "t1-g", "manifest": self.manifest("t1-g"), "after_s3": [self.GATE, two],
                   "done_s3": ["s3://braingeneersdev/t/g.txt"]}]
        self.assertEqual(self.add(stages=stages)[0], 0)
        for _ in range(2):                                      # passes with nothing there: nothing submitted, silent
            self.run_pass()
            self.assertEqual(self.cl(), {})
        self.assertEqual(self.task()["stages"][0]["state"], "pending")
        rc, out, _ = self.wd("task", "show", "t1")
        self.assertIn("waiting-on %s" % self.GATE, out)
        self.assertIn("waiting-on %s" % two, out)
        self.assertEqual(self.pushes(), [])
        self.assertEqual(self.prompts(), [])
        (self.fake / "s3.json").write_text(json.dumps([self.GATE]))      # only one of the two keys
        self.run_pass()
        self.assertEqual(self.cl(), {})
        out = self.wd("task", "show", "t1")[1]
        self.assertIn("waiting-on %s" % two, out)
        self.assertNotIn("waiting-on %s" % self.GATE, out)
        (self.fake / "s3.json").write_text(json.dumps([self.GATE, two]))
        self.run_pass()
        self.assertIn("t1-g", self.cl(), "submitted on the first pass after the last key appeared")
        self.assertEqual(self.task()["stages"][0]["state"], "running")
        self.assertTrue(any("every after_s3 key exists" in e for e in self.task()["events"]))

    def test_after_s3_waiting_stage_does_not_block_other_stages(self):
        free = {"id": "f", "job": "t1-f", "manifest": self.manifest("t1-f"), "done_s3": ["s3://braingeneersdev/t/f.txt"]}
        self.assertEqual(self.gated(extra=[free])[0], 0)
        self.run_pass()
        self.assertIn("t1-f", self.cl())
        self.assertNotIn("t1-g", self.cl())

    def test_after_s3_combines_with_after(self):
        stages = [{"id": "a", "job": "t1-a", "manifest": self.manifest("t1-a"), "done_s3": ["s3://braingeneersdev/t/a.txt"]},
                  {"id": "b", "job": "t1-b", "manifest": self.manifest("t1-b"), "after": ["a"], "after_s3": [self.GATE],
                   "done_s3": ["s3://braingeneersdev/t/b.txt"]}]
        self.assertEqual(self.add(stages=stages)[0], 0)
        (self.fake / "s3.json").write_text(json.dumps([self.GATE]))      # the key is there but stage a is not done
        self.run_pass()
        self.assertIn("t1-a", self.cl())
        self.assertNotIn("t1-b", self.cl())
        self.set_job("t1-a", state="ok")
        (self.fake / "s3.json").write_text(json.dumps([self.GATE, "s3://braingeneersdev/t/a.txt"]))
        self.run_pass()
        self.assertIn("t1-b", self.cl())

    def test_after_s3_dry_run_says_waiting_and_changes_nothing(self):
        self.gated()
        before = (self.state / "tasks/t1/task.json").read_text()
        rc, out, err = self.wd("run", "--dry-run", "--tasks-only")
        self.assertEqual(rc, 0, err)
        self.assertIn("waits on %s" % self.GATE, out)
        self.assertNotIn("would submit", out)
        self.assertEqual(before, (self.state / "tasks/t1/task.json").read_text())
        (self.fake / "s3.json").write_text(json.dumps([self.GATE]))
        self.assertIn("would submit stage g", self.wd("run", "--dry-run", "--tasks-only")[1])
        self.assertEqual(self.cl(), {})

    def test_stage_without_after_s3_is_unchanged(self):
        self.add()
        self.assertNotIn("after_s3", self.task()["stages"][0])
        self.run_pass()
        self.assertIn("t1-a", self.cl())


if __name__ == "__main__":
    unittest.main(verbosity=1)

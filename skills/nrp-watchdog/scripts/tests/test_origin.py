#!/usr/bin/env python3
"""Tests for origin attribution (which chat a person returns to). Reuses the fake kubectl/aws/claude harness of test_tasks.
Nothing real is sent: Slack payloads are captured by a local HTTP stub on 127.0.0.1 (never notification-service) and
pushes otherwise go to the fake banner log. Run: python3 tests/test_origin.py"""
import fcntl
import http.server
import importlib.machinery
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_tasks as tt                                    # harness only; its TestCase is not re-collected from here

SCRIPT = tt.SCRIPT
_TMP = tempfile.mkdtemp(prefix="wdorigin_mod_")
os.environ["NRP_WATCHDOG_STATE"] = _TMP                    # the module-level STATE of the imported script
os.environ["NRP_WATCHDOG_OWNER_NAME"] = "Sam"                 # how messages name the person (setting owner_name)
WD = importlib.machinery.SourceFileLoader("wd_under_test", SCRIPT).load_module()

RT = {"title": "rt-sort-3d", "link": "t3-thread://v2/9287f026-7701-4dd7-9c6f-f015440d149e/5488c222-111b-479b-899d-141dbb803bfd",
      "assistant": "Codex gpt-6-astra", "collaborator": "Sam"}


class Pure(unittest.TestCase):
    def test_norm_origin_accepts_t3_link_with_angle_brackets_and_defaults_collaborator(self):
        o = WD.norm_origin({"title": " rt-sort-3d ", "link": "<%s>" % RT["link"], "assistant": "Codex gpt-6-astra"})
        self.assertEqual(o["link"], RT["link"])
        self.assertEqual(o["title"], "rt-sort-3d")
        self.assertEqual(o["collaborator"], "Sam")
        self.assertEqual(o["source"], "registered")

    def test_norm_origin_refuses_bad_input(self):
        for bad in ("a string", {"title": "x", "color": "red"}, {"assistant": "Codex"}, {"title": "x", "link": "t3 thread"},
                    {"title": "x", "link": "t3-thread://a|b"}, {"link": "javascript:alert(1)"}):
            with self.assertRaises(WD.ChainError, msg=repr(bad)):
                WD.norm_origin(bad)
        self.assertIsNone(WD.norm_origin(None))
        self.assertIsNone(WD.norm_origin({}))

    def test_backticks_and_newlines_cannot_break_slack_formatting(self):
        o = WD.norm_origin({"title": "evil`code\nsecond line", "link": RT["link"]})
        self.assertNotIn("`", o["title"])
        self.assertNotIn("\n", o["title"])

    def test_slack_escaping_and_literal_link(self):
        o = WD.norm_origin({"title": "A & B <!channel>", "link": RT["link"], "assistant": "Codex <x>"})
        text = "\n".join(WD.origin_slack(o))
        self.assertIn("*Return to chat: A &amp; B &lt;!channel&gt;*", text)
        self.assertIn("(Codex &lt;x&gt;, working with Sam)", text)
        self.assertIn("`%s`" % RT["link"], text, "custom-scheme links stay literal, not <url|label>")
        self.assertNotIn("<!channel>", text)
        web = WD.origin_slack(WD.norm_origin({"title": "Doc", "link": "https://example.org/a?b=1&c=2"}))
        self.assertEqual(web, ["*Return to chat: <https://example.org/a?b=1&c=2|Doc>* (working with Sam)"])

    def test_missing_origin_wording(self):
        self.assertEqual(WD.origin_slack(None, "task t9: goal"), ["*origin not recorded* (task t9: goal)"])
        self.assertTrue(WD.origin_plain(None).startswith("origin not recorded"))
        self.assertEqual(WD.origin_tag(None), "[origin not recorded]")

    def test_system_alert_is_not_attributed_to_a_chat(self):
        text = WD.slack_text("kubectl has failed 6 passes <x>", [])
        self.assertTrue(text.startswith("*Not tied to one chat*"))
        self.assertIn("kubectl has failed 6 passes &lt;x&gt;", text)
        self.assertIn("*NRP watchdog* (automated script, working with Sam; not a chat)", text)
        self.assertEqual(WD.short_tag([]), "[shared] ")


class Stub(http.server.BaseHTTPRequestHandler):
    got = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        Stub.got.append((self.headers.get("Authorization"), json.loads(body)))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status":"delivered"}')

    def log_message(self, *a):
        pass


class O(unittest.TestCase):
    setUp, tearDown = tt.T.setUp, tt.T.tearDown
    wd, tool, manifest, add, task, cl, set_job, plan, pushes, prompts, run_pass = (
        tt.T.wd, tt.T.tool, tt.T.manifest, tt.T.add, tt.T.task, tt.T.cl, tt.T.set_job, tt.T.plan, tt.T.pushes, tt.T.prompts, tt.T.run_pass)

    def fail(self, job="t1-a"):
        self.set_job(job, state="FAILED", term={"reason": "OOMKilled", "exitCode": 137})

    def test_origin_is_persisted_shown_and_survives_retry_resume_and_agent_prompt(self):
        rc, out, err = self.add(mode="auto", origin=RT)
        self.assertEqual(rc, 0, err)
        self.assertNotIn("warning", err)
        self.assertEqual(self.task()["origin"]["link"], RT["link"])
        self.run_pass()
        self.fail()                                                       # auto mode: fix agent, silent retry
        self.plan({"cmds": [["sh", "sed -i '' 's/512Mi/1Gi/g' %s" % self.task()["stages"][0]["manifest"]],
                            ["nrp-task", "submit", "t1-a", "--reason", "OOM 512Mi -> 1Gi"],
                            ["nrp-task", "report", "RESUBMITTED", "OOM -> 1Gi"]], "result": "RESUBMITTED"})
        self.run_pass()
        prompt = self.prompts()[0].read_text()
        self.assertIn('Origin: chat "rt-sort-3d" (Codex gpt-6-astra, with Sam) ' + RT["link"], prompt)
        self.assertIn("not that chat", prompt, "the repair agent is told it is not the origin chat")
        self.assertEqual(self.task()["origin"]["title"], "rt-sort-3d")
        # same failure again -> NEEDS_OWNER (a push naming the chat), then a person resumes
        self.fail()
        self.run_pass()
        self.run_pass()
        self.assertEqual(self.task()["status"], "NEEDS_OWNER")
        self.assertEqual(len(self.pushes()), 1)
        self.assertIn("[rt-sort-3d] NRP task t1 needs you", self.pushes()[0])
        rc, out, err = self.wd("task", "resume", "t1", "--note", "decided")
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.task()["origin"], dict(self.task()["origin"], **RT))
        rc, out, _ = self.wd("task", "show", "t1")
        self.assertIn('origin: chat "rt-sort-3d" (Codex gpt-6-astra, with Sam) ' + RT["link"], out)
        rc, out, _ = self.wd("task", "list")
        self.assertIn("<rt-sort-3d>", out)

    def test_missing_origin_warns_stores_none_and_falls_back_to_goal_and_repo(self):
        rc, out, err = self.add(mode="watch", code={"repo": str(self.repo), "subdir": "job"})
        self.assertEqual(rc, 0, err)
        self.assertIn("has no origin", err)
        self.assertIsNone(self.task()["origin"])
        self.run_pass()
        self.fail()
        self.run_pass()
        self.assertIn("[origin not recorded] NRP task t1 needs you", self.pushes()[0])
        rc, out, _ = self.wd("task", "show", "t1")
        self.assertIn("origin: origin not recorded (no chat recorded; goal and code repo above identify it)", out)
        rc, out, _ = self.wd("digest")
        self.assertIn("t1 (origin not recorded (goal: test task t1))", out)
        rc, out, _ = self.wd("origin", "task", "t1")
        self.assertIn("origin not recorded", out)

    def test_require_flag_refuses_missing_origin(self):
        self.env["NRP_WATCHDOG_REQUIRE_ORIGIN"] = "1"
        rc, out, err = self.add()
        self.assertEqual(rc, 1)
        self.assertIn("task refused" if "task refused" in err else "refused", err)
        self.assertFalse((self.state / "tasks" / "t1").exists())
        rc, out, err = self.add(origin=RT)
        self.assertEqual(rc, 0, err)

    def test_flags_override_json_and_bad_link_is_refused(self):
        rc, out, err = self.add(origin={"title": "old", "link": RT["link"]})
        self.assertEqual(rc, 0, err)
        f = self.tmp / "t2.json"
        spec = json.loads((self.tmp / "t1.json").read_text())
        spec["name"] = "t2"
        spec["stages"] = [{"id": "a", "job": "t2-a", "manifest": self.manifest("t2-a"), "done_s3": ["s3://braingeneersdev/alice/test/t2/a.txt"]}]
        f.write_text(json.dumps(spec))
        rc, out, err = self.wd("task", "add", str(f), "--origin-title", "new title", "--origin-assistant", "Claude Opus")
        self.assertEqual(rc, 0, err)
        o = self.task("t2")["origin"]
        self.assertEqual((o["title"], o["link"], o["assistant"]), ("new title", RT["link"], "Claude Opus"))
        spec["name"] = "t3"
        spec["stages"][0].update(id="a", job="t3-a", manifest=self.manifest("t3-a"))
        f.write_text(json.dumps(spec))
        rc, out, err = self.wd("task", "add", str(f), "--origin-link", "not a link")
        self.assertEqual(rc, 1)
        self.assertIn("origin.link", err)

    def test_backfill_is_metadata_only_needs_evidence_and_refuses_overwrite(self):
        self.add(mode="watch")
        self.run_pass()
        self.fail()
        self.run_pass()
        before = self.task()
        self.assertEqual(before["status"], "NEEDS_OWNER")
        rc, out, err = self.wd("origin", "task", "t1", "--title", RT["title"], "--link", RT["link"])
        self.assertEqual(rc, 1)
        self.assertIn("--evidence is required", err)
        self.assertIsNone(self.task()["origin"])
        rc, out, err = self.wd("origin", "task", "t1", "--title", RT["title"], "--link", RT["link"], "--assistant", RT["assistant"],
                               "--evidence", "T3 thread_read 2026-11-05: title, provider; task code repo is its checkout")
        self.assertEqual(rc, 0, err)
        after = self.task()
        o = after["origin"]
        self.assertEqual((o["title"], o["link"], o["collaborator"]), (RT["title"], RT["link"], "Sam"))
        self.assertTrue(o["source"].startswith("backfilled "))
        self.assertIn("thread_read", o["evidence"])
        strip = lambda t: {k: v for k, v in t.items() if k not in ("origin", "events")}
        self.assertEqual(strip(before), strip(after), "status, stages, approval, attempts, failure untouched")
        self.assertEqual(self.cl()["t1-a"]["state"], "FAILED", "nothing submitted or deleted")
        rc, out, err = self.wd("origin", "task", "t1", "--title", "other", "--evidence", "x")
        self.assertEqual(rc, 1)
        self.assertIn("already has origin", err)
        rc, out, err = self.wd("origin", "task", "t1", "--title", "rt-sort-3d (renamed)", "--evidence", "renamed", "--replace")
        self.assertEqual(rc, 0, err)
        o = self.task()["origin"]
        self.assertEqual((o["title"], o["link"], o["assistant"]), ("rt-sort-3d (renamed)", RT["link"], RT["assistant"]))
        rc, out, err = self.wd("origin", "task", "nosuch", "--title", "x", "--evidence", "x")
        self.assertEqual(rc, 1)
        self.assertIn("no task named nosuch", err)

    def test_backfill_waits_for_the_runners_state_lock(self):
        self.add(mode="watch")
        lock = open(self.state / "state.lock", "a+")
        fcntl.flock(lock, fcntl.LOCK_EX)
        p = subprocess.Popen([str(self.bin / "nrp-watchdog"), "origin", "task", "t1", "--title", "x", "--link", RT["link"], "--evidence", "e"],
                             env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(0.8)
        self.assertIsNone(p.poll(), "must block while the runner holds state.lock")
        self.assertIsNone(self.task()["origin"])
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
        p.wait(timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr.read())
        self.assertEqual(self.task()["origin"]["title"], "x")

    def test_slack_payload_for_a_task_escalation_names_the_origin_chat(self):
        srv = http.server.HTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        jwt = self.tmp / "jwt.json"
        jwt.write_text('{"access_token": "fake.jwt.token"}')
        env = {k: v for k, v in self.env.items() if k != "NRP_WATCHDOG_NO_PUSH"}
        env.update(NRP_WATCHDOG_JWT=str(jwt), NRP_WATCHDOG_SLACK_URL="http://127.0.0.1:%d/v1/slack" % srv.server_port, NRP_WATCHDOG_SLACK_USER="UTEST")
        self.env = env
        Stub.got.clear()
        rc, out, err = self.add(mode="watch", origin=dict(RT, title="rt-sort-3d <&>"))
        self.assertEqual(rc, 0, err)
        self.run_pass()
        self.set_job("t1-a", state="FAILED", term={"reason": "Error", "exitCode": 1}, log="shard check <FAILED> & <!channel>: 2 of 16")
        self.run_pass()
        srv.shutdown()
        self.assertEqual(len(Stub.got), 1, (self.state / "watchdog.log").read_text()[-1500:])
        auth, payload = Stub.got[0]
        self.assertEqual(auth, "Bearer fake.jwt.token")
        self.assertEqual(payload["user_id"], "UTEST")
        lines = payload["text"].split("\n")
        self.assertEqual(lines[0], "*Return to chat: rt-sort-3d &lt;&amp;&gt;* (Codex gpt-6-astra, working with Sam)")
        self.assertEqual(lines[1], "`%s`" % RT["link"])
        self.assertTrue(lines[2].startswith("*NRP watchdog* (automated script, working with Sam; not a chat): NRP task t1 needs you:"))
        self.assertNotIn("<!channel>", payload["text"])
        self.assertIn("&lt;!channel&gt;", payload["text"])
        pushed = json.loads((self.state / "pushed.json").read_text())["task:t1:1"]
        self.assertTrue(pushed["msg"].startswith("[rt-sort-3d <&>] "))
        self.assertIn("rt-sort-3d <&>", pushed["origin"][0])

    def test_slack_payload_without_origin_says_so_and_names_goal(self):
        text = self._text_for_unrecorded_task()
        self.assertTrue(text.startswith("*origin not recorded* (task t1: test task t1)"), text)

    def _text_for_unrecorded_task(self):
        self.add(mode="watch")
        env = dict(self.env, NRP_WATCHDOG_STATE=str(self.state))
        code = ("import importlib.machinery as m,sys;w=m.SourceFileLoader('w',sys.argv[1]).load_module();print(w.slack_text('boom', ['task:t1']))")
        r = subprocess.run([sys.executable, "-c", code, SCRIPT], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_digest_labels_old_events_with_a_backfilled_origin(self):
        self.add(mode="watch")
        rc, out, _ = self.wd("digest")
        self.assertIn("[t1 · origin not recorded]", out)
        self.wd("origin", "task", "t1", "--title", RT["title"], "--link", RT["link"], "--evidence", "verified")
        rc, out, _ = self.wd("digest")
        self.assertIn("[t1 · rt-sort-3d]", out)
        self.assertIn("not by one chat", out)

    def test_chain_origin_add_show_backfill_and_stop_alert(self):
        step = {"id": "a", "job": "c-a", "cwd": str(self.tmp), "argv": ["/bin/echo", "x"], "state": "running"}
        spec = {"name": "c1", "owner": "some owner", "steps": [step], "origin": RT}
        f = self.tmp / "c1.json"
        f.write_text(json.dumps(spec))
        rc, out, err = self.wd("chain", "add", str(f))
        self.assertEqual(rc, 0, err)
        rc, out, _ = self.wd("chain", "show", "c1")
        self.assertIn('origin: chat "rt-sort-3d"', out)
        spec.pop("origin")
        spec["name"] = "c2"
        spec["steps"] = [dict(step, job="c-b")]
        f.write_text(json.dumps(spec))
        rc, out, err = self.wd("chain", "add", str(f))
        self.assertEqual(rc, 0)
        self.assertIn("has no origin", err)
        rc, out, _ = self.wd("chain", "show", "c2")
        self.assertIn("origin not recorded (owner field: some owner)", out)
        rc, out, err = self.wd("origin", "chain", "c2", "--title", "finch", "--link", RT["link"], "--evidence", "verified by parent")
        self.assertEqual(rc, 0, err)
        self.set_job("c-a", state="FAILED")
        self.set_job("c-b", state="FAILED")
        rc, out, err = self.wd("run")
        self.assertEqual(rc, 0, err)
        pushes = self.pushes()
        self.assertEqual(len(pushes), 2, pushes)
        joined = "\n".join(pushes)
        self.assertIn("[rt-sort-3d] chain c1 STOPPED", joined)
        self.assertIn("[finch] chain c2 STOPPED", joined)

    def test_legacy_add_records_origin_and_a_same_job_reregistration_keeps_it(self):
        rc, out, err = self.wd("add", "legacy-1", "--label", "old job", "--origin-title", "rt-sort-3d", "--origin-link", RT["link"])
        self.assertEqual(rc, 0, err)
        self.assertIn('chat "rt-sort-3d"', out)
        jobs = json.loads((self.state / "jobs.json").read_text())["jobs"]
        self.assertEqual(jobs["legacy-1"]["origin"]["link"], RT["link"])
        rc, out, err = self.wd("add", "legacy-1", "--label", "old job again")      # a repair agent re-registers the same Job
        self.assertEqual(rc, 0, err)
        self.assertNotIn("has no origin", err)
        jobs = json.loads((self.state / "jobs.json").read_text())["jobs"]
        self.assertEqual(jobs["legacy-1"]["origin"]["title"], "rt-sort-3d")
        rc, out, err = self.wd("add", "legacy-2", "--label", "no origin")
        self.assertIn("has no origin", err)
        self.assertNotIn("origin", json.loads((self.state / "jobs.json").read_text())["jobs"]["legacy-2"])
        rc, out, err = self.wd("origin", "job", "legacy-2", "--title", "t", "--link", RT["link"], "--evidence", "e")
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads((self.state / "jobs.json").read_text())["jobs"]["legacy-2"]["origin"]["title"], "t")


if __name__ == "__main__":
    unittest.main(verbosity=1)

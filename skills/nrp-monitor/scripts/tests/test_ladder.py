#!/usr/bin/env python3
"""v3 task escalation ladder and Tier 0 deadline rules. Same harness as test_tasks.py (fake kubectl / aws / osascript / claude, scratch state
dir, real `nrp-task`), plus a fake `kubectl patch` and a local HTTP server standing in for the coordinator chat's webhook relay.
Run: python3 tests/test_ladder.py"""
import json
import os
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_tasks  # noqa: E402

PATCH_BRANCH = '''elif a[0] == "patch":
    n = a[2]; body = json.loads(a[a.index("-p") + 1])
    if n not in cl["jobs"]: sys.stderr.write('Error from server (NotFound): jobs "%s" not found\\n' % n); sys.exit(1)
    cl["jobs"][n]["deadline"] = body["spec"]["activeDeadlineSeconds"]; save()
    open(d + "/patched.log", "a").write("%s %s\\n" % (n, body["spec"]["activeDeadlineSeconds"])); print("job.batch/%s patched" % n)
'''
KUBECTL = test_tasks.FAKE_KUBECTL.replace('elif a[:2] == ["create", "configmap"]:', PATCH_BRANCH + 'elif a[:2] == ["create", "configmap"]:')
assert PATCH_BRANCH in KUBECTL


class Relay(BaseHTTPRequestHandler):
    status = 200
    received = []

    def do_POST(self):
        self.received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        self.send_response(self.status)
        self.end_headers()

    def log_message(self, *args):
        pass


class Ladder(unittest.TestCase):
    pass


for _k, _v in vars(test_tasks.T).items():          # the harness helpers only: not test_tasks' own tests (they would run twice)
    if not _k.startswith("test_"):
        setattr(Ladder, _k, _v)
_base_setup = test_tasks.T.setUp


def _setUp(self):
    _base_setup(self)
    (self.bin / "kubectl").write_text(KUBECTL)
    Relay.status, Relay.received = 200, []
    self.server = HTTPServer(("127.0.0.1", 0), Relay)
    threading.Thread(target=self.server.serve_forever, daemon=True).start()


def _tearDown(self):
    self.server.shutdown()
    self.server.server_close()
    test_tasks.T.tearDown(self)


Ladder.setUp, Ladder.tearDown = _setUp, _tearDown


class LadderTests(Ladder):
    # ---------------------------------------------------------------- helpers
    def webhook(self, name="t1"):
        p = self.state / "webhooks" / name
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps({"url": "http://127.0.0.1:%d/hook" % self.server.server_port, "workstream": "coord"}))
        p.chmod(0o600)

    def write_task(self, fn, n="t1"):
        p = self.state / "tasks" / n / "task.json"
        t = json.loads(p.read_text())
        fn(t)
        p.write_text(json.dumps(t))

    def inject_failure(self, cls="infra", sig="stuck:pod-x", detail="pod x STUCK creating 142 min", n="t1"):
        def f(t):
            t["stages"][0]["state"] = "failed"
            t["failure"] = {"stage": "a", "job": t["stages"][0]["job"], "cls": cls, "sig": sig, "detail": detail, "logs": None, "ts": time.time()}
        self.write_task(f, n)

    def triage_says(self, text):
        (self.fake / "claude_out").write_text(text)

    def agent_models(self):
        return [json.loads(l)[json.loads(l).index("--model") + 1] for l in (self.fake / "claude_args.log").read_text().splitlines()]

    def events(self):
        return "\n".join(self.task()["events"])

    def unknown_failure(self):
        """A real script-classified `unknown` failure: the Job failed with no traceback and no exit reason."""
        self.run_pass()
        self.set_job("t1-a", state="FAILED", term={"reason": "Error", "exitCode": 1}, log="worker finished item 17 then went quiet")

    def sonnet_plan_stop(self, line="STOPPED: cannot tell why the worker stopped"):
        self.plan({"cmds": [["nrp-task", "report", "STOPPED", line[9:]]], "result": line})

    # ---------------------------------------------------------------- Tier 1: benign / no fix needed closes the event
    def test_benign_closes_the_event_without_owner_or_fix_agent(self):
        self.add()
        self.webhook()
        self.run_pass()
        self.set_job("t1-a", state="running", started=time.time() - 120)
        self.inject_failure()
        self.triage_says("CLOSE: the pod started 2 min ago and is writing logs")
        self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "running")
        self.assertIsNone(t["failure"])
        self.assertEqual(t["stages"][0]["state"], "running")
        self.assertEqual(len(self.prompts()), 1, "only the triage agent ran")
        self.assertEqual(self.agent_models(), ["haiku"])
        self.assertEqual(self.pushes(), [])
        self.assertEqual([e for e in Relay.received if e["event_type"] == "escalation"], [], "the coordinator is not woken either")
        self.assertIn("closed by Tier 1 triage", self.events())
        self.assertIn("triage-closed", (self.state / "digest.log").read_text())
        self.assertEqual(self.task()["attempts"], [], "no retry was used")

    def test_no_fix_needed_also_closes_and_triage_is_read_only(self):
        self.add()
        self.run_pass()
        self.set_job("t1-a", state="running", started=time.time() - 120)
        self.inject_failure()
        self.triage_says("CLOSE: running normally")
        self.run_pass()
        self.assertEqual(self.task()["status"], "running")
        args = json.loads((self.fake / "claude_args.log").read_text().splitlines()[0])
        allowed = args[args.index("--allowedTools") + 1:]
        self.assertTrue(allowed and all(a.startswith(("Bash(nrp-task show", "Bash(nrp-task logs", "Bash(nrp-task describe", "Bash(nrp-task util",
                                                       "Bash(nrp-task s3", "Read(")) for a in allowed), allowed)
        self.assertNotIn("Edit", " ".join(allowed))
        self.assertNotIn("Bash(nrp-task:*)", allowed)

    def test_benign_on_a_dead_job_is_refused_by_the_script(self):
        """The script decides, not the verdict: a CLOSE for a Job that failed and left no outputs goes on to Tier 2."""
        self.add()
        self.unknown_failure()
        self.triage_says("CLOSE: looks fine to me")
        self.sonnet_plan_stop()
        self.run_pass()
        self.assertEqual(len(self.prompts()), 2)
        self.assertIn("refused to close", self.events())
        self.assertEqual(self.task()["status"], "NEEDS_OWNER")             # no webhook here: the fallback

    def test_util_failures_receive_judge_review(self):
        """Tier 2's UTIL_OK waiver is the util 'no fix needed' path; Haiku is not asked about NRP-counted utilization."""
        self.add()
        self.run_pass()
        self.set_job("t1-a", state="running", started=time.time() - 120)
        self.inject_failure(cls="util", sig="util:cpu@512Mi", detail="pod outside NRP utilization bands")
        self.triage_says("ESCALATE: resize needs review")
        self.sonnet_plan_stop("STOPPED: resize needed")
        self.run_pass()
        self.assertEqual(self.agent_models(), ["haiku", "sonnet"])

    # ---------------------------------------------------------------- Tier 2: Sonnet fix after Haiku escalates
    def test_haiku_escalates_then_sonnet_fixes_silently(self):
        self.add()
        self.unknown_failure()
        self.triage_says("ESCALATE: the worker died after item 17 with no error; needs a look at the code")
        self.plan({"cmds": [["nrp-task", "submit", "t1-a", "--reason", "worker hung -> resubmit"],
                            ["nrp-task", "report", "RESUBMITTED", "resubmitted"]], "result": "RESUBMITTED: worker hung"})
        self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "retrying")
        self.assertEqual(self.agent_models(), ["haiku", "sonnet"])
        fix = self.prompts()[1].read_text()
        self.assertIn("TIER 1 TRIAGE", fix)
        self.assertIn("ESCALATE: the worker died after item 17", fix, "Tier 2 starts from Tier 1's diagnosis")
        self.assertEqual(self.pushes(), [])
        self.assertIn("Tier 1 triage: ESCALATE", self.events())

    def test_triage_is_recorded_on_the_failure_so_it_runs_once(self):
        self.add()
        self.unknown_failure()
        self.triage_says("ESCALATE: unclear")
        self.sonnet_plan_stop()
        self.run_pass()
        f = self.task()["failure"]
        self.assertTrue(f.get("triaged"))
        self.assertTrue(f["triage_text"].startswith("ESCALATE: unclear"))
        self.run_pass()
        self.assertEqual(self.agent_models().count("haiku"), 1)

    def test_terminal_classified_failure_skips_tier_1(self):
        self.add()
        self.run_pass()
        self.set_job("t1-a", state="FAILED", term={"reason": "OOMKilled", "exitCode": 137})
        self.plan({"cmds": [["nrp-task", "report", "STOPPED", "x"]], "result": "STOPPED: x"})
        self.run_pass()
        self.assertEqual(self.agent_models(), ["sonnet"])

    # ---------------------------------------------------------------- Tier 3: the coordinator chat, not the owner
    def test_sonnet_stop_wakes_the_coordinator_not_the_owner(self):
        self.add(origin={"title": "BWB FT prep", "link": "t3-thread://abc"})
        self.webhook()
        self.unknown_failure()
        self.triage_says("ESCALATE: unclear")
        self.sonnet_plan_stop()
        self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "WITH_COORDINATOR")
        self.assertEqual(self.pushes(), [], "the owner is NOT notified")
        self.assertIn("cannot tell why the worker stopped", t["reason"])
        wake = [e for e in Relay.received if e["event_type"] == "escalation"]
        self.assertEqual(len(wake), 1, Relay.received)
        self.assertEqual(wake[0]["workstream"], "coord")
        self.assertEqual(wake[0]["task"], "t1")
        self.assertIn("nrp-monitor task show t1", wake[0]["summary"])
        self.assertIn("task needs-owner t1", wake[0]["summary"])
        self.assertIn("task resume t1", wake[0]["summary"])
        self.assertLess(len(wake[0]["summary"]), 1700)
        self.assertFalse(any(e["event_type"] == "escalation" for e in t["webhook_outbox"]), "delivered, so acknowledged")
        rc, out, _ = self.wd("status", "--quiet")
        self.assertIn("wait on their coordinator chat", out)
        self.assertNotIn("need the owner", out)
        rc, out, _ = self.wd("digest")
        self.assertIn("With the coordinator chat, owner not notified (1)", out)
        self.assertIn("## Needs the owner (0)", out)

    def test_repeat_after_a_fix_goes_straight_to_the_coordinator(self):
        self.add()
        self.webhook()
        self.run_pass()
        self.set_job("t1-a", state="FAILED", term={"reason": "OOMKilled", "exitCode": 137})
        self.write_task(lambda t: t["attempts"].append({"stage": "a", "job": "t1-a", "cls": "resources", "sig": "oom@512Mi", "detail": "d",
                                                         "fix": "doubled memory", "by": "agent", "ts": time.time()}))
        self.run_pass()
        self.assertEqual(self.task()["status"], "WITH_COORDINATOR")
        self.assertEqual(self.prompts(), [], "no agent: it already failed the same way after its own fix")
        self.assertEqual(self.pushes(), [])

    def test_coordinator_calls_needs_owner_and_only_then_the_owner_is_told(self):
        self.add()
        self.webhook()
        self.unknown_failure()
        self.sonnet_plan_stop()
        self.run_pass()
        self.assertEqual(self.task()["status"], "WITH_COORDINATOR")
        self.assertEqual(self.pushes(), [])
        rc, out, err = self.wd("task", "needs-owner", "t1", "--reason", "the new filter changes the science: which threshold do you want?")
        self.assertEqual(rc, 0, err)
        t = self.task()
        self.assertEqual(t["status"], "NEEDS_OWNER")
        self.assertIn("which threshold", t["reason"])
        self.assertEqual(len(self.pushes()), 1)
        self.assertIn("which threshold", self.pushes()[0])
        rc, out, err = self.wd("task", "needs-owner", "t1", "--reason", "again, a second time")
        self.assertNotEqual(rc, 0, "already NEEDS_OWNER")
        self.assertEqual(len(self.pushes()), 1, "one DM only")

    def test_needs_owner_refuses_short_reason_and_finished_tasks(self):
        self.add()
        rc, _, err = self.wd("task", "needs-owner", "t1", "--reason", "x")
        self.assertNotEqual(rc, 0)
        rc, _, err = self.wd("task", "needs-owner", "nosuch", "--reason", "a long enough reason here")
        self.assertNotEqual(rc, 0)
        self.assertEqual(self.pushes(), [])

    def test_coordinator_hands_back_with_resume(self):
        self.add()
        self.webhook()
        self.unknown_failure()
        self.sonnet_plan_stop()
        self.run_pass()
        rc, out, err = self.wd("task", "resume", "t1", "--note", "patched the worker, resubmit")
        self.assertEqual(rc, 0, err)
        t = self.task()
        self.assertEqual(t["status"], "running")
        self.assertIn("resumed by the coordinator chat", self.events())
        self.run_pass()
        self.assertEqual(self.cl()["t1-a"]["state"], "running", "the failed stage was resubmitted")
        self.assertEqual(self.pushes(), [])

    def test_wake_delivery_failure_falls_back_to_the_owner(self):
        self.add()
        self.webhook()
        Relay.status = 503
        self.unknown_failure()
        self.sonnet_plan_stop()
        self.run_pass()
        self.assertEqual(self.task()["status"], "WITH_COORDINATOR")
        self.assertEqual(self.pushes(), [])
        for _ in range(self.mod_wake_tries() - 1):
            self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "NEEDS_OWNER")
        self.assertIn("could not be woken", t["reason"])
        self.assertIn("cannot tell why the worker stopped", t["reason"], "the original diagnosis is kept")
        self.assertEqual(len(self.pushes()), 1)
        self.assertFalse(any(e["event_type"] == "escalation" for e in t.get("webhook_outbox", [])))

    def mod_wake_tries(self):
        import re
        return int(re.search(r"^WAKE_MAX_TRIES = (\d+)", Path(test_tasks.SCRIPT).read_text(), re.M).group(1))

    def test_no_webhook_means_the_owner_is_told(self):
        self.add()
        self.unknown_failure()
        self.sonnet_plan_stop()
        self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "NEEDS_OWNER")
        self.assertIn("no coordinator webhook", t["reason"])
        self.assertEqual(len(self.pushes()), 1)

    def test_unanswered_wake_goes_to_the_owner_after_a_day(self):
        self.add()
        self.webhook()
        self.unknown_failure()
        self.sonnet_plan_stop()
        self.run_pass()
        self.assertEqual(self.task()["status"], "WITH_COORDINATOR")
        self.run_pass()
        self.assertEqual(self.task()["status"], "WITH_COORDINATOR", "not yet")
        self.write_task(lambda t: t.update(coordinator_since=time.time() - 25 * 3600))
        self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "NEEDS_OWNER")
        self.assertIn("did not answer", t["reason"])
        self.assertEqual(len(self.pushes()), 1)

    def test_watch_mode_and_gpu_stops_still_go_to_the_owner(self):
        self.add(mode="watch")
        self.webhook()
        self.run_pass()
        self.set_job("t1-a", state="FAILED", term={"reason": "OOMKilled", "exitCode": 137})
        self.run_pass()
        self.assertEqual(self.task()["status"], "NEEDS_OWNER")
        self.assertEqual(len(self.pushes()), 1)

    def test_resumable_field_is_validated(self):
        stages = [{"id": "a", "job": "t1-a", "manifest": self.manifest("t1-a"), "done_s3": ["s3://braingeneersdev/x/a"], "resumable": "yes"}]
        rc, _, err = self.add(stages=stages)
        self.assertNotEqual(rc, 0)
        self.assertIn("resumable", err)
        stages[0]["resumable"] = True
        self.assertEqual(self.add(stages=stages)[0], 0)
        self.assertTrue(self.task()["stages"][0]["resumable"])

    # ---------------------------------------------------------------- Tier 0 deadlines
    def run_job(self, **kw):
        self.add(**kw.pop("task", {}))
        self.run_pass()

    def patched(self):
        p = self.fake / "patched.log"
        return p.read_text().splitlines() if p.exists() else []

    def test_progressing_job_near_its_deadline_is_extended_in_place(self):
        self.run_job()
        now = time.time()
        self.set_job("t1-a", state="running", deadline=3600, start=now - 3000, started=now - 2900, log="item 100\nitem 101")
        self.run_pass()                                           # records pod_started and the first log sample
        self.assertEqual(self.patched(), [])
        self.set_job("t1-a", log="item 100\nitem 101\nitem 102")
        self.run_pass()                                           # the log advanced and 10 min remain
        self.assertEqual(self.patched(), ["t1-a 7200"])
        self.assertEqual(self.cl()["t1-a"]["deadline"], 7200)
        self.assertIn("still progressing", self.events())
        self.assertIn("deadline-extended", (self.state / "digest.log").read_text())
        self.assertEqual(self.task()["status"], "running")
        self.assertEqual(self.prompts(), [])
        self.assertEqual(self.pushes(), [])

    def test_extensions_are_capped(self):
        self.run_job()
        now = time.time()
        self.set_job("t1-a", state="running", deadline=3600, start=now - 3000, started=now - 2900, log="a")
        self.run_pass()
        for i in range(5):
            # each extension adds one original deadline; move the clock so the Job is near its (new) deadline again
            c = self.cl()["t1-a"]
            self.set_job("t1-a", start=time.time() - (c["deadline"] - 600), log="line %d" % i)
            self.run_pass()
        self.assertEqual(len(self.patched()), 2, self.patched())
        self.assertIn("extensions were used", self.events())

    def test_job_that_is_not_progressing_is_left_to_expire(self):
        self.run_job()
        now = time.time()
        self.set_job("t1-a", state="running", deadline=3600, start=now - 3000, started=now - 2900, log="stuck on item 7")
        self.run_pass()
        self.run_pass()                                           # same log tail twice: no progress
        self.assertEqual(self.patched(), [])
        self.assertIn("did not advance", self.events())

    def test_queue_time_is_credited_once_the_pod_starts(self):
        self.run_job()
        now = time.time()
        # 2 h deadline, the pod waited 30 min Pending and started 10 min ago
        self.set_job("t1-a", state="running", deadline=7200, start=now - 2400, started=now - 600, log="x")
        self.run_pass()
        self.assertEqual(self.patched(), ["t1-a 9000"], "original 7200 s + 1800 s Pending")
        self.assertIn("credited 30 min", self.events())
        self.run_pass()
        self.assertEqual(len(self.patched()), 1, "credited once")

    def test_short_queue_is_not_credited(self):
        self.run_job()
        now = time.time()
        self.set_job("t1-a", state="running", deadline=7200, start=now - 400, started=now - 300, log="x")
        self.run_pass()
        self.assertEqual(self.patched(), [])

    def test_pending_job_near_deadline_is_kept_alive_and_then_credited(self):
        self.run_job()
        now = time.time()
        self.set_job("t1-a", state="running", deadline=3600, start=now - 3000)     # no pod started: still Pending
        self.run_pass()
        patched = self.patched()
        self.assertEqual(len(patched), 1, patched)
        new = int(patched[0].split()[1])
        self.assertTrue(6600 <= new <= 6700, new)                 # elapsed 3000 s + one original deadline
        self.assertIn("still Pending", self.events())
        # the pod finally starts: the whole wait is credited on top of the original deadline, never double counted
        self.set_job("t1-a", start=time.time() - 5000, started=time.time() - 100, deadline=new)
        self.run_pass()
        self.run_pass()
        want = 3600 + 4900
        last = int(self.patched()[-1].split()[1])
        self.assertTrue(want - 60 <= last <= want + 60 and last > new, (last, want, new))

    def test_pending_job_stuck_on_an_image_error_is_not_extended(self):
        self.run_job()
        now = time.time()
        self.set_job("t1-a", state="running", deadline=3600, start=now - 3000, wait="ImagePullBackOff")
        self.run_pass()
        self.assertEqual(self.patched(), [])

    def test_dead_resumable_stage_is_resubmitted_once_with_double_deadline(self):
        stages = [{"id": "a", "job": "t1-a", "manifest": self.manifest("t1-a"), "done_s3": ["s3://braingeneersdev/x/a"], "resumable": True}]
        self.add(stages=stages)
        self.webhook()
        self.run_pass()
        now = time.time()
        self.set_job("t1-a", started=now - 3500)
        self.run_pass()                                           # records pod_started
        self.set_job("t1-a", state="FAILED", reason="DeadlineExceeded", deadline=3600, start=time.time() - 3700)
        self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "retrying")
        self.assertEqual(self.prompts(), [], "Tier 0 only: no model")
        self.assertEqual(self.pushes(), [])
        self.assertEqual(t["attempts"][0]["cls"], "slow")
        self.assertEqual(t["attempts"][0]["by"], "monitor")
        self.assertIn("activeDeadlineSeconds: 7200", Path(t["stages"][0]["manifest"]).read_text())
        self.assertIn("activeDeadlineSeconds: 7200", (self.fake / "applied.log").read_text().splitlines()[-1].replace("  ", " "))
        self.assertEqual(t["stages"][0]["dl"]["resubmits"], 1)
        self.assertIn("deadline-resubmit", (self.state / "digest.log").read_text())
        # the second timeout of the same stage is not resubmitted again: it is a repeat after a fix, so Tier 3
        self.set_job("t1-a", started=time.time() - 7000)
        self.run_pass()
        self.set_job("t1-a", state="FAILED", reason="DeadlineExceeded", deadline=7200, start=time.time() - 7300)
        self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "WITH_COORDINATOR")
        self.assertEqual(len(t["attempts"]), 1)
        self.assertEqual(self.pushes(), [])

    def test_manifest_resume_flag_counts_as_resumable(self):
        m = self.manifest("t1-a", **{'print(1)': 'print(1)", "--skip-existing'})
        self.add(stages=[{"id": "a", "job": "t1-a", "manifest": m, "done_s3": ["s3://braingeneersdev/x/a"]}])
        self.run_pass()
        self.set_job("t1-a", started=time.time() - 3500)
        self.run_pass()
        self.set_job("t1-a", state="FAILED", reason="DeadlineExceeded", deadline=3600, start=time.time() - 3700)
        self.run_pass()
        self.assertEqual(self.task()["status"], "retrying")
        self.assertEqual(self.prompts(), [])

    def test_non_resumable_timeout_enters_the_ladder_at_tier_1(self):
        """Not known to resume by skipping finished items, so nothing is assumed: Haiku, Sonnet, then the coordinator."""
        self.add()
        self.webhook()
        self.run_pass()
        self.set_job("t1-a", started=time.time() - 3500)
        self.run_pass()
        self.set_job("t1-a", state="FAILED", reason="DeadlineExceeded", deadline=3600, start=time.time() - 3700)
        self.sonnet_plan_stop("STOPPED: one node ran a pod 10x slower; rerunning redoes everything")
        self.run_pass()
        t = self.task()
        self.assertEqual(self.agent_models(), ["haiku", "sonnet"])
        self.assertEqual(t["status"], "WITH_COORDINATOR")
        self.assertEqual(self.pushes(), [], "a timeout never pages the owner")
        self.assertEqual(t["attempts"], [])
        self.assertIn("class slow", self.prompts()[1].read_text())
        self.assertTrue(any(e["event_type"] == "escalation" for e in Relay.received))

    def test_queue_class_deadline_is_untouched_by_the_timeout_rules(self):
        self.add()
        self.run_pass()
        self.set_job("t1-a", state="FAILED", reason="DeadlineExceeded")
        self.plan({"cmds": [["nrp-task", "report", "STOPPED", "need more info"]], "result": "STOPPED: need more info"})
        self.run_pass()
        self.assertIn("class queue", self.prompts()[-1].read_text())


if __name__ == "__main__":
    unittest.main()

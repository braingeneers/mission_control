#!/usr/bin/env python3
"""v3 build step 2: the monitor wakes the SAME coordinator chat whatever harness it runs in (T3 webhook, Claude Code session, Codex session),
once per plan step, never per failure that is still going up the ladder. Fake `claude` / `codex` programs record what they were asked; no models,
cluster or network."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_agent_runners as TA  # noqa: E402  (load_module: the script as a module)

SID_C = "11111111-2222-3333-4444-555555555555"
SID_X = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

FAKE = """#!/bin/sh
# records argv (one per line), cwd and stdin of a wake; rc from $FAKE_DIR/rc (default 0)
d="@FAKE@"
printf '%s\\n' "$@" > "$d/$(basename "$0").argv"
pwd > "$d/$(basename "$0").cwd"
cat > "$d/$(basename "$0").stdin"
echo x >> "$d/$(basename "$0").calls"
[ -f "$d/rc" ] && { echo "$(cat "$d/out" 2>/dev/null)" ; echo "resume failed: no conversation" >&2; exit "$(cat "$d/rc")"; }
echo '{"type":"result","is_error":false,"result":"ok"}'
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wdwake_"))
        (self.tmp / "state").mkdir()
        self.w = TA.load_module(self.tmp / "state")
        self.fake = self.tmp / "fake"
        self.fake.mkdir()
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        for n in ("claude", "codex"):
            (self.bin / n).write_text(FAKE.replace("@FAKE@", str(self.fake)))
            (self.bin / n).chmod(0o755)
        self.chat_dir = self.tmp / "chat"
        self.chat_dir.mkdir()
        self.env = patch.dict(os.environ, {"PATH": "%s:%s" % (self.bin, os.environ["PATH"])})
        self.env.start()
        self.addCleanup(self.env.stop)
        for name in ("log", "digest", "push", "push_clear"):
            p = patch.object(self.w, name)
            setattr(self, name, p.start())
            self.addCleanup(p.stop)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def argv(self, prog):
        return (self.fake / (prog + ".argv")).read_text().splitlines()

    def calls(self, prog):
        p = self.fake / (prog + ".calls")
        return len(p.read_text().splitlines()) if p.exists() else 0

    def task(self, name="t1", harness=None, status="running", **kw):
        o = {"title": "the chat", "collaborator": "Sam"}
        if harness:
            o.update(harness=harness, session={"claude": SID_C, "codex": SID_X}.get(harness), cwd=str(self.chat_dir))
        t = {"name": name, "label": name, "created": self.w.now(), "status": status, "namespace": "test", "origin": o, "mode": "auto",
             "stages": [{"id": "a", "job": name + "-a", "state": "running", "after": [], "done_s3": []}], "attempts": [], "failure": None,
             "events": [], "max_retries": 4}
        t.update(kw)
        self.w.task_write(t)
        return t

    def deliver(self):
        self.w.process_task_webhooks(SimpleNamespace(dry_run=False), {})

    def outbox(self, name="t1"):
        return (self.w.task_load(name) or {}).get("webhook_outbox") or []


class OriginHarness(Base):
    def test_origin_accepts_a_claude_or_codex_session_and_refuses_inconsistent_ones(self):
        w = self.w
        o = w.norm_origin({"title": "chat", "harness": "claude", "session": SID_C, "cwd": "/tmp/x"})
        self.assertEqual((o["harness"], o["session"], o["cwd"]), ("claude", SID_C, "/tmp/x"))
        self.assertEqual(w.norm_origin({"harness": "codex", "session": SID_X})["session"], SID_X, "a session alone names the chat")
        self.assertEqual(w.norm_origin({"title": "t", "link": "t3-thread://v2/e/t", "harness": "t3"})["harness"], "t3")
        for bad in ({"title": "x", "harness": "claude"},                                    # no session
                    {"title": "x", "harness": "vim", "session": SID_C},
                    {"title": "x", "harness": "t3", "session": SID_C},                      # T3 chats are woken through their webhook
                    {"title": "x", "session": SID_C},
                    {"title": "x", "harness": "claude", "session": "a b;rm"},
                    {"title": "x", "harness": "codex", "session": SID_X, "cwd": "relative/dir"},
                    {"title": "x", "harness": "codex", "session": SID_X, "cwd": "/a/../b"}):
            with self.assertRaises(w.ChainError, msg=repr(bad)):
                w.norm_origin(bad)

    def test_overlay_reads_the_session_from_the_environment_only_when_the_harness_is_named(self):
        w = self.w
        flags = SimpleNamespace(origin_title="t", origin_link=None, origin_assistant=None, origin_collaborator=None, origin_harness="claude",
                                origin_session=None, origin_cwd=None)
        with patch.dict(os.environ, {"CLAUDE_CODE_SESSION_ID": SID_C, "CODEX_THREAD_ID": SID_X}):
            o = w.origin_overlay(None, flags)
            self.assertEqual((o["harness"], o["session"], o["cwd"]), ("claude", SID_C, os.getcwd()))
            flags.origin_harness = "codex"
            self.assertEqual(w.origin_overlay(None, flags)["session"], SID_X)
            flags.origin_session = "explicit-id-1234"
            self.assertEqual(w.origin_overlay(None, flags)["session"], "explicit-id-1234", "an explicit id beats the environment")
            flags.origin_harness, flags.origin_session = None, None
            self.assertNotIn("session", w.origin_overlay({"title": "t"}, flags) or {}, "no harness named: nothing is guessed from the environment")
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
            flags.origin_harness = "claude"
            with self.assertRaises(w.ChainError):                                         # named, but no id anywhere
                w.norm_origin(w.origin_overlay(None, flags))

    def test_wake_target_follows_the_origin_then_the_webhook(self):
        w = self.w
        self.assertEqual(w.wake_target(self.task(harness="claude")), {"harness": "claude", "session": SID_C, "cwd": str(self.chat_dir)})
        self.assertEqual(w.wake_target(self.task(harness="codex"))["harness"], "codex")
        self.assertIsNone(w.wake_target(self.task()))
        (self.tmp / "state" / "webhooks").mkdir()
        (self.tmp / "state" / "webhooks" / "t1").write_text("{}")
        self.assertEqual(w.wake_target(self.task()), {"harness": "t3"})
        self.assertEqual(w.wake_target(self.task(harness="claude"))["harness"], "claude", "an explicit session beats a webhook file")


class Delivery(Base):
    def test_claude_session_is_resumed_not_started(self):
        t = self.task(harness="claude")
        self.w.task_txn("t1", lambda t: self.w.queue_task_webhook(t, "escalation", summary="NRP task t1 needs its coordinator chat: boom"))
        self.deliver()
        argv = self.argv("claude")
        self.assertEqual(argv[:4], ["-p", "--resume", SID_C, "--permission-mode"])
        self.assertIn("dontAsk", argv)
        self.assertNotIn("--no-session-persistence", argv, "the wake must land in the chat's history")
        self.assertNotIn("--model", argv, "the chat keeps its own model")
        self.assertIn("Bash(nrp-monitor task needs-owner:*)", argv)
        self.assertNotIn("Bash(nrp-monitor:*)", argv, "only the commands the wake names")
        self.assertEqual((self.fake / "claude.cwd").read_text().strip(), str(self.chat_dir.resolve()), "run in the chat's own directory")
        text = (self.fake / "claude.stdin").read_text()
        self.assertIn("boom", text)
        self.assertIn("last resort", text)
        self.assertIn("NRP monitor wake", text)
        self.assertEqual(self.outbox(), [], "delivered: acknowledged")
        self.assertIn("wake delivered: escalation via claude", "\n".join(self.w.task_load("t1")["events"]))

    def test_codex_session_is_resumed_by_id_with_the_prompt_on_stdin(self):
        self.task(harness="codex")
        self.w.task_txn("t1", lambda t: self.w.queue_task_webhook(t, "done"))
        self.deliver()
        self.assertEqual(self.argv("codex"), ["exec", "resume", "--all", "--skip-git-repo-check", SID_X, "-"])
        self.assertNotIn("--ephemeral", self.argv("codex"))
        self.assertIn("finished", (self.fake / "codex.stdin").read_text())
        self.assertEqual(self.calls("claude"), 0)
        self.assertEqual(self.outbox(), [])

    def test_t3_goes_to_the_webhook_and_starts_no_process(self):
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer
        got = []

        class H(BaseHTTPRequestHandler):
            def do_POST(s):
                got.append(json.loads(s.rfile.read(int(s.headers["Content-Length"]))))
                s.send_response(200)
                s.end_headers()

            def log_message(s, *a):
                pass
        srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        p = self.tmp / "state" / "webhooks" / "t1"
        p.parent.mkdir()
        p.write_text(json.dumps({"url": "http://127.0.0.1:%d/h" % srv.server_port, "workstream": "coord"}))
        p.chmod(0o600)
        self.task(harness="t3")
        self.w.task_txn("t1", lambda t: self.w.queue_task_webhook(t, "escalation", summary="s"))
        self.deliver()
        self.assertEqual([e["event_type"] for e in got], ["escalation"])
        self.assertEqual(self.calls("claude") + self.calls("codex"), 0)

    def test_failed_resume_is_counted_and_retried(self):
        self.task(harness="claude")
        (self.fake / "rc").write_text("1")
        self.w.task_txn("t1", lambda t: self.w.queue_task_webhook(t, "done"))
        self.deliver()
        self.assertEqual(len(self.outbox()), 1, "kept for the next pass")
        self.assertEqual(list(self.w.task_load("t1")["wake_tries"].values()), [1])
        (self.fake / "rc").unlink()
        self.deliver()
        self.assertEqual(self.outbox(), [])
        self.assertEqual(self.w.task_load("t1").get("wake_tries"), {})

    def test_escalation_that_cannot_be_delivered_falls_back_to_the_owner_after_the_cap(self):
        self.task(harness="codex")
        (self.fake / "rc").write_text("1")
        self.w.to_coordinator("t1", "stage a failed twice", None)
        t = self.w.task_load("t1")
        self.assertEqual((t["status"], [e["event_type"] for e in t["webhook_outbox"]]), ("WITH_COORDINATOR", ["escalation"]))
        for i in range(self.w.WAKE_MAX_TRIES):
            self.assertEqual(self.w.task_load("t1")["status"], "WITH_COORDINATOR", "pass %d" % i)
            self.deliver()
        t = self.w.task_load("t1")
        self.assertEqual(t["status"], "NEEDS_OWNER")
        self.assertIn("could not be woken", t["reason"])
        self.assertIn("codex resume failed", t["reason"])
        self.assertEqual(self.outbox(), [])
        self.assertEqual(self.calls("codex"), self.w.WAKE_MAX_TRIES)

    def test_a_done_wake_that_never_lands_is_dropped_with_a_digest_line_not_retried_forever(self):
        self.task(harness="claude")
        (self.fake / "rc").write_text("1")
        self.w.task_txn("t1", lambda t: self.w.queue_task_webhook(t, "done"))
        for _ in range(self.w.WAKE_MAX_TRIES + 2):
            self.deliver()
        self.assertEqual(self.outbox(), [])
        self.assertEqual(self.calls("claude"), self.w.WAKE_MAX_TRIES)
        self.assertTrue(any(c.args[0] == "fault" and "not delivered" in c.args[1] for c in self.digest.call_args_list))

    def test_missing_cli_is_a_failed_delivery_not_a_crash(self):
        self.task(harness="claude")
        self.w.task_txn("t1", lambda t: self.w.queue_task_webhook(t, "done"))
        with patch.dict(os.environ, {"PATH": "/nonexistent"}):
            self.deliver()
        self.assertEqual(len(self.outbox()), 1)
        self.assertEqual(list(self.w.task_load("t1")["wake_tries"].values()), [1])

    def test_dry_run_delivers_nothing(self):
        self.task(harness="claude")
        self.w.task_txn("t1", lambda t: self.w.queue_task_webhook(t, "done"))
        self.w.process_task_webhooks(SimpleNamespace(dry_run=True), {})
        self.assertEqual(self.calls("claude"), 0)
        self.assertEqual(len(self.outbox()), 1)


class OneWake(Base):
    def test_a_failure_that_goes_up_the_ladder_wakes_nobody_until_the_ladder_ends(self):
        self.task(harness="claude")
        self.w.task_fail("t1", "a", "code", "sig", "Traceback ...")
        self.assertEqual(self.outbox(), [], "Tier 0/1/2 handle it: no per-failure wake")
        self.w.to_coordinator("t1", "the fix agent did not resubmit: STOPPED", None)
        ev = self.outbox()
        self.assertEqual([e["event_type"] for e in ev], ["escalation"], "one wake for the whole failure, at the end of the ladder")
        self.assertIn("task resume t1", ev[0]["summary"])
        self.assertIn("needs-owner", ev[0]["summary"])
        self.deliver()
        self.assertEqual(self.calls("claude"), 1)
        self.assertEqual(self.outbox(), [])

    def test_no_wake_target_still_escalates_to_the_owner(self):
        self.task()
        self.w.to_coordinator("t1", "boom", None)
        t = self.w.task_load("t1")
        self.assertEqual(t["status"], "NEEDS_OWNER")
        self.assertIn("no coordinator webhook or harness session", t["reason"])

    def test_watch_only_failure_is_final_and_sends_the_one_failure_wake(self):
        self.task(harness="codex", mode="watch")
        self.w.task_fail("t1", "a", "code", "sig", "Traceback in stage a")
        self.w.handle_failure("t1", SimpleNamespace(dry_run=False))
        self.assertEqual([e["event_type"] for e in self.outbox()], ["failure"])
        self.assertEqual(self.w.task_load("t1")["status"], "NEEDS_OWNER")

    def plan_step(self, *names, step="3"):
        pid = "plan-x"
        (self.w.plan_dir(pid)).mkdir(parents=True, exist_ok=True)
        for n in names:
            self.w.ledger_add(pid, step, n, "session", None)
        return {"plan": "PLAN.md#" + pid, "from_step": step}

    def finish(self, name):
        self.w.task_txn(name, lambda t: tstage_done(t))
        with patch.object(self.w, "observe_task"), patch.object(self.w, "report_long_pending"):
            self.w.advance_task(name, {}, SimpleNamespace(dry_run=False))

    def test_one_done_wake_per_plan_step_not_one_per_task(self):
        od = self.plan_step("c1", "c2", "c3")
        for n in ("c1", "c2", "c3"):
            self.task(name=n, harness="claude", on_done={"plan": "plan-x", "from_step": od["from_step"]})
        self.finish("c1")
        self.assertEqual(self.outbox("c1"), [])
        self.assertIn("done wake held", "\n".join(self.w.task_load("c1")["events"]))
        self.finish("c2")
        self.assertEqual(self.outbox("c2"), [])
        self.finish("c3")                                                                   # the last task of the step sends the one wake
        ev = self.outbox("c3")
        self.assertEqual([e["event_type"] for e in ev], ["done"])
        self.assertIn("c1, c2, c3", ev[0]["summary"])
        self.assertEqual(sum(len(self.outbox(n)) for n in ("c1", "c2", "c3")), 1)
        self.w.process_task_webhooks(SimpleNamespace(dry_run=False), {})
        self.assertEqual(self.calls("claude"), 1)
        self.assertIn("plan step 3", (self.fake / "claude.stdin").read_text())

    def test_jobs_with_old_and_new_labels_are_both_discovered_by_name(self):
        items = [{"metadata": {"name": "job-"+name, "labels": {"nrp-"+name+"/kind": "s3check"}},
                  "status": {"active": 1}} for name in ("watchdog", "monitor")]
        with patch.object(self.w, "kubectl", return_value=SimpleNamespace(returncode=0, stdout=json.dumps({"items": items}))) as k:
            jobs = self.w.fetch_jobs("test")
        self.assertEqual(set(jobs), {"job-watchdog", "job-monitor"})
        self.assertNotIn("-l", k.call_args.args)
        labels = self.w.s3_check_job_manifest("new", [])["metadata"]["labels"]
        self.assertIn("nrp-monitor/kind", labels)
        self.assertNotIn("nrp-watchdog/kind", labels)

    def test_last_cancel_sends_one_summary_for_terminal_siblings(self):
        od = self.plan_step("c1", "c2", "c3")
        for n in ("c1", "c2", "c3"):
            self.task(name=n, harness="claude", on_done={"plan": "plan-x", "from_step": "3"})
        self.finish("c1")
        self.w.task_txn("c2", lambda t: t.update(status="failed"))
        self.w.cmd_task_cancel(SimpleNamespace(name="c3"))
        ev = self.outbox("c3")
        self.assertEqual(len(ev), 1)
        for outcome in ("done: c1", "failed: c2", "cancelled: c3"):
            self.assertIn(outcome, ev[0]["summary"])
        self.w.cmd_task_cancel(SimpleNamespace(name="c3"))
        self.assertEqual(len(self.outbox("c3")), 1)

    def test_all_cancelled_internal_paths_also_wake_once(self):
        self.plan_step("c1", "c2")
        for n in ("c1", "c2"):
            self.task(name=n, harness="claude", on_done={"plan": "plan-x", "from_step": "3"})
        for n in ("c1", "c2"):
            self.w.task_txn(n, lambda t: t.update(status="cancelled"))
        ev = self.outbox("c2")
        self.assertEqual(len(ev), 1)
        self.assertIn("done: none; failed: none; cancelled: c1, c2", ev[0]["summary"])

    def test_mark_registered_stage_resumable_logs_event(self):
        self.task()
        self.w.cmd_task_stage(SimpleNamespace(name="t1", stage="a", resumable=True))
        t = self.w.task_load("t1")
        self.assertTrue(t["stages"][0]["resumable"])
        self.assertIn("marked resumable", t["events"][-1])

    def test_a_lone_task_still_wakes_once_when_it_finishes(self):
        self.task(harness="codex")
        self.finish("t1")
        self.assertEqual([e["event_type"] for e in self.outbox()], ["done"])
        self.assertNotIn("summary", self.outbox()[0], "single-task payload is unchanged")

    def test_a_cancelled_sibling_does_not_hold_the_step(self):
        od = self.plan_step("c1", "c2")
        self.task(name="c1", harness="claude", on_done={"plan": "plan-x", "from_step": "3"})
        self.task(name="c2", harness="claude", status="cancelled", on_done={"plan": "plan-x", "from_step": "3"})
        self.finish("c1")
        self.assertEqual([e["event_type"] for e in self.outbox("c1")], ["done"])

    def test_no_per_job_callback_secrets_remain_in_the_code(self):
        src = (Path(__file__).resolve().parents[1] / "nrp-monitor").read_text().lower()
        self.assertNotIn("callback", src)
        self.assertNotIn("create secret", src)
        self.assertNotIn('"secret", "create"', src)


def tstage_done(t):
    for s in t["stages"]:
        s["state"] = "done"


class HandoffText(Base):
    def test_registering_prints_the_wake_target_and_asks_for_the_escalation_text(self):
        w = self.w
        self.assertTrue(w.handoff_escalation_missing("## Registrar\n\nSam is rebuilding the table.\n"))
        self.assertFalse(w.handoff_escalation_missing("## Registrar\n\nFailures go to the monitor's subagents first; this chat is the last resort.\n"))
        self.assertTrue(w.handoff_escalation_missing("## Registrar\n\n<!-- escalation: last resort -->\n"), "comments do not count")
        for word in ("subagents", "last resort", "needs-owner"):
            self.assertIn(word, w.HANDOFF_ESC_ASK)

    def test_template_tells_the_registrar_what_to_write(self):
        text = (Path(__file__).resolve().parents[1] / "templates" / "handoff.md").read_text()
        for word in ("subagents", "last resort", "needs-owner", "once when the plan step"):
            self.assertIn(word, text)


import test_tasks as tt  # noqa: E402


class AddFlags(unittest.TestCase):
    """`task add` / `origin task` through the real CLI (fake kubectl and aws)."""
    setUp, tearDown = tt.T.setUp, tt.T.tearDown
    wd, manifest, add, task = tt.T.wd, tt.T.manifest, tt.T.add, tt.T.task

    def add_with(self, name, *flags, origin=None):
        stages = [{"id": "a", "job": name + "-a", "manifest": self.manifest(name + "-a"), "done_s3": ["s3://braingeneersdev/alice/test/%s/a.txt" % name]}]
        f = self.tmp / (name + ".json")
        spec = {"name": name, "goal": "test task " + name, "approved": "Sam 2026-11-05 in chat: go", "notes": "a fake task", "stages": stages}
        if origin:
            spec["origin"] = origin
        f.write_text(json.dumps(spec))
        return self.wd("task", "add", str(f), *flags)

    def test_codex_and_claude_origin_flags_are_recorded_and_the_wake_target_is_printed(self):
        rc, out, err = self.add_with("t1", "--origin-title", "codex chat", "--origin-harness", "codex", "--origin-session", SID_X, "--origin-cwd", "/tmp")
        self.assertEqual(rc, 0, err)
        o = self.task("t1")["origin"]
        self.assertEqual((o["harness"], o["session"], o["cwd"]), ("codex", SID_X, "/tmp"))
        self.assertIn("Wake: Codex session %s" % SID_X, out)
        self.assertIn("never a new thread", out)
        self.assertIn("HANDOFF:", out, "no handoff yet: told what to write in it")
        self.assertIn("last resort", out)
        rc, out, err = self.add_with("t2", "--origin-title", "claude chat", "--origin-harness", "claude", "--origin-session", SID_C)
        self.assertEqual(rc, 0, err)
        self.assertIn("Wake: Claude Code session %s" % SID_C, out)
        self.assertTrue(self.task("t2")["origin"]["cwd"].startswith("/"), "defaults to the current directory")

    def test_session_id_is_read_from_the_environment_when_only_the_harness_is_named(self):
        self.env["CLAUDE_CODE_SESSION_ID"] = SID_C
        rc, out, err = self.add_with("t1", "--origin-title", "c", "--origin-harness", "claude")
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.task("t1")["origin"]["session"], SID_C)
        del self.env["CLAUDE_CODE_SESSION_ID"]
        rc, out, err = self.add_with("t2", "--origin-title", "c", "--origin-harness", "claude")
        self.assertEqual(rc, 1)
        self.assertIn("origin.harness claude needs origin.session", err)
        self.assertFalse((self.state / "tasks" / "t2").exists())

    def test_json_origin_may_carry_the_harness_and_t3_keeps_working(self):
        rc, out, err = self.add_with("t1", origin={"title": "j", "harness": "codex", "session": SID_X})
        self.assertEqual(rc, 0, err)
        rc, out, err = self.add_with("t2", origin={"title": "t3 chat", "link": "t3-thread://v2/e/t", "harness": "t3"})
        self.assertEqual(rc, 0, err)
        self.assertIn("NO wake target", out, "a T3 origin without a webhook file has nowhere to wake yet")

    def test_origin_command_can_bind_the_session_later(self):
        self.add("t1")
        rc, out, err = self.wd("origin", "task", "t1", "--harness", "codex", "--session", SID_X, "--replace", "--evidence", "codex resume list 2026-11-11")
        self.assertEqual(rc, 0, err)
        o = self.task("t1")["origin"]
        self.assertEqual((o["harness"], o["session"]), ("codex", SID_X))
        self.assertTrue(o["title"], "--replace changes only the fields given")


if __name__ == "__main__":
    unittest.main()

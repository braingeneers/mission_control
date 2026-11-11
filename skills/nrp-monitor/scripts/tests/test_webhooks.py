#!/usr/bin/env python3
"""Notification-only task webhooks: local HTTP and temporary state, no cluster or models."""
import importlib.machinery
import importlib.util
import fcntl
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[1] / "nrp-monitor"


class Handler(BaseHTTPRequestHandler):
    status = 200
    received = []
    agents = []

    def do_POST(self):
        self.agents.append(self.headers.get("User-Agent"))
        self.received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        self.send_response(self.status)
        self.end_headers()

    def log_message(self, *args):
        pass


class Webhooks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        old = os.environ.get("NRP_WATCHDOG_STATE")
        os.environ["NRP_WATCHDOG_STATE"] = self.tmp.name
        loader = importlib.machinery.SourceFileLoader("wd_webhook_test", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.wd = importlib.util.module_from_spec(spec)
        loader.exec_module(self.wd)
        if old is None:
            del os.environ["NRP_WATCHDOG_STATE"]
        else:
            os.environ["NRP_WATCHDOG_STATE"] = old
        Handler.status, Handler.received = 200, []
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.wd.task_write({"name": "example", "stages": [{"id": "a", "job": "job", "state": "running"}]})
        self.path = Path(self.tmp.name) / "webhooks" / "example"
        self.path.parent.mkdir()
        self.path.write_text(json.dumps({"url": "http://127.0.0.1:%d/webhook-token" % self.server.server_port,
                                         "workstream": "lit-map"}))
        self.path.chmod(0o600)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def deliver(self, dry_run=False):
        self.wd.process_task_webhooks(SimpleNamespace(dry_run=dry_run), {})

    def test_failure_does_not_wake_but_a_queued_event_retries_idempotently(self):
        # v3: a failure goes up the ladder first, so task_fail itself sends no wake (the escalation wake is the one that reaches the chat)
        self.wd.task_fail("example", "a", "code", "signature", "secret log")
        self.wd.task_fail("example", "a", "code", "signature", "secret log")
        task = self.wd.task_load("example")
        self.assertFalse(task.get("webhook_outbox"))
        self.assertNotIn("event_id", task["failure"])
        self.wd.task_txn("example", lambda t: self.wd.queue_task_webhook(t, "failure"))
        task = self.wd.task_load("example")
        event = task["webhook_outbox"][0]
        self.assertEqual(len(task["webhook_outbox"]), 1)
        self.assertEqual(set(event), {"task", "event_type", "event_id", "generation"})
        Handler.status = 503
        self.deliver()
        self.assertEqual(self.wd.task_load("example")["webhook_outbox"], [event])
        Handler.status = 200
        self.deliver()
        self.deliver()
        self.assertEqual(Handler.received, [dict(event, workstream="lit-map")] * 2)
        self.assertEqual(self.wd.task_load("example")["webhook_outbox"], [])
        self.assertNotIn("webhook-token", self.wd.LOG.read_text())
        # Cloudflare in front of the relay rejects Python-urllib's default agent (error 1010).
        self.assertTrue(Handler.agents and all(a == "nrp-monitor/1.0" for a in Handler.agents), Handler.agents)

    def test_permissions_symlink_and_dry_run(self):
        self.wd.task_txn("example", lambda t: self.wd.queue_task_webhook(t, "done"))
        self.deliver(dry_run=True)
        self.path.chmod(0o644)
        self.deliver()
        self.assertEqual(Handler.received, [])
        self.path.unlink()
        self.path.symlink_to("/dev/null")
        self.deliver()
        self.assertEqual(Handler.received, [])
        self.assertEqual(len(self.wd.task_load("example")["webhook_outbox"]), 1)

    def test_opt_in_only(self):
        self.path.unlink()
        self.wd.task_fail("example", "a", "code", "signature", "detail")
        self.assertFalse(self.wd.task_load("example").get("webhook_outbox"))

    def test_task_done_queues_generation(self):
        self.wd.task_write({"name": "example", "label": "example", "created": self.wd.now(),
                            "status": "running", "stages": [{"id": "a", "state": "done", "after": []}],
                            "attempts": [], "failure": None, "namespace": "test"})
        with patch.object(self.wd, "observe_task"):
            self.wd.advance_task("example", {}, SimpleNamespace(dry_run=False))
        task = self.wd.task_load("example")
        self.assertEqual(task["status"], "done")
        self.assertEqual(task["done_event_id"], task["webhook_outbox"][0]["generation"])
        self.deliver()
        self.assertEqual(Handler.received[0]["event_type"], "done")

    def test_watch_mode_refuses_running_pass(self):
        with open(self.wd.LOCK, "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.wd.cmd_task_watch(SimpleNamespace(name="example")), 1)
        self.assertEqual(self.wd.cmd_task_watch(SimpleNamespace(name="example")), 0)
        self.assertEqual(self.wd.task_load("example")["mode"], "watch")


if __name__ == "__main__":
    unittest.main()

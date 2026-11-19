#!/usr/bin/env python3
"""The main chat: only it sees global notices at session start; other chats see their own items. Same harness as test_tasks
(scratch state dir, fake kubectl/aws/claude; nothing real is called). Run: python3 -m pytest tests/test_main_chat.py"""
import json
import os
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_tasks  # noqa: E402

LINK_A = "t3-thread://v2/fake-env/chat-aaaa"
LINK_B = "t3-thread://v2/fake-env/chat-bbbb"
POINTER = "global notices are in `nrp-monitor digest`"
SET_HINT = "set a main chat with `nrp-monitor main-chat --here`"


class Base(unittest.TestCase):
    pass


for _k, _v in vars(test_tasks.T).items():          # harness helpers only: not test_tasks' own tests
    if not _k.startswith("test_"):
        setattr(Base, _k, _v)


class MainChat(Base):
    def status(self, chat=None, *extra):
        saved = self.env
        self.env = dict(saved, **({"T3CODE_THREAD_ID": chat} if chat else {}))
        try:
            return self.wd("status", "--quiet", *extra)
        finally:
            self.env = saved

    def main(self, *args, chat=None):
        saved = self.env
        self.env = dict(saved, **({"T3CODE_THREAD_ID": chat} if chat else {}))
        try:
            return self.wd("main-chat", *args)
        finally:
            self.env = saved

    def config(self):
        return json.loads((self.state / "config.json").read_text())

    def bad_node(self):
        (self.state / "bad-nodes.json").write_text(json.dumps({"gpu-node-1": {"last_fault": time.time(), "expires": time.time() + 3600,
                                                                               "reason": "x", "fault": "x"}}))

    def block(self, *runners):
        (self.state / "runners.json").write_text(json.dumps({r: {"until": time.time() + 3600} for r in runners}))

    def second_runner(self):
        (self.bin / "codex").write_text("#!/bin/sh\nexit 0\n")
        os.chmod(self.bin / "codex", 0o755)
        (self.state / "agents.json").write_text(json.dumps({"runners": ["claude", "codex"]}))

    def needs_owner(self, name, link, reason="pick the dataset"):
        self.add(name, origin={"title": "chat for " + name, "link": link})
        p = self.state / "tasks" / name / "task.json"
        t = json.loads(p.read_text())
        t["status"], t["reason"] = "NEEDS_OWNER", reason
        p.write_text(json.dumps(t))

    # ---- command
    def test_set_show_clear(self):
        rc, out, _ = self.main()
        self.assertIn("main chat: none", out)
        rc, out, err = self.main("--link", LINK_A, "--title", "Main thread")
        self.assertEqual(rc, 0, err)
        rec = self.config()["main_chat"]
        self.assertEqual((rec["link"], rec["title"]), (LINK_A, "Main thread"))
        self.assertIn("set_at", rec)
        self.assertEqual(json.loads((self.state / "config.json").read_text())["deputy_enabled"], False, "other config keys kept")
        self.assertIn("Main thread", self.main()[1])
        rc, out, _ = self.main("--clear")
        self.assertEqual(rc, 0)
        self.assertNotIn("main_chat", self.config())
        log = self.wd("log")[1]
        self.assertIn("main chat none -> Main thread", log)
        self.assertIn("-> none", log)

    def test_here_uses_this_chat_and_refuses_when_unknown(self):
        rc, out, err = self.main("--here", chat="chat-aaaa")
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.config()["main_chat"]["session"], "chat-aaaa")
        rc, out, err = self.main("--here")
        self.assertNotEqual(rc, 0)
        self.assertIn("unknown", err)
        self.assertEqual(self.config()["main_chat"]["session"], "chat-aaaa", "refusal changes nothing")

    def test_bad_link_refused(self):
        self.assertNotEqual(self.main("--link", "not a link")[0], 0)
        self.assertNotIn("main_chat", self.config())

    # ---- status --quiet
    def test_main_chat_sees_every_global_line(self):
        self.main("--link", LINK_A)
        self.bad_node()
        self.block("claude")
        self.needs_owner("other", LINK_B)
        rc, out, _ = self.status("chat-aaaa")
        self.assertIn("1 node(s) excluded", out)
        self.assertIn("1 task(s) need the owner: other:", out)
        self.assertIn("agent runner(s) out of usage: claude", out)
        self.assertNotIn(POINTER, out)

    def test_other_chat_sees_only_its_own_owner_wait(self):
        self.main("--link", LINK_A)
        self.bad_node()
        self.second_runner()
        self.block("claude")
        self.needs_owner("mine", LINK_B, "mine needs you")
        self.needs_owner("theirs", LINK_A, "theirs needs you")
        rc, out, _ = self.status("chat-bbbb")
        self.assertIn("1 task(s) need the owner: mine:", out)
        self.assertNotIn("theirs", out)
        self.assertNotIn("node(s) excluded", out)
        self.assertNotIn("out of usage", out)
        self.assertNotIn(POINTER, out, "a known chat under a set main chat is not pointed anywhere")

    def test_unknown_chat_gets_only_the_pointer(self):
        self.main("--link", LINK_A)
        self.bad_node()
        self.needs_owner("t", LINK_A)
        rc, out, _ = self.status(None)
        self.assertEqual(out, "nrp-monitor: " + POINTER)
        self.assertNotIn(SET_HINT, out)

    def test_pointer_suggests_setting_a_main_chat_when_none_is_set(self):
        self.bad_node()
        self.needs_owner("t", LINK_A)
        for chat in (None, "chat-zzzz"):
            rc, out, _ = self.status(chat)
            self.assertIn(POINTER + "; " + SET_HINT, out)
            self.assertNotIn("node(s) excluded", out)
        rc, out, _ = self.status("chat-aaaa")                # its own wait is still its own
        self.assertIn("1 task(s) need the owner: t:", out)
        self.assertIn(SET_HINT, out)

    def test_no_pointer_without_global_lines(self):
        self.assertEqual(self.status(None), (0, "", ""))
        self.assertEqual(self.status("chat-aaaa"), (0, "", ""))

    def test_no_runner_left_shows_in_every_chat_but_one_blocked_runner_does_not(self):
        self.main("--link", LINK_A)
        self.block("claude")                                  # the only runner
        for chat in (None, "chat-bbbb", "chat-aaaa"):
            rc, out, _ = self.status(chat)
            self.assertIn("NO runner left", out, chat)
        self.second_runner()                                  # another runner remains
        self.assertIn("work uses the next runner", self.status("chat-aaaa")[1])
        for chat in (None, "chat-bbbb"):
            self.assertNotIn("out of usage", self.status(chat)[1])

    def test_heartbeat_warning_shows_in_every_chat(self):
        self.main("--link", LINK_A)
        self.add("t1")                                        # a live task and no heartbeat
        for chat in (None, "chat-bbbb", "chat-aaaa"):
            rc, out, _ = self.status(chat)
            self.assertEqual(rc, 3, chat)
            self.assertIn("WARNING: nrp-monitor has never run", out)

    def test_plain_status_still_shows_everything(self):
        self.main("--link", LINK_A)
        self.bad_node()
        self.needs_owner("other", LINK_A)
        saved = self.env
        self.env = dict(saved, T3CODE_THREAD_ID="chat-bbbb")
        try:
            rc, out, _ = self.wd("status")
        finally:
            self.env = saved
        self.assertIn("excluded node gpu-node-1", out)
        self.assertIn("1 task(s) need the owner", out)
        self.assertIn("ok: heartbeat", out)

    # ---- transfer with origin --replace
    def origin_replace(self, name, link, chat=None):
        saved = self.env
        self.env = dict(saved, **({"T3CODE_THREAD_ID": chat} if chat else {}))
        try:
            return self.wd("task", "origin", name, "--replace", "--link", link, "--title", "New chat", "--evidence", "test fixture")
        finally:
            self.env = saved

    def test_origin_replace_moves_the_main_chat_with_the_work(self):
        self.add("t1", origin={"title": "old", "link": LINK_A})
        self.main("--link", LINK_A, "--title", "Old main")
        rc, out, err = self.origin_replace("t1", LINK_B)
        self.assertEqual(rc, 0, err)
        self.assertIn("main chat moved with the work", out)
        self.assertEqual(self.config()["main_chat"]["link"], LINK_B)
        self.assertEqual(self.config()["main_chat"]["title"], "New chat")
        self.bad_node()
        self.assertIn("node(s) excluded", self.status("chat-bbbb")[1])
        self.assertNotIn("excluded", self.status("chat-aaaa")[1], "the old thread stops getting global notices")
        self.assertIn("main chat Old main", self.wd("log")[1])

    def test_origin_replace_leaves_main_chat_alone_when_it_is_another_chat(self):
        self.add("t1", origin={"title": "old", "link": LINK_A})
        self.main("--link", "t3-thread://v2/fake-env/chat-cccc")
        rc, out, err = self.origin_replace("t1", LINK_B)
        self.assertEqual(rc, 0, err)
        self.assertNotIn("main chat", out)
        self.assertEqual(self.config()["main_chat"]["link"], "t3-thread://v2/fake-env/chat-cccc")

    def test_origin_replace_without_a_main_chat_sets_none(self):
        self.add("t1", origin={"title": "old", "link": LINK_A})
        rc, out, err = self.origin_replace("t1", LINK_B)
        self.assertEqual(rc, 0, err)
        self.assertNotIn("main_chat", self.config())

    # ---- digest
    def test_digest_has_a_runner_usage_line(self):
        self.assertNotIn("Agent runners blocked", self.wd("digest")[1])
        self.block("claude")
        out = self.wd("digest")[1]
        self.assertIn("Agent runners blocked: claude out of usage until", out)
        self.assertIn("NO runner left", out)
        self.second_runner()
        out = self.wd("digest")[1]
        self.assertIn("Agent runners blocked: claude out of usage", out)
        self.assertNotIn("NO runner left", out)


if __name__ == "__main__":
    unittest.main()

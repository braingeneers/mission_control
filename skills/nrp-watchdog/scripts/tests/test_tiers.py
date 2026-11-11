#!/usr/bin/env python3
"""v3 build step 5: per-tier backends (tiers in agents.json), the gemini runner, failover only on unavailable/auth/limit, old config compat,
`nrp-watchdog setup` and install.sh. All runners are mocked or fake programs; nothing calls a model."""
import json
import os
import pty
import select
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_agent_runners as TA  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
TIERS = {"triage": [{"runner": "gemini", "model": "gemini-3.8-flash", "thinking": "lowest"}, {"runner": "claude", "model": "haiku"}],
         "task": [{"runner": "claude", "model": "sonnet"}]}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wdtiers_"))
        (self.tmp / "state").mkdir()
        self.w = TA.load_module(self.tmp / "state")
        for name, kw in (("log", {}), ("digest", {}), ("push", {}), ("push_clear", {}), ("runner_ready", {"return_value": True})):
            p = patch.object(self.w, name, **kw)
            setattr(self, name, p.start())
            self.addCleanup(p.stop)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def cfg(self, obj):
        self.w.AGENTS_CFG.write_text(obj if isinstance(obj, str) else json.dumps(obj))


class Config(Base):
    def test_tiers_load_and_order_is_kept(self):
        self.cfg({"tiers": TIERS})
        cfg, problem = self.w.load_agent_cfg()
        self.assertIsNone(problem)
        self.assertEqual([b["runner"] for b in self.w.tier_backends("triage")], ["gemini", "claude"])
        self.assertEqual(self.w.tier_backends("triage")[0], {"runner": "gemini", "model": "gemini-3.8-flash", "thinking": "lowest"})
        self.assertEqual(self.w.tier_backends("task"), [{"runner": "claude", "model": "sonnet"}])
        self.assertEqual(cfg["runners"][:2], ["gemini", "claude"], "the runners the tiers name come first")

    def test_gemini_is_limited_to_the_read_only_tier_and_bad_entries_fall_back_to_defaults(self):
        for bad in ({"tiers": {"task": [{"runner": "gemini", "model": "m"}]}}, {"tiers": {"repair": [{"runner": "gemini"}]}},
                    {"tiers": {"triage": [{"runner": "claude", "thinking": "low"}]}},
                    {"tiers": {"triage": [{"runner": "gemini", "thinking": "extreme"}]}},
                    {"tiers": {"triage": [{"runner": "gemini", "thinking": True}]}},
                    {"tiers": {"triage": [{"runner": "vim"}]}}, {"tiers": {"triage": []}}, {"tiers": {"nope": [{"runner": "claude"}]}},
                    {"tiers": {"triage": [{"runner": "claude", "model": "a b"}]}}, {"tiers": {"triage": [{"runner": "claude", "color": 1}]}},
                    {"tiers": [1]}):
            self.cfg(bad)
            cfg, problem = self.w.load_agent_cfg()
            self.assertTrue(problem, bad)
            self.assertEqual(cfg, self.w.default_agent_cfg())
        self.cfg({"tiers": {"task": [{"runner": "gemini"}]}})
        self.assertIn("limited to the triage tier", self.w.load_agent_cfg()[1])
        for th in ("lowest", "low", "medium", "high", 0, 512):
            self.cfg({"tiers": {"triage": [{"runner": "gemini", "thinking": th}]}})
            self.assertIsNone(self.w.load_agent_cfg()[1], th)

    def test_old_format_still_loads_and_means_the_same_ordered_list(self):
        self.cfg({"runners": ["claude", "codex"], "models": {"triage": {"claude": "opus", "codex": "gpt-x"}, "task": {"claude": "sonnet"}}})
        cfg, problem = self.w.load_agent_cfg()
        self.assertIsNone(problem)
        self.assertEqual(self.w.tier_backends("triage"), [{"runner": "claude", "model": "opus"}, {"runner": "codex", "model": "gpt-x"}])
        self.assertEqual(self.w.tier_backends("task")[0], {"runner": "claude", "model": "sonnet"})
        self.assertEqual(self.w.tier_backends("task")[1], {"runner": "codex"}, "no model configured: the CLI default")
        self.assertEqual(list(self.w.agent_cmd("triage", ["A"]))[3], "opus")
        self.cfg({"runners": ["gemini", "claude"]})                     # old-style list naming gemini: it only serves the read-only tier
        self.assertEqual([b["runner"] for b in self.w.tier_backends("triage")], ["gemini", "claude"])
        self.assertEqual([b["runner"] for b in self.w.tier_backends("task")], ["claude"])

    def test_no_file_is_claude_only_as_before(self):
        self.assertEqual([b["runner"] for b in self.w.tier_backends("triage")], ["claude"])
        self.assertEqual(self.w.agent_cfg()["tiers"], {})

    def test_chosen_backend_model_reaches_the_claude_command(self):
        self.cfg({"tiers": {"task": [{"runner": "claude", "model": "opus"}]}})
        spec = dict(self.w.agent_cmd("task", ["A"]).spec, backend={"runner": "claude", "model": "opus"})
        self.assertEqual(self.w.claude_argv(spec)[3], "opus")
        self.assertEqual(self.w.agent_cmd("task", ["A"])[3], "sonnet", "the plain command keeps the tier default")


class GeminiRunner(Base):
    def run_gemini(self, stdout="", stderr="", rc=0, tier="triage", backend=None, allowed=None, **kw):
        seen = {}

        def fake_run(argv, **k):
            seen["argv"], seen["input"], seen["env"], seen["cwd"] = argv, k.get("input"), k.get("env"), k.get("cwd")
            seen["policy"] = Path(argv[argv.index("--admin-policy") + 1]).read_text()
            seen["settings"] = json.loads(Path(k["env"]["GEMINI_CLI_SYSTEM_SETTINGS_PATH"]).read_text())
            return subprocess.CompletedProcess(argv, rc, stdout, stderr)
        spec = {"tier": tier, "allowed": allowed if allowed is not None else ["Bash(nrp-task show:*)", "Bash(nrp-task logs:*)",
                "Read(//tmp/state/tasks/t1/**)", "Edit(//tmp/state/tasks/t1/**)"], "json": kw.get("json", False), "deny": [],
                "backend": backend or {"runner": "gemini", "model": "gemini-3.8-flash", "thinking": "lowest"}}
        with patch.object(self.w.subprocess, "run", fake_run):
            res = self.w.exec_gemini(spec, "the prompt", self.tmp, 60, {"PATH": "/bin"})
        return res, seen

    def test_argv_is_headless_json_default_approval_with_an_admin_policy_and_the_alias(self):
        res, seen = self.run_gemini(stdout=json.dumps({"response": "BENIGN: pod started", "stats": {}}))
        argv = seen["argv"]
        self.assertEqual(argv[0], "gemini")
        self.assertIn("-p", argv)
        self.assertEqual(argv[argv.index("--approval-mode") + 1], "default", "nothing unlisted is approved; headless ask_user is deny")
        self.assertEqual(argv[argv.index("-o") + 1], "json")
        self.assertIn("--skip-trust", argv)
        self.assertEqual(argv[argv.index("-m") + 1], "nrp-monitor-triage", "the alias carries the thinking setting")
        for bad in ("--yolo", "-y", "--sandbox", "-s"):
            self.assertNotIn(bad, argv)
        self.assertEqual(seen["input"], "the prompt", "the prompt travels on stdin, not in argv")
        self.assertEqual(res[:2], ("ok", "BENIGN: pod started"))
        al = seen["settings"]["modelConfigs"]["customAliases"]["nrp-monitor-triage"]
        self.assertEqual(al["modelConfig"]["model"], "gemini-3.8-flash")
        self.assertEqual(al["modelConfig"]["generateContentConfig"]["thinkingConfig"], {"thinkingLevel": "MINIMAL"})
        self.assertEqual(seen["settings"]["mcp"], {"allowed": []})
        self.assertNotIn("GEMINI_API_KEY", seen["env"])

    def test_policy_denies_everything_then_allows_only_the_allowlist_and_never_edits(self):
        _, seen = self.run_gemini(stdout=json.dumps({"response": "ESCALATE: x"}))
        import tomllib
        rules = tomllib.loads(seen["policy"])["rule"]
        self.assertEqual(rules[0], {"toolName": "*", "decision": "deny", "priority": 1})
        shell = next(r for r in rules if r.get("toolName") == "run_shell_command")
        self.assertEqual((shell["commandPrefix"], shell["decision"]), (["nrp-task show", "nrp-task logs"], "allow"))
        reads = [r for r in rules if r.get("toolName") == "read_file" and r["decision"] == "allow"]
        self.assertEqual(len(reads), 1)
        self.assertIn("/tmp/state/tasks/t1/", reads[0]["argsPattern"])
        self.assertTrue(any(r["decision"] == "deny" and r["priority"] > 100 and r["toolName"] == "read_file" for r in rules), "no ../ escape")
        self.assertFalse(any(r["toolName"] in ("write_file", "replace") and r["decision"] == "allow" for r in rules), "Edit rules are not translated")

    def test_thinking_budget_and_no_thinking(self):
        _, seen = self.run_gemini(stdout="{}", backend={"runner": "gemini", "model": "gemini-2.5-flash", "thinking": 0})
        self.assertEqual(seen["settings"]["modelConfigs"]["customAliases"]["nrp-monitor-triage"]["modelConfig"]["generateContentConfig"]["thinkingConfig"],
                         {"thinkingBudget": 0})
        _, seen = self.run_gemini(stdout="{}", backend={"runner": "gemini", "model": "gemini-3.8-flash"})
        self.assertNotIn("modelConfigs", seen["settings"])
        self.assertEqual(seen["argv"][seen["argv"].index("-m") + 1], "gemini-3.8-flash")

    def test_json_mode_wraps_the_answer_like_the_other_runners(self):
        res, _ = self.run_gemini(stdout=json.dumps({"response": "NO_FIX_NEEDED: finished"}), json=True)
        j = json.loads(res[1])
        self.assertEqual((j["result"], j["is_error"], j["runner"]), ("NO_FIX_NEEDED: finished", False, "gemini"))

    def test_only_the_triage_tier_may_run_on_gemini(self):
        for tier in ("task", "repair", "pod", "repair_auth"):
            res = self.w.exec_gemini({"tier": tier, "allowed": [], "json": False, "deny": []}, "p", self.tmp, 5, {})
            self.assertEqual(res[0], "error", tier)

    def test_limit_and_auth_are_reported_as_such_but_a_bad_answer_is_not(self):
        res, _ = self.run_gemini(stdout=json.dumps({"error": {"message": "429 RESOURCE_EXHAUSTED: quota exceeded"}}), rc=1)
        self.assertEqual(res[0], "limit")
        res, _ = self.run_gemini(stderr="Error: Please set an Auth method in settings or GEMINI_API_KEY", rc=1)
        self.assertEqual(res[0], "auth")
        res, _ = self.run_gemini(stdout=json.dumps({"response": "I think it is fine"}))
        self.assertEqual(res[0], "ok", "a wrong answer is not a failover reason")
        res, _ = self.run_gemini(stderr="Traceback (most recent call last): KeyError", rc=1)
        self.assertEqual(res[0], "ok", "an unrelated crash is returned to the caller as an error, not hidden by a failover")


class Failover(Base):
    def run_dispatch(self, results, tier="triage", cfg=None, on=None):
        self.cfg(cfg or {"tiers": TIERS})
        calls = []

        def fake(name):
            def f(spec, prompt, cwd, timeout, env):
                calls.append((name, spec["backend"].get("model")))
                return results[name] if not isinstance(results[name], list) else results[name].pop(0)
            return f
        with patch.dict(self.w.RUNNER_EXEC, {n: fake(n) for n in ("claude", "codex", "gemini")}):
            res = self.w.dispatch_agent(self.w.agent_cmd(tier, ["A"]).spec, "p", self.tmp / "cwd", on_failover=on)
        return res, calls

    def test_usage_limit_moves_to_the_next_backend_and_is_logged(self):
        seen = []
        res, calls = self.run_dispatch({"gemini": ("limit", "RESOURCE_EXHAUSTED quota exceeded", "", 1), "claude": ("ok", "BENIGN: x", "", 0)}, on=seen.append)
        self.assertEqual((res[0], res[1]), ("claude", "ok"))
        self.assertEqual(calls, [("gemini", "gemini-3.8-flash"), ("claude", "haiku")], "each backend gets its own configured model")
        self.assertEqual(len(seen), 1)
        self.assertIn("gemini/gemini-3.8-flash unavailable (usage limit)", seen[0])
        self.assertIn("using claude/haiku", seen[0])
        self.assertTrue(self.w.runner_blocked("gemini"))

    def test_auth_failure_and_missing_cli_also_fail_over(self):
        seen = []
        res, calls = self.run_dispatch({"gemini": ("auth", "", "not signed in", 1), "claude": ("ok", "x", "", 0)}, on=seen.append)
        self.assertEqual(res[0], "claude")
        self.assertIn("not signed in", seen[0])
        st = self.w.read_json(self.w.RUNNER_STATE, {})
        self.assertEqual(st["gemini"]["kind"], "auth")
        self.assertTrue(3000 < st["gemini"]["until"] - time.time() <= self.w.AUTH_BLOCK_S + 5)
        # now gemini is set aside: the next run skips it and says so
        seen.clear()
        res, calls = self.run_dispatch({"claude": ("ok", "x", "", 0)}, on=seen.append)
        self.assertEqual(calls, [("claude", "haiku")])
        self.assertIn("set aside", seen[0])
        self.w.RUNNER_STATE.write_text("{}")
        with patch.object(self.w, "runner_ready", lambda r: r != "gemini"):
            seen.clear()
            res, calls = self.run_dispatch({"claude": ("ok", "x", "", 0)}, on=seen.append)
        self.assertEqual(calls, [("claude", "haiku")])
        self.assertIn("not installed", seen[0])

    def test_a_bad_answer_a_timeout_or_an_error_never_fails_over(self):
        for first in (("ok", "ESCALATE: nonsense", "", 0), ("timeout", "", "", None), ("ok", "", "Traceback", 1), ("error", "", "boom", 1)):
            self.w.RUNNER_STATE.write_text("{}")
            seen = []
            res, calls = self.run_dispatch({"gemini": first, "claude": ("ok", "must not run", "", 0)}, on=seen.append)
            self.assertEqual(res[0], "gemini", first)
            self.assertEqual([c[0] for c in calls], ["gemini"], first)
            self.assertEqual(seen, [])

    def test_every_backend_unavailable_waits_without_using_a_retry(self):
        seen = []
        res, calls = self.run_dispatch({"gemini": ("limit", "quota exceeded", "", 1), "claude": ("auth", "", "please run /login", 1)}, on=seen.append)
        self.assertEqual(res[1], "unavailable")
        self.assertTrue(self.w.is_unavailable(res[2]))
        self.assertEqual(len(seen), 2)
        self.assertIn("no backend left", seen[1])

    def test_tiers_are_independent(self):
        res, calls = self.run_dispatch({"claude": ("ok", "fixed", "", 0), "gemini": ("limit", "quota exceeded", "", 1)}, tier="task")
        self.assertEqual((res[0], calls), ("claude", [("claude", "sonnet")]), "the fixer never tries gemini")

    def test_failovers_land_in_the_tasks_events_through_run_task_agent(self):
        self.cfg({"tiers": TIERS})
        w = self.w
        w.task_write({"name": "t1", "label": "t1", "stages": [], "events": [], "status": "running", "failure": {}, "origin": {}})
        results = {"gemini": ("limit", "RESOURCE_EXHAUSTED", "", 1),
                   "claude": ("ok", json.dumps({"result": "BENIGN: fine", "is_error": False, "permission_denials": []}), "", 0)}

        def fake(name):
            return lambda spec, prompt, cwd, timeout, env: results[name]
        with patch.dict(w.RUNNER_EXEC, {n: fake(n) for n in ("claude", "codex", "gemini")}):
            line, _ = w.run_task_agent("t1", "triage prompt", SimpleNamespace(dry_run=False), kind="triage")
        self.assertEqual(line, "BENIGN: fine")
        t = w.task_load("t1")
        self.assertTrue(any("backend failover (tier triage): gemini/gemini-3.8-flash unavailable" in e for e in t["events"]), t["events"])
        self.assertEqual(t["agent_runs"][-1]["runner"], "claude")
        self.assertEqual(t["agent_runs"][-1]["verdict"], "BENIGN")


class Setup(Base):
    def args(self, **kw):
        d = dict(non_interactive=True, subscriptions=None, triage=None, fixer=None, dry_run=False)
        d.update(kw)
        return SimpleNamespace(**d)

    def run_setup(self, installed=("claude", "codex", "gemini"), **kw):
        import io
        from contextlib import redirect_stdout
        out = io.StringIO()
        with patch.object(self.w.shutil, "which", lambda r, **k: "/fake/bin/" + r if r in installed else None), redirect_stdout(out):
            rc = self.w.cmd_setup(self.args(**kw))
        return rc, out.getvalue()

    def test_non_interactive_default_is_gemini_flash_lowest_then_sonnet(self):
        rc, out = self.run_setup()
        self.assertEqual(rc, 0)
        cfg = json.loads(self.w.AGENTS_CFG.read_text())
        self.assertEqual(cfg["tiers"]["triage"][0], {"runner": "gemini", "model": "gemini-3.8-flash", "thinking": "lowest"})
        self.assertEqual(cfg["tiers"]["task"][0], {"runner": "claude", "model": "sonnet"})
        self.assertEqual(cfg["tiers"]["task"][1]["runner"], "codex", "the other subscription is the failover")
        self.assertNotIn("gemini", cfg["runners"], "gemini cannot run the legacy repair tiers")
        self.assertIsNone(self.w.load_agent_cfg()[1], "what setup writes loads cleanly")
        self.assertIn("(new file)", out)
        self.assertIn("+++ agents.json (proposed)", out)
        self.assertFalse(list(self.w.AGENTS_CFG.parent.glob("agents.json.tmp")), "written atomically")
        self.assertFalse(self.w.AGENTS_CFG.with_name("agents.json.bak").exists())

    def test_only_claude_installed_uses_claude_for_both_tiers(self):
        self.run_setup(installed=("claude",))
        cfg = json.loads(self.w.AGENTS_CFG.read_text())
        self.assertEqual(cfg["tiers"]["triage"], [{"runner": "claude", "model": "haiku"}])
        self.assertEqual(cfg["tiers"]["task"], [{"runner": "claude", "model": "sonnet"}])

    def test_subscriptions_limit_the_choices_even_when_a_cli_is_installed(self):
        self.run_setup(subscriptions="claude,t3")
        cfg = json.loads(self.w.AGENTS_CFG.read_text())
        self.assertEqual([b["runner"] for b in cfg["tiers"]["triage"]], ["claude"])
        _, out = self.run_setup(subscriptions="gemini,claude", installed=("claude",), dry_run=True)
        self.assertIn("gemini but its CLI is not on PATH", out)

    def test_explicit_flags_win_and_are_validated(self):
        self.run_setup(triage="gemini:gemini-3.8-flash:lowest,claude:haiku", fixer="codex:gpt-6.1-sol")
        cfg = json.loads(self.w.AGENTS_CFG.read_text())
        self.assertEqual(cfg["tiers"]["triage"], TIERS["triage"])
        self.assertEqual(cfg["tiers"]["task"], [{"runner": "codex", "model": "gpt-6.1-sol"}])
        with self.assertRaises(SystemExit) as e:
            self.run_setup(fixer="gemini:gemini-3.8-flash")
        self.assertIn("limited to the triage tier", str(e.exception))
        with self.assertRaises(SystemExit):
            self.run_setup(triage="gemini:m:extreme")
        with self.assertRaises(SystemExit):
            self.run_setup(installed=(), subscriptions="")

    def test_existing_file_gets_a_diff_a_backup_and_keeps_the_other_settings(self):
        old = {"runners": ["claude"], "limits": {"task": {"turns": 7, "timeout": 99}}, "followup_ladder": ["triage"]}
        self.cfg(old)
        rc, out = self.run_setup()
        self.assertIn("--- agents.json (current)", out)
        self.assertIn('-{"runners": ["claude"]', out)
        self.assertIn('+  "tiers": {', out)
        bak = self.w.AGENTS_CFG.with_name("agents.json.bak")
        self.assertEqual(json.loads(bak.read_text()), old)
        new = json.loads(self.w.AGENTS_CFG.read_text())
        self.assertEqual(new["limits"], old["limits"])
        self.assertEqual(new["followup_ladder"], ["triage"])
        self.assertEqual(self.w.load_agent_cfg()[0]["limits"]["task"]["turns"], "7")
        rc, out = self.run_setup()
        self.assertIn("nothing to change", out)

    def test_dry_run_writes_nothing_and_an_unreadable_file_is_never_overwritten(self):
        rc, out = self.run_setup(dry_run=True)
        self.assertEqual(rc, 0)
        self.assertFalse(self.w.AGENTS_CFG.exists())
        self.assertIn("dry run", out)
        self.cfg("{not json")
        with self.assertRaises(SystemExit):
            self.run_setup()
        self.assertEqual(self.w.AGENTS_CFG.read_text(), "{not json")

    def test_interactive_walkthrough_with_defaults_and_a_custom_answer(self):
        import io
        from contextlib import redirect_stdout
        answers = iter(["claude,gemini", "", "claude:opus", "y"])
        out = io.StringIO()
        with patch.object(self.w.shutil, "which", lambda r, **k: "/fake/bin/" + r if r in ("claude", "gemini") else None), \
                patch("builtins.input", lambda prompt="": next(answers)), patch.object(self.w.sys.stdin, "isatty", lambda: True), redirect_stdout(out):
            rc = self.w.cmd_setup(self.args(non_interactive=False))
        self.assertEqual(rc, 0)
        cfg = json.loads(self.w.AGENTS_CFG.read_text())
        self.assertEqual(cfg["tiers"]["triage"][0]["runner"], "gemini")
        self.assertEqual(cfg["tiers"]["task"], [{"runner": "claude", "model": "opus"}])
        self.assertIn("no separate Opus tier", out.getvalue())
        self.assertIn("Tier 1 triage", out.getvalue())

    def test_interactive_refuses_without_a_terminal_and_declining_writes_nothing(self):
        with patch.object(self.w.sys.stdin, "isatty", lambda: False):
            with self.assertRaises(SystemExit) as e:
                self.w.cmd_setup(self.args(non_interactive=False))
        self.assertIn("--non-interactive", str(e.exception))
        import io
        from contextlib import redirect_stdout
        answers = iter(["claude", "", "", "n"])
        with patch.object(self.w.shutil, "which", lambda r, **k: "/fake/bin/claude" if r == "claude" else None), \
                patch("builtins.input", lambda prompt="": next(answers)), patch.object(self.w.sys.stdin, "isatty", lambda: True), \
                redirect_stdout(io.StringIO()):
            rc = self.w.cmd_setup(self.args(non_interactive=False))
        self.assertEqual(rc, 1)
        self.assertFalse(self.w.AGENTS_CFG.exists())

    def test_cli_entry_point_and_agents_command_show_the_tiers(self):
        env = dict(os.environ, NRP_WATCHDOG_STATE=str(self.tmp / "cli-state"), PATH=os.environ["PATH"])
        script = str(HERE / "nrp-watchdog")
        r = subprocess.run([sys.executable, script, "setup", "--non-interactive", "--subscriptions", "claude", "--dry-run"], env=env,
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 0, r.stderr or r.stdout)
        self.assertIn("agents.json (proposed)", r.stdout)
        self.assertIn('"runner": "claude"', r.stdout)
        self.assertFalse((self.tmp / "cli-state" / "agents.json").exists())


class InstallSh(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wdinst_"))
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        for n in ("claude", "gemini"):
            (self.bin / n).write_text("#!/bin/sh\nexit 0\n")
            (self.bin / n).chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), NRP_WATCHDOG_LABEL="test.nrp-watchdog", PATH="%s:%s" % (self.bin, os.environ["PATH"]))
        self.env.pop("NRP_WATCHDOG_STATE", None)
        self.state = self.home / ".local/state/nrp-watchdog"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def no_tty(self):
        return subprocess.run(["sh", str(HERE / "install.sh")], env=self.env, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)

    def tty(self, answers):
        master, slave = pty.openpty()
        p = subprocess.Popen(["sh", str(HERE / "install.sh")], env=self.env, stdin=slave, stdout=slave, stderr=slave, close_fds=True)
        os.close(slave)
        os.write(master, answers.encode())
        out, deadline = b"", time.time() + 60
        while time.time() < deadline:
            r, _, _ = select.select([master], [], [], 0.5)
            if r:
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                out += chunk
            elif p.poll() is not None:
                break
        p.wait(timeout=10)
        os.close(master)
        return p.returncode, out.decode(errors="replace")

    def test_without_a_terminal_it_only_says_how_to_run_setup(self):
        r = self.no_tty()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("nrp-watchdog setup", r.stdout)
        self.assertFalse((self.state / "agents.json").exists())

    def test_with_a_terminal_it_runs_setup_once_and_then_leaves_the_file_alone(self):
        rc, out = self.tty("\n\n\n\n")                                  # accept: subscriptions, Tier 1, Tier 2, write
        self.assertEqual(rc, 0, out)
        cfg = json.loads((self.state / "agents.json").read_text())
        self.assertEqual(cfg["tiers"]["triage"][0]["runner"], "gemini")
        self.assertEqual(cfg["tiers"]["task"][0], {"runner": "claude", "model": "sonnet"})
        self.assertIn("Tier 1 triage", out)
        before = (self.state / "agents.json").read_text()
        rc, out = self.tty("")                                            # second install: file exists, so no questions and no hang
        self.assertEqual(rc, 0, out)
        self.assertNotIn("Tier 1 triage", out)
        self.assertEqual((self.state / "agents.json").read_text(), before)

    def test_skip_variable_never_asks(self):
        self.env["NRP_WATCHDOG_SETUP"] = "skip"
        rc, out = self.tty("")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("Tier 1 triage", out)
        self.assertFalse((self.state / "agents.json").exists())


if __name__ == "__main__":
    unittest.main()

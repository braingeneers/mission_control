#!/usr/bin/env python3
"""Tests for plan-run on_done continuation (feature flag <state>/on_done.enabled, default off).
Same fakes as test_tasks.py (fake kubectl/aws/claude; the fake claude runs real `nrp-task` commands from fake/agent_plan.json).
Run: python3 tests/test_plans.py"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_tasks  # noqa: E402

# reuse the fakes and helpers of test_tasks.T without re-running its tests
Base = type("Base", (test_tasks.T,), {k: None for k in dir(test_tasks.T) if k.startswith("test_")})

PLAN = """# Workstream plan

## Some other track <!-- plan:other -->
Not this one.

## Test plan <!-- plan:tp -->
**Central question:** does the thing work?

```run
plan: tp
approval: Sam 2026-11-06 in chat: "go through step 2, stop for the visual review"   # verbatim
steps: 1, 2, 2b, 3
approved_through: %(through)s
stop_for_hunter: 2b
may_touch: s3://braingeneersdev/alice/test/
```

### Step 1: import
Done when: import_done.json exists with n_units > 0.

### Step 2: QC
Done when: qc_summary.json exists.

### Step 2b: visual review (Sam)

## Later section
not part of the plan
"""


class P(Base):
    def setUp(self):
        super().setUp()
        self.write_plan("2")
        self.work = self.state / "plans" / "tp" / "work"

    def write_plan(self, through):
        (self.tmp / "PLAN.md").write_text(PLAN % {"through": through})

    def flag(self, on=True):
        f = self.state / "on_done.enabled"
        f.touch() if on else f.unlink(missing_ok=True)

    def add_step(self, name, step, out=None, **kw):
        out = out or "s3://braingeneersdev/alice/test/%s/done.json" % name
        stages = [{"id": "a", "job": name + "-a", "manifest": self.manifest(name + "-a"), "done_s3": [out]}]
        return self.add(name=name, stages=stages, on_done={"plan": "PLAN.md#tp", "from_step": step}, **kw)

    def finish(self, name):
        """Run the pass that submits, then mark the Job ok with its output present."""
        self.run_pass()
        self.set_job(name + "-a", state="ok")
        (self.fake / "s3.json").write_text(json.dumps(json.loads((self.fake / "s3.json").read_text()) +
                                                      ["s3://braingeneersdev/alice/test/%s/done.json" % name]))
        return self.run_pass()

    def next_task_cmds(self, name, step, out=None):
        """Fake agent commands: write a manifest + TASK.json under work/, then next-add it."""
        out = out or "s3://braingeneersdev/alice/test/%s/done.json" % name
        man = self.work / ("%s-a.yaml" % name)
        spec = {"name": name, "goal": "step %s of the test plan" % step, "notes": "next step",
                "stages": [{"id": "a", "job": name + "-a", "manifest": str(man), "done_s3": [out]}],
                "on_done": {"plan": "tp", "from_step": step}}
        man_text = Path(self.manifest(name + "-a")).read_text()
        return [["sh", "cat > %s <<'X'\n%sX\n" % (man, man_text)],
                ["sh", "cat > %s/%s.json <<'X'\n%s\nX\n" % (self.work, name, json.dumps(spec))],
                ["nrp-task", "next-add", str(self.work / ("%s.json" % name))]]

    def plan_state(self):
        return json.loads((self.state / "plans" / "tp" / "state.json").read_text())

    # ------------------------------------------------------------------ add-time gates
    def test_plan_section_and_run_block(self):
        rc, out, err = self.wd("plan", "sync", str(self.tmp / "PLAN.md") + "#tp")
        self.assertEqual(rc, 0, err)
        self.assertIn("approved through 2", out)
        text = (self.state / "plans" / "tp" / "plan.md").read_text()
        self.assertIn("Step 2b", text)
        self.assertNotIn("Later section", text)
        self.assertNotIn("Not this one", text)
        h = json.loads((self.state / "plans" / "tp" / "header.json").read_text())
        self.assertEqual(h["steps"], ["1", "2", "2b", "3"])
        self.assertEqual(h["stops"], ["2b"])
        (self.tmp / "PLAN.md").write_text((PLAN % {"through": "2"}).replace("stop_for_hunter:", "stop_for_owner:"))     # the new key name
        rc, _, err = self.wd("plan", "sync", str(self.tmp / "PLAN.md") + "#tp")
        self.assertEqual(rc, 0, err)
        h = json.loads((self.state / "plans" / "tp" / "header.json").read_text())
        self.assertEqual(h["stops"], ["2b"])
        (self.tmp / "PLAN.md").write_text(PLAN % {"through": "2"})
        (self.tmp / "PLAN.md").write_text((PLAN % {"through": "2"}).replace("approval:", "approvl:"))
        rc, _, err = self.wd("plan", "sync", str(self.tmp / "PLAN.md") + "#tp")
        self.assertNotEqual(rc, 0)
        self.assertIn("approval", err)

    def test_header_stored_before_the_owner_rename_still_loads(self):
        """Plans synced by the earlier script store `stop_for_hunter`; the running code reads `stops`."""
        import importlib.util, os; from monitor_imports import machinery
        rc, _, err = self.wd("plan", "sync", str(self.tmp / "PLAN.md") + "#tp")
        self.assertEqual(rc, 0, err)
        hp = self.state / "plans" / "tp" / "header.json"
        h = json.loads(hp.read_text())
        h["stop_for_hunter"] = h.pop("stops")
        hp.write_text(json.dumps(h))
        old = os.environ.get("NRP_MONITOR_STATE")
        os.environ["NRP_MONITOR_STATE"] = str(self.state)
        try:
            loader = machinery.SourceFileLoader("wd_plan_hdr", str(Path(__file__).resolve().parents[1] / "nrp-monitor"))
            spec = importlib.util.spec_from_loader("wd_plan_hdr", loader)
            wd = importlib.util.module_from_spec(spec)
            loader.exec_module(wd)
            self.assertEqual(wd.plan_header("tp")["stops"], ["2b"])
        finally:
            if old is None:
                os.environ.pop("NRP_MONITOR_STATE", None)
            else:
                os.environ["NRP_MONITOR_STATE"] = old

    def test_add_refuses_unapproved_and_stop_steps(self):
        rc, _, err = self.add_step("alice-t1", "3")
        self.assertNotEqual(rc, 0)
        self.assertIn("approved through step 2", err)
        self.write_plan("3")
        rc, _, err = self.add_step("alice-t1", "2b")
        self.assertNotEqual(rc, 0)
        self.assertIn("stop for the owner", err)
        rc, _, err = self.add_step("alice-t1", "1")
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.task("alice-t1")["on_done"]["from_step"], "1")
        self.assertEqual(self.plan_state()["ledger"]["1"][0]["task"], "alice-t1")
        rc, _, err = self.add_step("alice-t1b", "1")                       # v3: a second task for the same step while alice-t1 is live is allowed
        self.assertEqual(rc, 0, err)
        self.assertEqual([e["task"] for e in self.plan_state()["ledger"]["1"]], ["alice-t1", "alice-t1b"])

    # ------------------------------------------------------------------ flag off (default)
    def test_flag_off_records_but_starts_nothing(self):
        self.assertEqual(self.add_step("alice-t1", "1")[0], 0)
        self.finish("alice-t1")
        t = self.task("alice-t1")
        self.assertEqual(t["status"], "done")
        self.assertEqual(t["continuation"]["status"], "OFF")
        self.assertFalse(self.prompts())
        ps = self.plan_state()
        self.assertEqual(ps["status"], "waiting")
        self.assertIn("would check 'done when' for step 1 and start step(s) 2", ps["reason"])
        rc, out, _ = self.wd("digest")
        self.assertIn("## Plans (auto-continue OFF): 1 waiting on the owner", out)

    # ------------------------------------------------------------------ flag on
    def test_continue_registers_next_step_then_waits_at_stop(self):
        self.flag()
        self.assertEqual(self.add_step("alice-t1", "1")[0], 0)
        self.plan({"cmds": self.next_task_cmds("alice-t2", "2") + [["nrp-task", "report", "CONTINUED", "step 1 done when holds; started step 2"]],
                   "result": "CONTINUED"},
                  {"cmds": self.next_task_cmds("t3", "2b") + [["nrp-task", "report", "WAITING", "QC done; galleries ready for review"]],
                   "result": "WAITING"})
        self.finish("alice-t1")
        prompt = self.prompts()[0].read_text()
        self.assertIn("Steps you MAY start now (the monitor computed this; `nrp-task next-add` enforces it): 2", prompt)
        t2 = self.task("alice-t2")
        self.assertEqual(t2["on_done"], {"plan": "tp", "from_step": "2", "depth": 1, "by": "continuation", "parent": "alice-t1"})
        self.assertIn("auto-continued by the monitor after task alice-t1", t2["approved"])
        self.assertEqual(self.task("alice-t1")["continuation"]["status"], "CONTINUED")
        self.assertEqual(self.plan_state()["status"], "running")
        self.finish("alice-t2")                                             # step 2 done -> next is 2b, a stop: refused, WAITING
        outs = (self.fake / "agent_outs.log").read_text().splitlines()[-1]
        self.assertIn("may not be started automatically (planned stop for the owner)", outs)
        with self.assertRaises(FileNotFoundError):
            self.task("t3")
        ps = self.plan_state()
        self.assertEqual(ps["status"], "waiting")
        self.assertIn("galleries ready", ps["reason"])
        res = (self.state / "plans" / "tp" / "results.md").read_text()
        self.assertIn("step 1, task alice-t1: CONTINUED", res)
        self.assertIn("step 2, task alice-t2: WAITING", res)
        self.assertFalse(self.pushes())                                # no push overnight: the digest/morning report carries it

    def test_continuation_runs_once_and_step_starts_once(self):
        self.flag()
        self.assertEqual(self.add_step("alice-t1", "1")[0], 0)
        self.plan({"cmds": [["nrp-task", "report", "NOT-DONE", "import_done.json says n_units 0"]], "result": "NOT-DONE"})
        self.finish("alice-t1")
        self.run_pass()
        self.run_pass()
        self.assertEqual(len(self.prompts()), 1)
        ps = self.plan_state()
        self.assertEqual(ps["status"], "waiting")
        self.assertIn("NOT-DONE", ps["reason"])
        # a rerun of step 1 needs a session; the ledger keeps both entries
        self.assertEqual(self.add_step("alice-t1r", "1")[0], 0)
        self.assertEqual([e["by"] for e in self.plan_state()["ledger"]["1"]], ["session", "session"])

    def test_next_add_refuses_outside_run(self):
        self.flag()
        self.assertEqual(self.add_step("alice-t1", "1")[0], 0)
        self.plan({"cmds": self.next_task_cmds("alice-t2", "2", out="s3://braingeneersdev/someone-else/x/done.json")
                   + [["nrp-task", "report", "WAITING", "next-add refused"]], "result": "WAITING"})
        self.finish("alice-t1")
        outs = (self.fake / "agent_outs.log").read_text().splitlines()[-1]
        rc, out = self.tool("alice-t1", "next-add", str(self.work / "alice-t2.json"))  # after the run closed
        self.assertNotEqual(rc, 0)
        self.assertIn("only for the continue agent", out)

    def test_agent_without_report_is_failed_and_waits(self):
        self.flag()
        self.assertEqual(self.add_step("alice-t1", "1")[0], 0)
        self.plan({"cmds": [], "result": "something vague"})
        self.finish("alice-t1")
        self.assertEqual(self.task("alice-t1")["continuation"]["status"], "FAILED")
        self.assertIn("FAILED", self.plan_state()["reason"])

    def test_dry_run_changes_nothing(self):
        self.flag()
        self.assertEqual(self.add_step("alice-t1", "1")[0], 0)
        self.run_pass()
        self.set_job("alice-t1-a", state="ok")
        (self.fake / "s3.json").write_text(json.dumps(["s3://braingeneersdev/alice/test/alice-t1/done.json"]))
        self.run_pass()                                               # alice-t1 done; its continuation is claimed here...
        self.assertTrue(self.task("alice-t1").get("continuation"))
        # ...so check dry-run on a fresh done task instead
        self.assertEqual(self.add_step("alice-t9", "2")[0], 0)
        p = self.state / "tasks" / "alice-t9" / "task.json"
        t = json.loads(p.read_text())
        t["status"] = "done"
        p.write_text(json.dumps(t))
        rc, out, err = self.wd("run", "--tasks-only", "--dry-run")
        self.assertEqual(rc, 0, err)
        self.assertIn("[dry-run] plan tp: task alice-t9 (step 2) done; auto-continue on", out)
        self.assertNotIn("continuation", json.loads(p.read_text()))


class NightCode(P):
    """The continue agent may write and test code for the next approved step on a monitor/<task> branch (never main)."""
    CODE = {"subdir": "job"}

    def setUp(self):
        super().setUp()
        self.env["NRP_TASK_PYTHON"] = sys.executable                   # the interpreter that has pytest (config.json "pv3_python" in real use)
        self.flag()
        (self.tmp / "PLAN.md").write_text((PLAN % {"through": "2"}).replace(
            "may_touch: s3://braingeneersdev/alice/test/", "may_touch: s3://braingeneersdev/alice/test/, job/"))
        self.wc = self.work / "code-2"                                 # the work clone code-begin makes for step 2

    def add_code_step(self, name="alice-t1", step="1"):
        return self.add_step(name, step, code=dict(self.CODE, repo=str(self.repo)))

    def sh(self, script):
        return ["sh", script]

    def write_code(self, rel="job/new_step.py", body="def double(x):\n    return 2 * x\n"):
        return self.sh("cat > %s/%s <<'X'\n%sX\n" % (self.wc, rel, body))

    def write_test(self):
        return self.write_code("job/test_new_step.py", "from new_step import double\n\n\ndef test_double():\n    assert double(2) == 4\n")

    def register(self, name="alice-t2", step="2"):
        """One shell snippet: ship, read the sha256 from the output, write a manifest naming it, write TASK.json, next-add."""
        man, spec = self.work / (name + "-a.yaml"), self.work / (name + ".json")
        job = {"name": name, "goal": "step %s of the test plan" % step, "stages": [{"id": "a", "job": name + "-a", "manifest": str(man),
               "done_s3": ["s3://braingeneersdev/alice/test/%s/done.json" % name]}], "on_done": {"plan": "tp", "from_step": step}}
        text = Path(self.manifest(name + "-a")).read_text()
        return self.sh("OUT=$(nrp-task code-ship) || { echo \"$OUT\"; exit 1; }; SHA=$(echo \"$OUT\" | sed -n 's/^sha256: //p'); "
                       "cat > %s <<X\n%s# code sha256 $SHA\nX\ncat > %s <<'X'\n%s\nX\nnrp-task next-add %s" % (man, text, spec, json.dumps(job), spec))

    def outs(self):
        return [json.loads(l) for l in (self.fake / "agent_outs.log").read_text().splitlines()]





    def test_plan_gpu_stage_is_covered_by_the_plans_approval_date(self):
        gpu = self.manifest("alice-g1-a", **{"requests: {cpu": "requests: {nvidia.com/gpu: 1, cpu"})
        stages = [{"id": "a", "job": "alice-g1-a", "manifest": gpu, "done_s3": ["s3://braingeneersdev/alice/test/alice-g1/done.json"]}]
        rc, _, err = self.add(name="alice-g1", stages=stages)                    # not a plan step: still needs gpu_ok_until
        self.assertNotEqual(rc, 0)
        self.assertIn("gpu_ok_until", err)
        rc, _, err = self.add(name="alice-g1", stages=stages, on_done={"plan": "PLAN.md#tp", "from_step": "1"})
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.task("alice-g1")["stages"][0]["gpu_plan"], "plan tp approved 2026-11-06")
        self.run_pass()
        self.assertIn("alice-g1-a", self.cl())                                   # submitted without a gpu_ok_until date
        (self.tmp / "PLAN.md").write_text((PLAN % {"through": "2"}).replace("approval: Sam 2026-11-06", "approval: Sam yesterday"))
        rc, _, err = self.add(name="alice-g2", stages=[dict(stages[0], id="b", job="alice-g2-a", manifest=self.manifest("alice-g2-a", **{"requests: {cpu": "requests: {nvidia.com/gpu: 1, cpu"}),
                              done_s3=["s3://braingeneersdev/alice/test/alice-g2/done.json"])], on_done={"plan": "PLAN.md#tp", "from_step": "2"})
        self.assertNotEqual(rc, 0)                                         # an approval line without a date does not cover a GPU stage
        self.assertIn("gpu_ok_until", err)


for _k in dir(P):                       # NightCode reuses P's helpers, not its tests
    if _k.startswith("test_") and _k not in NightCode.__dict__:
        setattr(NightCode, _k, None)


if __name__ == "__main__":
    unittest.main()

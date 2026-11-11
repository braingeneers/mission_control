#!/usr/bin/env python3
"""Regression tests for the EXACT success-marker check (2026-11-06 incident: `aws s3 ls s3://b/DONE` is a PREFIX match, so
`DONE.1` of an Indexed Job satisfied `DONE`, the watchdog deleted running pods and 16 of 50 featurecontrols were lost).
Fake aws (tests/test_chains.py, tests/test_tasks.py) answers `ls` by prefix like the real one and `s3api head-object` exactly.
Run: python3 tests/test_s3_exact.py  (or pytest)"""
import importlib.machinery
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE_T = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE_T))
import test_chains as tc                                   # harness only
import test_tasks as tt

_TMP = tempfile.mkdtemp(prefix="wds3_mod_")
os.environ["NRP_WATCHDOG_STATE"] = _TMP
WD = importlib.machinery.SourceFileLoader("wd_s3_under_test", tt.SCRIPT).load_module()
B = "s3://braingeneersdev/alice/finch/pv3/jobs/pv3-gate-x"


def cp(rc, out="", err=""):
    return SimpleNamespace(returncode=rc, stdout=out, stderr=err)


class Pure(unittest.TestCase):
    def test_uses_head_object_with_bucket_key_endpoint_never_ls(self):
        with patch.object(WD.subprocess, "run", return_value=cp(0, '{"ETag": "\\"x\\""}')) as run:
            self.assertIs(WD.s3_exists(B + "/DONE", {"aws_profile": "p"}), True)
        cmd = run.call_args[0][0]
        self.assertEqual(cmd[:1] + cmd[1:3], ["aws", "--endpoint-url", WD.DEFAULT_S3])
        self.assertIn("s3api", cmd)
        self.assertIn("head-object", cmd)
        self.assertNotIn("ls", cmd)
        self.assertEqual(cmd[cmd.index("--bucket") + 1], "braingeneersdev")
        self.assertEqual(cmd[cmd.index("--key") + 1], "alice/finch/pv3/jobs/pv3-gate-x/DONE")
        self.assertEqual(cmd[cmd.index("--profile") + 1], "p")

    def test_404_is_false_everything_else_unknown(self):
        e404 = "An error occurred (404) when calling the HeadObject operation: Not Found"
        cases = [(cp(254, "", e404), False),
                 (cp(254, "", "An error occurred (403) when calling the HeadObject operation: Forbidden"), None),
                 (cp(254, "", "An error occurred (500) when calling the HeadObject operation: Internal Error"), None),
                 (cp(255, "", "Could not connect to the endpoint URL"), None),
                 (cp(255, "", "The security token included in the request is expired"), None),
                 (cp(0, "<html>proxy login</html>"), None), (cp(0, ""), None), (cp(1, "", ""), None),
                 (cp(254, "", "An error occurred (404) when calling the ListObjects operation"), None)]
        for r, want in cases:
            with patch.object(WD.subprocess, "run", return_value=r), patch.object(WD, "log"):
                self.assertIs(WD.s3_exists(B + "/DONE", {}), want, msg=repr(r))

    def test_timeout_and_exec_errors_are_unknown(self):
        for exc in (subprocess.TimeoutExpired("aws", 120), FileNotFoundError("aws")):
            with patch.object(WD.subprocess, "run", side_effect=exc), patch.object(WD, "log"):
                self.assertIsNone(WD.s3_exists(B + "/DONE", {}))

    def test_not_a_single_object_is_unknown_without_calling_aws(self):
        for bad in ("s3://bucket", "s3://bucket/", "s3://bucket/folder/", "http://x/y", "", None, "s3:///k"):
            with patch.object(WD.subprocess, "run") as run, patch.object(WD, "log"):
                self.assertIsNone(WD.s3_exists(bad, {}), msg=repr(bad))
                run.assert_not_called()

    def test_s3_split(self):
        self.assertEqual(WD.s3_split("s3://b/k/DONE.0"), ("b", "k/DONE.0"))
        for bad in ("s3://b", "s3://b/", "s3://b/k/", "b/k"):
            self.assertIsNone(WD.s3_split(bad))


class ExactChains(tc.Base):
    def setup_chain(self, name, uri):
        self.add(name, [self.step("a", "j-a", done_s3=[uri])])
        self.run_pass()
        self.set_job("j-a", "ok")

    def test_DONE_absent_with_DONE_dot_1_present_does_not_complete_and_keeps_the_job(self):
        self.setup_chain("c", B + "/DONE")
        self.s3(B + "/DONE.1", B + "/DONE.0", B + "/RUNNING")
        self.run_pass()
        ch = self.chain("c")
        self.assertEqual(ch["status"], "stopped")
        self.assertIn("does not exist", json.dumps(ch))
        self.assertIn("j-a", self.jobs_in_cluster(), "the Job (its pods) must NOT be deleted on a prefix hit")
        self.assertNotEqual(self.states("c")["a"], "done")

    def test_DONE_dot_1_is_not_satisfied_by_DONE_dot_10(self):
        self.setup_chain("c", B + "/DONE.1")
        self.s3(B + "/DONE.10", B + "/DONE.11")
        self.run_pass()
        self.assertEqual(self.chain("c")["status"], "stopped")
        self.assertIn("j-a", self.jobs_in_cluster())

    def test_complete_marker_completes_and_deletes_the_job(self):
        self.setup_chain("c", B + "/DONE")
        self.s3(B + "/DONE", B + "/DONE.0", B + "/DONE.1")
        self.run_pass()
        self.assertEqual(self.chain("c")["status"], "finished")
        self.assertNotIn("j-a", self.jobs_in_cluster())

    def test_access_denied_and_network_and_garbage_never_count_as_success(self):
        for flag in ("aws_403", "aws_fail", "aws_garbage"):
            name = "c" + flag.replace("_", "")
            job = "j-" + flag.replace("_", "")
            self.add(name, [self.step("a", job, done_s3=[B + "/DONE"])])
            self.run_pass()
            self.set_job(job, "ok")
            self.s3(B + "/DONE")                                # the object exists, but the check cannot say so
            (self.fake / flag).write_text("")
            self.run_pass(2)
            self.assertEqual(self.chain(name)["status"], "active", flag)
            self.assertIn(job, self.jobs_in_cluster(), flag)
            self.assertNotEqual(self.states(name)["a"], "done", flag)
            (self.fake / flag).unlink()
            self.run_pass()
            self.assertEqual(self.chain(name)["status"], "finished", flag + " recovers once the check works")

    def test_persistent_access_error_stops_after_five_passes_and_keeps_the_job(self):
        self.setup_chain("c", B + "/DONE")
        (self.fake / "aws_403").write_text("")
        self.run_pass(6)
        ch = self.chain("c")
        self.assertEqual(ch["status"], "stopped")
        self.assertIn("cannot check", json.dumps(ch))
        self.assertIn("j-a", self.jobs_in_cluster())

    def test_chain_add_refuses_prefix_style_done_s3(self):
        rc, out, err = self.add("p", [self.step("a", "j-a", done_s3=["s3://b/out/"])])
        self.assertNotEqual(rc, 0)
        self.assertIn("ONE object", out + err)


class ExactTasks(unittest.TestCase):
    setUp, tearDown = tt.T.setUp, tt.T.tearDown
    wd, tool, manifest, add, task, cl, set_job, plan, pushes, prompts, run_pass, age_submit = (
        tt.T.wd, tt.T.tool, tt.T.manifest, tt.T.add, tt.T.task, tt.T.cl, tt.T.set_job, tt.T.plan, tt.T.pushes, tt.T.prompts,
        tt.T.run_pass, tt.T.age_submit)

    def one(self, uri=B + "/DONE", **kw):
        rc, out, err = self.add(stages=[{"id": "a", "job": "t1-a", "manifest": self.manifest("t1-a"), "done_s3": [uri]}], **kw)
        self.assertEqual(rc, 0, out + err)
        self.run_pass()
        self.set_job("t1-a", state="ok")

    def s3(self, *uris):
        (self.fake / "s3.json").write_text(json.dumps(list(uris)))

    def test_DONE_absent_with_DONE_dot_1_present_is_not_success_and_keeps_the_job(self):
        self.one(max_retries=0)
        self.s3(B + "/DONE.1", B + "/DONE.0")
        self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "NEEDS_OWNER")
        self.assertIn("does not exist", t["reason"])
        self.assertIn("t1-a", self.cl(), "no delete on a prefix hit")
        self.assertNotEqual(t["stages"][0]["state"], "done")

    def test_complete_marker_succeeds_and_deletes_the_job(self):
        self.one()
        self.s3(B + "/DONE")
        self.run_pass()
        self.assertEqual(self.task()["status"], "done")
        self.assertNotIn("t1-a", self.cl())

    def test_access_denied_is_retried_never_success(self):
        self.one()
        self.s3(B + "/DONE")
        (self.fake / "aws_403").write_text("")
        self.run_pass()
        self.run_pass()
        t = self.task()
        self.assertNotEqual(t["stages"][0]["state"], "done")
        self.assertGreaterEqual(t["stages"][0].get("s3_errors", 0), 2)
        self.assertIn("t1-a", self.cl())
        (self.fake / "aws_403").unlink()
        self.run_pass()
        self.assertEqual(self.task()["status"], "done")

    def test_vanished_job_with_only_a_sibling_marker_is_not_done(self):
        self.one(max_retries=0)
        c = json.loads((self.fake / "cluster.json").read_text())
        del c["jobs"]["t1-a"]
        (self.fake / "cluster.json").write_text(json.dumps(c))
        self.age_submit()
        self.s3(B + "/DONE.1")
        self.run_pass()
        self.assertNotEqual(self.task()["stages"][0]["state"], "done")

    def test_add_refuses_prefix_style_done_s3_and_warns_only_on_exact_existing(self):
        rc, out, err = self.add(stages=[{"id": "a", "job": "t1-a", "manifest": self.manifest("t1-a"), "done_s3": ["s3://braingeneersdev/alice/x/"]}])
        self.assertNotEqual(rc, 0)
        self.assertIn("single objects", out + err)
        self.s3("s3://braingeneersdev/alice/test/t1/a.txt.old")
        rc, out, err = self.add()
        self.assertEqual(rc, 0, out + err)
        self.assertNotIn("ALREADY exists", out + err, "a sibling key is not the marker")


class IndexedJobCompletion(unittest.TestCase):
    """status.succeeded >= 1 is only the FIRST shard of an Indexed Job; the Job is done when all completions are (Complete=True)."""
    def test_job_complete_rules(self):
        jc = WD.job_complete
        self.assertFalse(jc(1, 50, True, False), "1 of 50 shards done, 49 running")
        self.assertFalse(jc(34, 50, True, False))
        self.assertFalse(jc(49, 50, False, False), "all pods gone but one index missing is not success")
        self.assertTrue(jc(50, 50, False, False))
        self.assertTrue(jc(1, 50, False, True), "the Complete condition is authoritative")
        self.assertTrue(jc(1, None, False, False), "work-queue Job: one success, nothing active")
        self.assertFalse(jc(1, None, True, False))
        self.assertFalse(jc(0, 1, False, False))

    def test_classify_job_indexed(self):
        def job(succ, comp, active, complete=False):
            st = {"succeeded": succ, "active": active}
            if complete:
                st["conditions"] = [{"type": "SuccessCriteriaMet", "status": "True"}, {"type": "Complete", "status": "True"}]
            return {"spec": {"completions": comp, "completionMode": "Indexed"}, "status": st}
        self.assertEqual(WD.classify_job(job(16, 50, 34)), "running")
        self.assertEqual(WD.classify_job(job(1, 2, 1)), "running")
        self.assertEqual(WD.classify_job(job(50, 50, 0, True)), "ok")
        self.assertEqual(WD.classify_job({"spec": {}, "status": {"succeeded": 1}}), "ok", "plain 1-completion Job unchanged")


class IndexedTasks(unittest.TestCase):
    """A partly finished Indexed Job must neither complete a stage nor fail it, and must keep its pods."""
    setUp, tearDown = tt.T.setUp, tt.T.tearDown
    wd, tool, manifest, add, task, cl, set_job, plan, pushes, prompts, run_pass, age_submit = (
        tt.T.wd, tt.T.tool, tt.T.manifest, tt.T.add, tt.T.task, tt.T.cl, tt.T.set_job, tt.T.plan, tt.T.pushes, tt.T.prompts,
        tt.T.run_pass, tt.T.age_submit)

    def test_task_partial_indexed_job_waits_without_deleting(self):
        self.add(stages=[{"id": "a", "job": "t1-a", "manifest": self.manifest("t1-a"), "done_s3": [B + "/DONE"]}], max_retries=0)
        self.run_pass()
        self.set_job("t1-a", state="running", completions=50, succeeded=16)
        (self.fake / "s3.json").write_text(json.dumps([B + "/DONE.0", B + "/DONE.1"]))
        self.run_pass()
        self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "running", t.get("reason"))
        self.assertEqual(t["stages"][0]["state"], "running")
        self.assertIn("t1-a", self.cl())
        self.assertEqual(self.pushes(), [])
        self.set_job("t1-a", state="ok", completions=50, succeeded=50)
        (self.fake / "s3.json").write_text(json.dumps([B + "/DONE.0", B + "/DONE"]))
        self.run_pass()
        self.assertEqual(self.task()["status"], "done")
        self.assertNotIn("t1-a", self.cl())

    def test_task_job_state_helper_matches_indexed_rule(self):
        self.add(stages=[{"id": "a", "job": "t1-a", "manifest": self.manifest("t1-a"), "done_s3": [B + "/DONE"]}], max_retries=0)
        self.run_pass()
        self.set_job("t1-a", state="running", completions=4, succeeded=1)
        env = dict(self.env)
        code = ("import importlib.machinery as m,sys;w=m.SourceFileLoader('w',%r).load_module();print(w.job_state('t1-a','braingeneers'))" % str(self.bin / "nrp-monitor"))
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=dict(env, PATH=self.env["PATH"]))
        self.assertEqual(r.stdout.strip(), "running", r.stderr[-300:])
        self.set_job("t1-a", state="ok", completions=4, succeeded=4)
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=dict(env, PATH=self.env["PATH"]))
        self.assertEqual(r.stdout.strip(), "ok", r.stderr[-300:])


class IndexedChains(tc.Base):
    def test_chain_partial_indexed_job_waits_without_deleting(self):
        self.add("ix", [self.step("a", "j-a", done_s3=[B + "/DONE"])])
        self.run_pass()
        self.set_job("j-a", "running", completions=50, succeeded=16)
        self.s3(B + "/DONE.0", B + "/DONE.1")
        self.run_pass(2)
        self.assertEqual(self.chain("ix")["status"], "active")
        self.assertIn("j-a", self.jobs_in_cluster())
        self.set_job("j-a", "ok", completions=50, succeeded=50)
        self.s3(B + "/DONE", B + "/DONE.0")
        self.run_pass()
        self.assertEqual(self.chain("ix")["status"], "finished")
        self.assertNotIn("j-a", self.jobs_in_cluster())


if __name__ == "__main__":
    unittest.main()

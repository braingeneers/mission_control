#!/usr/bin/env python3
"""Tests for the in-cluster S3 check fallback (2026-11-07: both public S3 endpoints returned 503 to the laptop while pods still reached
the internal endpoint). No cluster, no S3: subprocess/kubectl are mocked. Run: python3 tests/test_s3_incluster.py  (or pytest)"""
import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
os.environ["NRP_WATCHDOG_STATE"] = tempfile.mkdtemp(prefix="wds3_incl_")
WD = importlib.machinery.SourceFileLoader("wd_s3_incl_under_test", str(HERE / "nrp-watchdog")).load_module()
A, B, C, D = ("s3://braingeneersdev/alice/x/%s/DONE" % n for n in "abcd")
E503 = "An error occurred (503) when calling the HeadObject operation (reached max retries: 2): Service Unavailable"
E404 = "An error occurred (404) when calling the HeadObject operation: Not Found"


def cp(rc, out="", err=""):
    return SimpleNamespace(returncode=rc, stdout=out, stderr=err)


class Cluster:
    """Fake aws (per-URI external answers) + fake kubectl (create/get/logs/delete) recording what happened."""
    def __init__(self, external, job_lines=None, finished="1/", wait_s=240):
        self.external, self.job_lines, self.finished = external, job_lines, finished
        self.created, self.calls = [], []

    def run(self, cmd, **kw):
        if cmd[0] == "aws":
            u = "s3://%s/%s" % (cmd[cmd.index("--bucket") + 1], cmd[cmd.index("--key") + 1])
            v = self.external[u]
            return cp(0, '{"ETag": "x"}') if v is True else cp(254, "", E404) if v is False else cp(254, "", E503)
        assert cmd[:5] == ["kubectl", "-n", "braingeneers", "create", "-f"], cmd
        self.created.append(json.loads(kw["input"]))
        return cp(0, "job.batch/x created")

    def kubectl(self, *a, timeout=120):
        self.calls.append(a)
        verb = a[2]
        if verb == "get":
            return cp(0, self.finished)
        if verb == "logs":
            return cp(0, self.job_lines or "")
        return cp(0, "deleted")

    def deleted(self):
        return [c[4] for c in self.calls if c[2] == "delete"]


def patched(cl, **env):
    return (patch.object(WD.subprocess, "run", side_effect=cl.run), patch.object(WD, "kubectl", side_effect=cl.kubectl),
            patch.object(WD.time, "sleep"), patch.object(WD, "log"), patch.dict(os.environ, env))


class Fallback(unittest.TestCase):
    def check(self, cl, uris, **env):
        ps = patched(cl, **env)
        for p in ps:
            p.start()
        try:
            return WD.s3_check_many(uris, {})
        finally:
            for p in reversed(ps):
                p.stop()

    def test_job_manifest_matches_the_spec(self):
        m = WD.s3_check_job_manifest("nrpwd-s3check-1", [A, B])
        sp, pod = m["spec"], m["spec"]["template"]["spec"]
        ct = pod["containers"][0]
        self.assertEqual((m["metadata"]["namespace"], ct["image"]), ("braingeneers", "amazon/aws-cli:2.22.35"))
        self.assertEqual(ct["command"][:2], ["bash", "-c"])
        self.assertEqual(ct["command"][4:], [A, B])
        self.assertEqual((sp["activeDeadlineSeconds"], sp["ttlSecondsAfterFinished"], sp["backoffLimit"]), (300, 3600, 0))
        self.assertEqual(ct["resources"]["requests"], ct["resources"]["limits"])
        self.assertEqual(ct["resources"]["limits"], {"cpu": "1", "memory": "512Mi", "ephemeral-storage": "1Gi"})
        env = {e["name"]: e["value"] for e in ct["env"]}
        self.assertEqual(env["AWS_ENDPOINT_URL"], "http://rook-ceph-rgw-nautiluss3.rook")
        self.assertEqual((env["AWS_SHARED_CREDENTIALS_FILE"], env["AWS_CONFIG_FILE"]), ("/.aws/credentials", "/.aws/.s3cfg"))
        self.assertEqual({(v["mountPath"], v["subPath"]) for v in ct["volumeMounts"]}, {("/.aws/credentials", "credentials"), ("/.aws/.s3cfg", ".s3cfg")})
        self.assertEqual(pod["volumes"][0]["secret"]["secretName"], "prp-s3-credentials")
        self.assertEqual(m["metadata"]["labels"], {"pv3/user": WD.OWNER_LABEL, "nrp-watchdog/kind": "s3check"})
        self.assertEqual(pod["restartPolicy"], "Never")
        self.assertNotIn("gpu", json.dumps(m).lower())

    def test_exists_missing_error_map_to_true_false_none(self):
        cl = Cluster({A: None, B: None, C: None}, "EXISTS %s\nMISSING %s\nERROR %s\n" % (A, B, C))
        r = self.check(cl, [A, B, C])
        self.assertEqual(r, {A: True, B: False, C: None})
        self.assertEqual(len(cl.created), 1)
        self.assertEqual(cl.deleted(), [cl.created[0]["metadata"]["name"]])

    def test_one_job_for_all_failed_uris_and_only_those(self):
        cl = Cluster({A: None, B: True, C: False, D: None}, "EXISTS %s\nEXISTS %s\n" % (A, D))
        r = self.check(cl, [A, B, C, D, A])
        self.assertEqual(r, {A: True, B: True, C: False, D: True})
        self.assertEqual(len(cl.created), 1)
        self.assertEqual(cl.created[0]["spec"]["template"]["spec"]["containers"][0]["command"][4:], [A, D])   # 200 and 404 are never re-checked

    def test_no_failures_means_no_job(self):
        cl = Cluster({A: True, B: False})
        self.assertEqual(self.check(cl, [A, B]), {A: True, B: False})
        self.assertEqual(cl.created, [])

    def test_job_that_times_out_leaves_none_and_is_still_deleted(self):
        cl = Cluster({A: None}, job_lines="", finished="/")
        with patch.object(WD, "S3_JOB_WAIT_S", 0):
            r = self.check(cl, [A])
        self.assertEqual(r, {A: None})
        self.assertEqual(len(cl.deleted()), 1)

    def test_failed_job_without_answer_is_none(self):
        cl = Cluster({A: None}, job_lines="Unable to locate credentials\n", finished="/1")
        self.assertEqual(self.check(cl, [A]), {A: None})
        self.assertEqual(len(cl.deleted()), 1)

    def test_unlisted_or_garbled_job_lines_are_ignored(self):
        cl = Cluster({A: None, B: None}, "EXISTS s3://other/obj\nEXISTSX %s\nEXISTS %s\n" % (A, B))
        self.assertEqual(self.check(cl, [A, B]), {A: None, B: True})

    def test_cannot_create_job_is_none(self):
        cl = Cluster({A: None})
        orig = cl.run
        cl.run = lambda cmd, **kw: cp(1, "", "forbidden") if cmd[0] == "kubectl" else orig(cmd, **kw)
        ps = patched(cl)
        for p in ps:
            p.start()
        try:
            self.assertEqual(WD.s3_check_many([A], {}), {A: None})
        finally:
            for p in reversed(ps):
                p.stop()

    def test_switch_off_never_creates_a_job(self):
        for val in ("off", "OFF", "0", "false"):
            cl = Cluster({A: None}, "EXISTS %s\n" % A)
            self.assertEqual(self.check(cl, [A], NRP_WATCHDOG_S3_INCLUSTER=val), {A: None})
            self.assertEqual(cl.created, [])
        cl = Cluster({A: None}, "EXISTS %s\n" % A)
        self.assertEqual(self.check(cl, [A], NRP_WATCHDOG_S3_INCLUSTER="auto"), {A: True})

    def test_bad_uris_never_reach_the_job(self):
        with patch.object(WD, "log"):
            self.assertEqual(WD.s3_incluster(["s3://bucket", "s3://b/folder/"]), {})


class Prepass(unittest.TestCase):
    def setUp(self):
        self.task = {"name": "t", "status": "running", "namespace": "braingeneers", "stages": [
            {"id": "full", "state": "running", "job": "j-full", "done_s3": [A], "after": []},
            {"id": "busy", "state": "running", "job": "j-busy", "done_s3": [B], "after": []},
            {"id": "next", "state": "pending", "job": "j-next", "done_s3": [C], "after": ["full"], "after_s3": [D]}]}

    def run_prepass(self, cl, **env):
        jobs = {"j-full": {"state": "ok"}, "j-busy": {"state": "running"}}
        ps = list(patched(cl, **env)) + [patch.object(WD, "chain_names", return_value=[]), patch.object(WD, "task_names", return_value=["t"]),
                                          patch.object(WD, "task_load", side_effect=lambda n: self.task), patch.object(WD, "fetch_jobs", return_value=jobs)]
        for p in ps:
            p.start()
        try:
            WD.s3_prepass(SimpleNamespace(dry_run=False))
            return dict(WD.S3_PASS), WD.s3_exists(A, {}), None
        finally:
            for p in reversed(ps):
                p.stop()
            WD.S3_PASS = None

    def test_prepass_checks_only_finished_stage_markers_and_ready_gates_in_one_job(self):
        self.task["stages"][2]["after"] = []                    # the gate is ready (its predecessor is done)
        cl = Cluster({A: None, D: None}, "EXISTS %s\nMISSING %s\n" % (A, D))
        got, a_now, _ = self.run_prepass(cl)
        self.assertEqual(got, {A: True, D: False})               # B belongs to a running Job: never checked; C is not a gate
        self.assertIs(a_now, True)
        self.assertEqual(len(cl.created), 1)

    def test_s3_exists_uses_the_pass_answer_without_calling_aws(self):
        WD.S3_PASS = {A: True}
        try:
            with patch.object(WD.subprocess, "run") as run:
                self.assertIs(WD.s3_exists(A, {}), True)
                run.assert_not_called()
        finally:
            WD.S3_PASS = None

    def test_unanswered_uri_is_not_cached_so_it_stays_none(self):
        cl = Cluster({A: None, D: None}, "ERROR %s\n" % A)
        got, _, _ = self.run_prepass(cl)
        self.assertNotIn(A, got)

    def test_prepass_off_makes_no_job(self):
        cl = Cluster({A: None, D: None}, "EXISTS %s\n" % A)
        got, _, _ = self.run_prepass(cl, NRP_WATCHDOG_S3_INCLUSTER="off")
        self.assertEqual((got, cl.created), ({}, []))


class S3Read(unittest.TestCase):
    def setUp(self):
        self.m = importlib.machinery.SourceFileLoader("nrp_s3_read_t", str(HERE / "nrp-s3-read")).load_module()

    def run_main(self, argv, proc, job):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(self.m.subprocess, "run", return_value=proc), patch.object(self.m, "incluster", return_value=job) as inc, \
                redirect_stdout(out), redirect_stderr(err):
            rc = self.m.main(argv)
        return rc, out.getvalue(), inc

    def test_ls_falls_back_when_endpoint_unreachable(self):
        rc, out, inc = self.run_main(["ls", "s3://b/p/"], cp(255, "", "Could not connect to the endpoint URL"), "2026 1 DONE\n")
        self.assertEqual((rc, out.strip()), (0, "2026 1 DONE"))
        inc.assert_called_once()

    def test_ls_403_does_not_fall_back(self):
        rc, out, inc = self.run_main(["ls", "s3://b/p/"], cp(255, "", "An error occurred (AccessDenied) when calling the ListObjectsV2 operation: Forbidden"), "x")
        self.assertEqual(rc, 255)
        inc.assert_not_called()

    def test_ls_switch_off_does_not_run_a_job(self):
        m = self.m
        with patch.dict(os.environ, {"NRP_WATCHDOG_S3_INCLUSTER": "off"}):
            self.assertIsNone(m.incluster("ls", "s3://b/p/", "503"))

    def test_scripts_are_read_only(self):
        for s in (self.m.LS_SCRIPT, self.m.CAT_SCRIPT):
            for bad in (" rm", " sync", "s3 mv", "put-object", "delete"):
                self.assertNotIn(bad, s)
            self.assertIn("aws s3 ls" if s is self.m.LS_SCRIPT else "aws s3 cp", s)
        self.assertIn('"$1" -', self.m.CAT_SCRIPT)               # cp to stdout, never to a bucket


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""v3 tests: nrp-task reship over every declared code dir, Tier 0 rules (OOM resize, node-fault exclusion, long-Pending reason,
finished-Job cleanup) and several tasks per plan step. Same fakes as test_tasks.py (fake kubectl / aws / claude, scratch state dir);
the Prometheus peak query goes to a local stub server. Run: python3 tests/test_v3_tier0.py"""
import hashlib
import http.server
import io
import json
import shutil
import subprocess
import sys
import tarfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_plans  # noqa: E402
import test_tasks  # noqa: E402

HERE = Path(__file__).resolve().parent
CODESHIP = HERE / "fixtures" / "codeship_pv3.py"

Base = type("Base", (test_tasks.T,), {k: None for k in dir(test_tasks.T) if k.startswith("test_")})
PlanBase = type("PlanBase", (test_plans.P,), {k: None for k in dir(test_plans.P) if k.startswith("test_")})


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True, capture_output=True)


class Thanos(http.server.BaseHTTPRequestHandler):
    value = None          # bytes of the peak, or None for "no series"
    queries = []

    def do_GET(self):
        Thanos.queries.append(self.path)
        res = [] if Thanos.value is None else [{"metric": {}, "value": [0, str(Thanos.value)]}]
        body = json.dumps({"status": "success", "data": {"resultType": "vector", "result": res}}).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


GI = 2 ** 30


class Tier0(Base):
    def setUp(self):
        super().setUp()
        Thanos.value, Thanos.queries = None, []
        self.srv = http.server.HTTPServer(("127.0.0.1", 0), Thanos)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.env["NRP_WATCHDOG_THANOS_URL"] = "http://127.0.0.1:%d/api/v1/query" % self.srv.server_port

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        super().tearDown()

    def applied(self):
        p = self.fake / "applied.log"
        return p.read_text() if p.exists() else ""

    def oom(self, job="t1-a"):
        self.set_job(job, state="FAILED", term={"reason": "OOMKilled", "exitCode": 137})

    # ------------------------------------------------------------------ OOM -> peak x1.3
    def test_oom_resubmits_with_observed_peak_times_1_3_and_no_agent(self):
        self.assertEqual(self.add()[0], 0)
        self.run_pass()
        Thanos.value = 2 * GI
        self.oom()
        self.run_pass()
        self.assertEqual(len(self.prompts()), 0, "a rule fixed it: no model")
        t = self.task()
        self.assertEqual(t["tier0"][0]["rule"], "oom")
        self.assertEqual(t["tier0"][0]["memory"], "3Gi")                 # 2Gi x1.3 = 2.6Gi -> 3Gi
        self.assertEqual(t["attempts"][0]["by"], "tier0")
        self.assertIn("observed peak 2.0Gi", t["attempts"][0]["fix"])
        self.assertIn("memory: 3Gi", self.applied().split("t1-a")[-1])
        self.assertIn("t1-a", self.cl())
        self.assertEqual(t["status"], "retrying")
        self.assertTrue(any("max_over_time" in q and "pod%3D~%22t1-a-.%2A%22" in q for q in Thanos.queries), Thanos.queries)
        self.assertIn("3Gi", Path(t["stages"][0]["manifest"]).read_text())
        self.assertFalse(self.pushes())

    def test_oom_never_goes_below_the_limit_it_hit(self):
        self.assertEqual(self.add()[0], 0)
        self.run_pass()
        Thanos.value = 0.1 * GI                                          # 30 s samples missed the spike
        self.oom()
        self.run_pass()
        self.assertEqual(self.task()["tier0"][0]["memory"], "666Mi")    # the limit (512Mi) x1.3, not the 0.1Gi sample x1.3
        self.assertEqual(len(self.prompts()), 0)

    def test_oom_without_a_peak_number_goes_to_the_agent(self):
        self.assertEqual(self.add()[0], 0)
        self.run_pass()
        Thanos.value = None
        self.oom()
        self.run_pass()
        self.assertEqual(len(self.prompts()), 1, "no metric, no guess: the agent decides")
        self.assertNotIn("tier0", self.task())

    def test_oom_over_the_memory_cap_goes_to_the_agent(self):
        self.assertEqual(self.add()[0], 0)
        self.run_pass()
        Thanos.value = 100 * GI                                          # x1.3 = 130Gi > the 128Gi default cap
        self.oom()
        self.run_pass()
        self.assertEqual(len(self.prompts()), 1)
        self.assertNotIn("tier0", self.task())

    def test_a_second_oom_is_not_resized_by_the_rule_again(self):
        self.assertEqual(self.add()[0], 0)
        self.run_pass()
        Thanos.value = 2 * GI
        self.oom()
        self.run_pass()
        self.assertEqual(len(self.task()["tier0"]), 1)
        Thanos.value = 3 * GI
        self.oom()
        self.run_pass()
        self.assertEqual(len(self.task()["tier0"]), 1)
        self.assertEqual(len(self.prompts()), 1, "the second OOM goes up the ladder")

    def test_watch_mode_and_retry_cap_are_respected(self):
        self.assertEqual(self.add(mode="watch")[0], 0)
        self.run_pass()
        Thanos.value = 2 * GI
        self.oom()
        self.run_pass()
        t = self.task()
        self.assertEqual(t["status"], "NEEDS_OWNER")
        self.assertNotIn("tier0", t)
        self.assertEqual(len(self.prompts()), 0)

    def test_a_refused_resubmit_leaves_the_manifest_untouched(self):
        self.assertEqual(self.add(max_retries=0)[0], 0)
        self.run_pass()
        Thanos.value = 2 * GI
        self.oom()
        before = Path(self.task()["stages"][0]["manifest"]).read_text()
        self.run_pass()
        self.assertEqual(Path(self.task()["stages"][0]["manifest"]).read_text(), before)
        self.assertEqual(self.task()["status"], "NEEDS_OWNER")           # the cap is enforced by do_submit; handle_failure escalates

    def test_request_stays_within_the_shared_tolerance_of_the_limit(self):
        m = Path(self.manifest("t1-a"))
        m.write_text(m.read_text().replace("requests: {cpu: \"500m\", memory: 512Mi}", "requests: {cpu: \"500m\", memory: 400Mi}"))
        stage = {"id": "a", "job": "t1-a", "manifest": str(m), "done_s3": ["s3://braingeneersdev/t/a"]}
        self.assertEqual(self.add(stages=[stage])[0], 0)
        self.run_pass()
        Thanos.value = 10 * GI
        self.oom()
        self.run_pass()
        import yaml
        res = yaml.safe_load(Path(self.task()["stages"][0]["manifest"]).read_text())["spec"]["template"]["spec"]["containers"][0]["resources"]
        self.assertEqual(res["limits"]["memory"], "13Gi")
        self.assertEqual(res["requests"]["memory"], "11Gi")              # ceil(13 / 1.2) = 11: limit within 20% of the request

    # ------------------------------------------------------------------ known node fault -> exclude the node
    def node_fault(self, node="gpu-node-7", message="NVRM: Xid 79: GPU has fallen off the bus"):
        self.set_job("t1-a", state="FAILED", node=node, pod_status={"message": message})

    def test_known_node_fault_excludes_the_node_and_resubmits_without_agent(self):
        self.assertEqual(self.add()[0], 0)
        self.run_pass()
        self.node_fault()
        self.run_pass()
        t = self.task()
        self.assertEqual(len(self.prompts()), 0)
        self.assertEqual(t["tier0"][0], dict(t["tier0"][0], rule="node", node="gpu-node-7", stage="a"))
        self.assertEqual(t["attempts"][0]["by"], "tier0")
        app = self.applied().split("t1-a")[-1]
        self.assertIn("kubernetes.io/hostname", app)
        self.assertIn("NotIn", app)
        self.assertIn("gpu-node-7", app)
        self.assertIn("t1-a", self.cl())

    def test_node_exclusion_merges_into_an_existing_affinity_and_is_idempotent(self):
        import importlib.machinery, importlib.util
        ld = importlib.machinery.SourceFileLoader("wd_t0", test_tasks.SCRIPT)
        mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("wd_t0", ld))
        ld.exec_module(mod)
        doc = {"spec": {"template": {"spec": {"affinity": {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": [
            {"matchExpressions": [{"key": "nvidia.com/gpu.product", "operator": "In", "values": ["A100"]},
                                  {"key": "kubernetes.io/hostname", "operator": "NotIn", "values": ["bad-1"]}]}]}}}}}}}
        mod.exclude_node(doc, "bad-2")
        mod.exclude_node(doc, "bad-2")
        ex = doc["spec"]["template"]["spec"]["affinity"]["nodeAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"]["nodeSelectorTerms"][0]["matchExpressions"]
        self.assertEqual(ex[0]["values"], ["A100"])
        self.assertEqual(ex[1]["values"], ["bad-1", "bad-2"])
        bare = {"spec": {"template": {"spec": {}}}}
        mod.exclude_node(bare, "n")
        self.assertEqual(bare["spec"]["template"]["spec"]["affinity"]["nodeAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"]["nodeSelectorTerms"],
                         [{"matchExpressions": [{"key": "kubernetes.io/hostname", "operator": "NotIn", "values": ["n"]}]}])
        self.assertEqual(mod.mem_bytes("4Gi"), 4 * GI)
        self.assertEqual(mod.mem_bytes("2G"), 2e9)
        self.assertIsNone(mod.mem_bytes("lots"))
        self.assertEqual(mod.mem_text(2.6 * GI), "3Gi")
        self.assertEqual(mod.mem_text(300 * 2 ** 20), "300Mi")

    def test_an_ordinary_failure_is_not_a_node_fault(self):
        self.assertEqual(self.add()[0], 0)
        self.run_pass()
        self.node_fault(message="all fine here")
        self.run_pass()
        # an unclassified failure goes up the ladder (Tier 1 triage, then the Tier 2 fixer), not to the node rule
        self.assertIn(len(self.prompts()), (1, 2))
        self.assertNotIn("tier0", self.task())

    def test_the_same_failure_after_a_node_exclusion_goes_to_the_agent(self):
        self.assertEqual(self.add()[0], 0)
        self.run_pass()
        self.node_fault()
        self.run_pass()
        self.assertEqual(len(self.task()["tier0"]), 1)
        self.node_fault(node="gpu-node-9")                               # same signature again on another node: not a node problem
        self.run_pass()
        self.assertEqual(len(self.task()["tier0"]), 1)
        self.assertEqual(self.task()["status"], "NEEDS_OWNER")           # handle_failure: same way again after a retry

    # ------------------------------------------------------------------ long Pending reports the scheduler's reason
    def pending_manifest(self):
        m = Path(self.manifest("t1-a"))
        m.write_text(m.read_text().replace("      restartPolicy: Never\n", "      restartPolicy: Never\n"
                     "      affinity:\n        nodeAffinity:\n          requiredDuringSchedulingIgnoredDuringExecution:\n"
                     "            nodeSelectorTerms:\n            - matchExpressions:\n"
                     "              - {key: nvidia.com/gpu.product, operator: In, values: [NVIDIA-A100]}\n"))
        return str(m)

    def test_long_pending_reports_the_scheduler_reason_and_our_allow_list_once(self):
        stage = {"id": "a", "job": "t1-a", "manifest": self.pending_manifest(), "done_s3": ["s3://braingeneersdev/t/a"]}
        self.assertEqual(self.add(stages=[stage])[0], 0)
        self.run_pass()
        msg = "0/12 nodes are available: 12 node(s) didn't match Pod's node affinity/selector."
        self.set_job("t1-a", state="pending", node="", pod_status={"phase": "Pending", "conditions": [
            {"type": "PodScheduled", "status": "False", "reason": "Unschedulable", "message": msg}]})
        self.run_pass()
        self.assertEqual([e for e in self.task()["events"] if "Pending" in e], [], "not yet 30 minutes")
        self.age_submit()
        self.run_pass()
        ev = [e for e in self.task()["events"] if "Pending" in e]
        self.assertEqual(len(ev), 1, self.task()["events"])
        self.assertIn("0/12 nodes are available", ev[0])
        self.assertIn("our manifest restricts nodes: nvidia.com/gpu.product In NVIDIA-A100", ev[0])
        self.assertIn("allow-list", ev[0])
        out = self.wd("digest", "--hours", "1")[1]
        self.assertIn("Pending", out)
        self.run_pass()
        self.assertEqual(len([e for e in self.task()["events"] if "Pending" in e]), 1, "same reason: reported once")
        self.set_job("t1-a", pod_status={"phase": "Pending", "conditions": [
            {"type": "PodScheduled", "status": "False", "reason": "Unschedulable", "message": "0/12 nodes are available: 12 Insufficient nvidia.com/gpu."}]})
        self.run_pass()
        ev = [e for e in self.task()["events"] if "Pending" in e]
        self.assertEqual(len(ev), 2, "a changed reason is reported again")
        self.assertNotIn("our manifest restricts", ev[1])
        self.assertEqual(self.task()["status"], "running", "reporting changes nothing")
        self.assertEqual(len(self.prompts()), 0)

    def test_a_started_pod_is_not_reported_as_pending(self):
        self.assertEqual(self.add()[0], 0)
        self.run_pass()
        import time
        self.set_job("t1-a", state="running", started=time.time() - 60)
        self.run_pass()
        self.age_submit()
        self.run_pass()
        self.assertEqual([e for e in self.task()["events"] if "Pending" in e], [])

    # ------------------------------------------------------------------ finished Jobs are deleted only after the markers are verified
    def test_finished_job_is_deleted_only_when_its_success_marker_exists(self):
        self.assertEqual(self.add()[0], 0)
        self.run_pass()
        self.set_job("t1-a", state="ok")
        self.run_pass()                                                  # Job succeeded but the marker is missing
        self.assertIn("t1-a", self.cl(), "unverified: the Job and its pods are kept for diagnosis")
        self.assertFalse((self.fake / "deleted.log").exists())
        self.assertEqual(self.task()["failure"]["cls"], "outputs")

    def test_finished_job_with_verified_marker_is_deleted_and_logs_kept(self):
        self.assertEqual(self.add()[0], 0)
        self.run_pass()
        self.set_job("t1-a", state="ok")
        (self.fake / "s3.json").write_text(json.dumps(["s3://braingeneersdev/alice/test/t1/a.txt"]))
        self.run_pass()
        self.assertEqual((self.fake / "deleted.log").read_text().split(), ["t1-a"])
        self.assertTrue((self.state / "tasks/t1/logs/t1-a-a1.txt").exists())


class Reship(Base):
    """`nrp-task reship` packs every code dir the task declares, with the layout `--ship-code` produced at submission."""
    SPEC_URI = "s3://braingeneersdev/alice/test/pv3/jobs/t1-a/spec.json"
    OLD_URI = "s3://braingeneersdev/alice/test/pv3/code/0000000000000000.tgz"

    def key(self, uri):
        return hashlib.md5(uri.encode()).hexdigest()

    def make_repo(self, root, pkgs, with_codeship=False):
        """A git repo at `root` with package dirs `pkgs` ({name: {file: text}}); predictor_v3 gets the real codeship module."""
        for name, files in pkgs.items():
            (root / name).mkdir(parents=True, exist_ok=True)
            (root / name / "__init__.py").write_text("")
            for f, text in files.items():
                (root / name / f).parent.mkdir(parents=True, exist_ok=True)
                (root / name / f).write_text(text)
        if with_codeship:
            j = root / "predictor_v3" / "utils" / "jobs"
            j.mkdir(parents=True)
            for d in (root / "predictor_v3" / "utils", j):
                (d / "__init__.py").write_text("")
            shutil.copy(CODESHIP, j / "codeship.py")
        git(root, "init", "-q")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "init")

    def register(self, code, repo_dir=None):
        m = Path(self.manifest("t1-a"))
        m.write_text(m.read_text().replace('["python", "-c", "print(1)"]', '["python", "-m", "e", "gate", "--spec", "%s"]' % self.SPEC_URI))
        self.env["NRP_TASK_PYTHON"] = sys.executable
        stage = {"id": "a", "job": "t1-a", "manifest": str(m), "done_s3": ["s3://braingeneersdev/t/a"]}
        rc, out, err = self.add(stages=[stage], code=code)
        self.assertEqual(rc, 0, err)
        store = self.fake / "store"
        store.mkdir(exist_ok=True)
        (store / self.key(self.SPEC_URI)).write_text(json.dumps({"module": "m", "code": {"uri": self.OLD_URI, "sha256": "0" * 64}}))
        self.run_pass()
        self.set_job("t1-a", state="FAILED")
        return Path(self.task()["code"]["clone"])

    def tarball(self):
        store = self.fake / "store"
        spec = json.loads((store / self.key(self.SPEC_URI)).read_text())
        data = (store / self.key(spec["code"]["uri"])).read_bytes()
        return spec, tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")

    def test_reship_packs_the_package_and_extra_dirs_from_the_clone(self):
        self.make_repo(self.repo, {"predictor_v3": {"job.py": "print(1/0)\n"}, "finetune": {"tables.py": "A = 1\n"}, "bwb": {"clock.py": "B = 1\n"}},
                       with_codeship=True)
        clone = self.register({"repo": str(self.repo), "subdir": "predictor_v3", "extra_pkg_dirs": ["finetune", "bwb"]})
        self.assertTrue((clone / "finetune" / "tables.py").exists() and (clone / "bwb" / "clock.py").exists())
        (clone / "finetune" / "tables.py").write_text("A = 2\n")            # the agent's fix is in an EXTRA dir only
        (clone / "predictor_v3" / "job.py").write_text("print(1)\n")
        self.tool("t1", "commit", "fix tables and job")
        rc, out = self.tool("t1", "reship", "t1-a")
        self.assertEqual(rc, 0, out)
        self.assertIn("reshipped", out)
        self.assertIn("predictor_v3, finetune, bwb", out)
        spec, tf = self.tarball()
        names = tf.getnames()
        self.assertIn("predictor_v3/job.py", names)
        self.assertIn("finetune/tables.py", names)                         # layout: extras sit beside predictor_v3/
        self.assertIn("finetune/__init__.py", names)
        self.assertIn("bwb/clock.py", names)
        self.assertEqual(tf.extractfile("finetune/tables.py").read(), b"A = 2\n")
        info = json.loads(tf.extractfile("predictor_v3/CODE_INFO.json").read())
        self.assertEqual(sorted(info["extra_packages"]), ["bwb", "finetune"])
        self.assertEqual(spec["module"], "m")
        self.assertEqual(spec["code"]["uri"], "s3://braingeneersdev/alice/test/pv3/code/%s.tgz" % spec["code"]["sha256"][:16])
        self.assertTrue(any("dirs predictor_v3, finetune, bwb" in e for e in self.task()["events"]))

    def test_reship_no_op_check_covers_every_dir(self):
        self.make_repo(self.repo, {"predictor_v3": {"job.py": "print(1)\n"}, "finetune": {"tables.py": "A = 1\n"}}, with_codeship=True)
        clone = self.register({"repo": str(self.repo), "subdir": "predictor_v3", "extra_pkg_dirs": ["finetune"]})
        self.assertEqual(self.tool("t1", "reship", "t1-a")[0], 0)           # first reship: the spec still carries a dummy hash
        rc, out = self.tool("t1", "reship", "t1-a")
        self.assertIn("identical", out)                                      # same code in all dirs: nothing to do
        n = len(list((self.fake / "store").iterdir()))
        (clone / "finetune" / "tables.py").write_text("A = 99\n")            # a change in the EXTRA dir only must not be a no-op
        self.tool("t1", "commit", "extra dir fix")
        rc, out = self.tool("t1", "reship", "t1-a")
        self.assertEqual(rc, 0, out)
        self.assertIn("reshipped", out)
        self.assertEqual(len(list((self.fake / "store").iterdir())), n + 1)  # one more tarball uploaded
        self.assertIn("identical", self.tool("t1", "reship", "t1-a")[1])

    def test_reship_with_the_package_in_another_checkout_like_ft_tables_w6(self):
        """finetune/ + bwb/ in the task's repo (subdir finetune, so the clone is sparse), predictor_v3 and the packer in another repo."""
        snap, pv3 = self.tmp / "snap", self.tmp / "braindance"
        snap.mkdir()
        pv3.mkdir()
        self.make_repo(snap, {"finetune": {"tables.py": "A = 1\n"}, "bwb": {"clock.py": "B = 1\n"}})
        self.make_repo(pv3, {"predictor_v3": {"job.py": "print(1)\n"}}, with_codeship=True)
        clone = self.register({"repo": str(snap), "subdir": "finetune", "pkg_dir": str(pv3 / "predictor_v3"), "extra_pkg_dirs": ["finetune", "bwb"]})
        self.assertTrue((clone / "bwb" / "clock.py").exists(), "relative extras join the sparse checkout")
        self.assertFalse((clone / "predictor_v3").exists())
        (clone / "finetune" / "tables.py").write_text("A = 2\n")
        self.tool("t1", "commit", "fix a slow table")
        rc, out = self.tool("t1", "reship", "t1-a")
        self.assertEqual(rc, 0, out)
        spec, tf = self.tarball()
        self.assertEqual({n.split("/")[0] for n in tf.getnames()}, {"predictor_v3", "finetune", "bwb"})
        self.assertEqual(tf.extractfile("finetune/tables.py").read(), b"A = 2\n")
        self.assertEqual(tf.extractfile("predictor_v3/job.py").read(), b"print(1)\n")

    def test_reship_with_an_absolute_extra_dir_from_another_repo(self):
        other = self.tmp / "other"
        other.mkdir()
        self.make_repo(other, {"extpkg": {"lib.py": "L = 1\n"}})
        self.make_repo(self.repo, {"predictor_v3": {"job.py": "print(1)\n"}}, with_codeship=True)
        self.register({"repo": str(self.repo), "subdir": "predictor_v3", "extra_pkg_dirs": [str(other / "extpkg")]})
        rc, out = self.tool("t1", "reship", "t1-a")
        self.assertEqual(rc, 0, out)
        spec, tf = self.tarball()
        self.assertIn("extpkg/lib.py", tf.getnames())
        self.assertIn("predictor_v3/job.py", tf.getnames())

    def test_reship_refuses_a_declared_dir_that_is_missing_and_a_task_without_the_package(self):
        self.make_repo(self.repo, {"predictor_v3": {"job.py": "print(1)\n"}}, with_codeship=True)
        clone = self.register({"repo": str(self.repo), "subdir": "predictor_v3", "extra_pkg_dirs": ["gone"]})
        self.assertFalse((clone / "gone").exists())
        rc, out = self.tool("t1", "reship", "t1-a")
        self.assertNotEqual(rc, 0)
        self.assertIn("extra_pkg_dirs", out)
        self.assertIn("gone", out)

    def test_task_add_validates_code_dirs(self):
        self.make_repo(self.repo, {"predictor_v3": {"job.py": "x\n"}}, with_codeship=True)
        rc, out, err = self.add(code={"repo": str(self.repo), "subdir": "predictor_v3", "extra_pkg_dirs": ["../elsewhere"]})
        self.assertNotEqual(rc, 0)
        self.assertIn("no ..", err)
        rc, out, err = self.add(code={"repo": str(self.repo), "extra_pkg_dirs": ["not-an-identifier"]})
        self.assertNotEqual(rc, 0)
        self.assertIn("Python package name", err)
        rc, out, err = self.add(code={"repo": str(self.repo), "extra_pkg_dirs": ["/no/such/dir/pkg"]})
        self.assertNotEqual(rc, 0)
        self.assertIn("is not a folder", err)

    def test_task_code_declares_dirs_for_a_task_registered_without_them(self):
        snap, pv3 = self.tmp / "snap", self.tmp / "braindance"
        snap.mkdir()
        pv3.mkdir()
        self.make_repo(snap, {"finetune": {"tables.py": "A = 1\n"}, "bwb": {"clock.py": "B = 1\n"}})
        self.make_repo(pv3, {"predictor_v3": {"job.py": "print(1)\n"}}, with_codeship=True)
        clone = self.register({"repo": str(snap), "subdir": "finetune"})     # as ft-tables-w6 was registered
        rc, out = self.tool("t1", "reship", "t1-a")
        self.assertNotEqual(rc, 0)
        self.assertIn("predictor_v3", out)
        rc, out, err = self.wd("task", "code", "t1", "--pkg-dir", str(pv3 / "predictor_v3"), "--extra-pkg-dir", "finetune", "--extra-pkg-dir", "bwb")
        self.assertEqual(rc, 0, err)
        self.assertTrue((clone / "bwb" / "clock.py").exists())
        self.assertEqual(self.task()["code"]["extra_pkg_dirs"], ["finetune", "bwb"])
        self.assertIn("code dirs reship packs", self.wd("task", "show", "t1")[1])
        rc, out = self.tool("t1", "reship", "t1-a")
        self.assertEqual(rc, 0, out)
        self.assertEqual({n.split("/")[0] for n in self.tarball()[1].getnames()}, {"predictor_v3", "finetune", "bwb"})
        rc, out, err = self.wd("task", "code", "t1", "--extra-pkg-dir", "nope")
        self.assertNotEqual(rc, 0)
        self.assertIn("not in the task's code clone", err)


class StepTasks(PlanBase):
    """A plan step may have several tasks; it counts as done when all of them are, and is continued once."""

    def test_two_tasks_for_one_step_continue_once_when_both_are_done(self):
        self.flag()
        self.assertEqual(self.add_step("t1a", "1")[0], 0)
        self.assertEqual(self.add_step("t1b", "1")[0], 0)                  # the second task for the same live step is accepted
        self.assertEqual([e["task"] for e in self.plan_state()["ledger"]["1"]], ["t1a", "t1b"])
        self.plan({"cmds": self.next_task_cmds("t2", "2") + [["nrp-task", "report", "CONTINUED", "both cells done; started step 2"]], "result": "CONTINUED"})
        self.finish("t1a")                                                  # t1a done, t1b still running
        self.assertEqual(self.task("t1a")["status"], "done")
        self.assertEqual(len(self.prompts()), 0, "step 1 is not done until t1b is")
        self.assertNotIn("continuation", self.task("t1a"))
        self.assertTrue(any("waiting for task(s) t1b" in e for e in self.task("t1a")["events"]))
        self.finish("t1b")
        self.assertEqual(len(self.prompts()), 1, "one continue agent for the step")
        self.assertEqual(self.task("t1a")["continuation"]["status"], "CONTINUED")
        self.assertEqual(self.task("t1b")["continuation"]["status"], "COVERED")
        self.assertIn("continued by task t1a", self.task("t1b")["continuation"]["line"])
        self.assertEqual(self.task("t2")["on_done"]["from_step"], "2")
        self.run_pass()
        self.assertEqual(len(self.prompts()), 1)

    def test_a_sibling_that_needs_the_owner_holds_the_step(self):
        self.flag()
        self.assertEqual(self.add_step("t1a", "1")[0], 0)
        self.assertEqual(self.add_step("t1b", "1", mode="watch")[0], 0)
        self.run_pass()
        self.set_job("t1b-a", state="FAILED", term={"reason": "Error", "exitCode": 1})
        self.finish("t1a")
        self.run_pass()
        self.assertEqual(self.task("t1b")["status"], "NEEDS_OWNER")
        self.assertEqual(len(self.prompts()), 0)
        self.assertNotIn("continuation", self.task("t1a"))

    def test_a_cancelled_sibling_does_not_hold_the_step(self):
        self.flag()
        self.assertEqual(self.add_step("t1a", "1")[0], 0)
        self.assertEqual(self.add_step("t1b", "1")[0], 0)
        self.assertEqual(self.wd("task", "cancel", "t1b")[0], 0)
        self.plan({"cmds": [["nrp-task", "report", "WAITING", "nothing to start"]], "result": "WAITING"})
        self.finish("t1a")
        self.assertEqual(len(self.prompts()), 1)
        self.assertEqual(self.task("t1a")["continuation"]["status"], "WAITING")

    def test_one_continue_agent_may_register_several_tasks_for_the_next_step(self):
        self.flag()
        self.assertEqual(self.add_step("t1", "1")[0], 0)
        self.plan({"cmds": self.next_task_cmds("t2a", "2") + self.next_task_cmds("t2b", "2")
                   + [["nrp-task", "report", "CONTINUED", "started both cells of step 2"]], "result": "CONTINUED"})
        self.finish("t1")
        self.assertEqual(self.task("t2a")["on_done"]["from_step"], "2")
        self.assertEqual(self.task("t2b")["on_done"]["from_step"], "2")
        self.assertEqual([e["task"] for e in self.plan_state()["ledger"]["2"]], ["t2a", "t2b"])
        self.assertEqual(self.task("t1")["continuation"]["registered"], ["t2a", "t2b"])

    def test_a_step_started_by_someone_else_is_still_held_for_a_continuation(self):
        self.flag()
        self.assertEqual(self.add_step("t1", "1")[0], 0)
        self.assertEqual(self.add_step("t2s", "2")[0], 0)                  # a session already started step 2
        self.plan({"cmds": self.next_task_cmds("t2x", "2") + [["nrp-task", "report", "WAITING", "step 2 already started"]], "result": "WAITING"})
        self.finish("t1")
        outs = (self.fake / "agent_outs.log").read_text().splitlines()[-1]
        self.assertIn("already started once", outs)
        with self.assertRaises(FileNotFoundError):
            self.task("t2x")


if __name__ == "__main__":
    unittest.main()

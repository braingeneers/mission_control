#!/usr/bin/env python3
"""The 3 h GPU check (gpu_long_actions): NRP judges GPU pods on a ~3 h average, so a Job alternating GPU and CPU phases must be caught on
the long window even when 10-min samples look fine (NRP warning 2026-11-15, 36.5 % over 3 h). Pure-function tests on real
nrp-util-check lines. Run: python3 tests/test_gpu_long.py"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_agent_runners as TA  # noqa: E402

REAL = ("LOW t71-pilot-sort-test4-recordphase-hp6-a68d3ef585-dsdpz age 279m, 180m mean: cpu 2.37/8.00 (30%), mem 15.7/64.0Gi (25%, max 55.7), "
        "gpu 39% (gpu 1, NVIDIA A10) [NRP violation] rule=gpu")
POD = "t71-pilot-sort-test4-recordphase-hp6-a68d3ef585-dsdpz"


class GpuLong(unittest.TestCase):
    def setUp(self):
        self.m = TA.load_module(Path(tempfile.mkdtemp()))
        self.mine = {POD: "t71-pilot-sort-test4-recordphase-hp6-a68d3ef585", "x-1": "x"}

    def act(self, line):
        return [(p, a, pct) for p, a, pct, _, _ in self.m.gpu_long_actions([line], self.mine)]

    def test_real_warning_case_is_enforced(self):
        self.assertEqual(self.act(REAL), [(POD, "enforce", 39.0)])

    def test_young_pod_under_floor_only_warns(self):
        self.assertEqual(self.act(REAL.replace("age 279m", "age 60m")), [(POD, "warn", 39.0)])

    def test_very_young_pod_ignored(self):
        self.assertEqual(self.act(REAL.replace("age 279m", "age 30m")), [])

    def test_between_floor_and_warn_warns(self):
        self.assertEqual(self.act(REAL.replace("gpu 39%", "gpu 45%")), [(POD, "warn", 45.0)])

    def test_cpu_memory_only_line_ignored(self):
        line = "LOW x-1 age 300m, 180m mean: cpu 1.00/8.00 (12%) [NRP violation] rule=nrp"
        self.assertEqual(self.act(line), [])

    def test_lowest_gpu_of_multi_gpu_pod_decides(self):
        line = "LOW x-1 age 300m, 180m mean: gpu 35% (gpu 0, NVIDIA A100), gpu 80% (gpu 1, NVIDIA A100) [NRP violation] rule=gpu"
        self.assertEqual(self.act(line), [("x-1", "enforce", 35.0)])

    def test_no_dcgm_warns_never_enforces(self):
        line = "LOW x-1 age 300m, 180m mean: gpu 5% nvidia-smi max of 3 (no DCGM series; A10): re-check before deleting [NRP violation] rule=gpu"
        self.assertEqual([a for _, a, _ in self.act(line)], ["warn"])

    def test_other_owners_pods_ignored(self):
        self.assertEqual(self.act(REAL.replace(POD, "someone-else-pod")), [])

    def test_policy_floor(self):
        self.assertAlmostEqual(self.m.gpu_floor(), 0.40)


if __name__ == "__main__":
    unittest.main()

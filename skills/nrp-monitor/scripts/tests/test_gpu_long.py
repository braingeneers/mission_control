#!/usr/bin/env python3
"""The long-window GPU check (gpu_long_actions: warn on the 1 h mean, delete on the 2.5 h mean): NRP judges GPU pods on a ~3 h average, so a Job alternating GPU and CPU phases must be caught on
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


def at(line, window, age, pct=None):
    line = line.replace("180m mean", "%dm mean" % window).replace("age 279m", "age %dm" % age)
    return line.replace("gpu 39%", "gpu %d%%" % pct) if pct is not None else line


class GpuLong(unittest.TestCase):
    """Hunter 2026-11-15: warn on the 1 h average under the 40 % floor; delete when the 2.5 h average is under it."""
    def setUp(self):
        self.m = TA.load_module(Path(tempfile.mkdtemp()))
        self.mine = {POD: "t71-pilot-sort-test4-recordphase-hp6-a68d3ef585", "x-1": "x"}

    def act(self, warn=(), enforce=()):
        return [(p, a, pct) for p, a, pct, _, _ in self.m.gpu_long_actions(list(warn), list(enforce), self.mine)]

    def test_windows_match_owner_decision(self):
        self.assertEqual((self.m.GPU_WARN_WINDOW_MIN, self.m.GPU_ENFORCE_WINDOW_MIN), (60, 150))

    def test_real_warning_case_is_enforced_on_the_2p5h_mean(self):
        self.assertEqual(self.act(warn=[at(REAL, 60, 279, 36)], enforce=[at(REAL, 150, 279)]), [(POD, "enforce", 39.0)])

    def test_1h_mean_under_floor_warns(self):
        self.assertEqual(self.act(warn=[at(REAL, 60, 100, 30)]), [(POD, "warn", 30.0)])

    def test_under_1h_old_ignored(self):
        self.assertEqual(self.act(warn=[at(REAL, 50, 50, 10)]), [])

    def test_enforce_needs_2p5h_of_age(self):
        self.assertEqual(self.act(warn=[at(REAL, 60, 140, 30)], enforce=[at(REAL, 140, 140, 30)]), [(POD, "warn", 30.0)])

    def test_at_or_above_floor_no_action(self):
        self.assertEqual(self.act(warn=[at(REAL, 60, 200, 40)], enforce=[at(REAL, 150, 200, 45)]), [])

    def test_cpu_memory_only_line_ignored(self):
        line = "LOW x-1 age 300m, 60m mean: cpu 1.00/8.00 (12%) [NRP violation] rule=nrp"
        self.assertEqual(self.act(warn=[line], enforce=[line.replace("60m", "150m")]), [])

    def test_lowest_gpu_of_multi_gpu_pod_decides(self):
        line = "LOW x-1 age 300m, 150m mean: gpu 35% (gpu 0, NVIDIA A100), gpu 80% (gpu 1, NVIDIA A100) [NRP violation] rule=gpu"
        self.assertEqual(self.act(enforce=[line]), [("x-1", "enforce", 35.0)])

    def test_no_dcgm_warns_never_enforces(self):
        line = "LOW x-1 age 300m, %dm mean: gpu 5%% nvidia-smi max of 3 (no DCGM series; A10): re-check before deleting [NRP violation] rule=gpu"
        self.assertEqual(self.act(warn=[line % 60], enforce=[line % 150]), [("x-1", "warn", None)])

    def test_other_owners_pods_ignored(self):
        self.assertEqual(self.act(enforce=[at(REAL, 150, 279).replace(POD, "someone-else-pod")]), [])

    def test_policy_floor(self):
        self.assertAlmostEqual(self.m.gpu_floor(), 0.40)


if __name__ == "__main__":
    unittest.main()

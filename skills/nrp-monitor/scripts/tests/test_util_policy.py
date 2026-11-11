"""nrp-util-check takes its numbers from the nrp-cluster skill's shared utilization-policy.json (only numbers the skill states)
plus an optional local override that can only be stricter; no cluster, no network."""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SOURCE = HERE / 'nrp-util-check'
EXAMPLE = HERE / 'templates' / 'utilization-policy.local.json.example'
# the shared file wherever this test runs: the skill layout (scripts/tests), this repo's proposal, or an installed skill
SHARED_CANDIDATES = [
    HERE.parents[1] / 'nrp-cluster' / 'references' / 'utilization-policy.json',
    HERE.parents[1] / 'docs/agents/nrp-monitor-review/proposal/nrp-cluster/utilization-policy.json',
    Path.home() / '.claude/skills/nrp-cluster/references/utilization-policy.json',
]
SHARED = {"gpu_floor": 0.40, "limit_to_request_tolerance": 0.20, "max_concurrent_jobs": 400, "smoke_max_jobs": 3}
OWNER_LOCAL = {"max_concurrent_jobs": 40, "lab_floor": 0.4, "cpu_band": [0.2, 2.0], "memory_band": [0.2, 1.5],
               "small_pod_exempt": {"cpu": 1, "memory_bytes": 2000000000}, "account_block_after_violating_pods": 4}


class Policy(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='wdpolicy_'))

    def write(self, name, obj):
        p = self.tmp / name
        p.write_text(obj if isinstance(obj, str) else json.dumps(obj))
        return p

    def env(self, shared=SHARED, local=None):
        e = {"NRP_MONITOR_STATE": str(self.tmp / 'state'),
             "NRP_UTIL_POLICY": str(self.write('shared.json', shared)),
             "NRP_UTIL_POLICY_LOCAL": str(self.tmp / 'local.json')}
        if local is not None:
            self.write('local.json', local)
        return e

    def load(self, **kw):
        e = self.env(**kw)
        old = {k: os.environ.get(k) for k in e}
        os.environ.update(e)
        try:
            loader = importlib.machinery.SourceFileLoader('util_%d' % time.time_ns(), str(SOURCE))
            spec = importlib.util.spec_from_loader(loader.name, loader)
            m = importlib.util.module_from_spec(spec)
            loader.exec_module(m)
            return m
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def run_cli(self, *args, **kw):
        env = dict(os.environ, **self.env(**kw))
        return subprocess.run([sys.executable, str(SOURCE), *args], capture_output=True, text=True, env=env)

    cpu_idle = {"req": {"cpu": 4, "memory": 8e9}, "cpu": 0.5, "mem": 4e9, "gpus": []}      # CPU at 12.5 % of the request
    gpu_idle = {"req": {"nvidia_com_gpu": 1}, "gpus": [("0", "A100", 30.0)]}

    # ---- shared numbers only
    def test_shared_only_policy_raises_no_cpu_or_memory_flags(self):
        m = self.load()
        self.assertEqual(m.POLICY, SHARED)
        self.assertEqual(m.POLICY_WARNINGS, [])
        self.assertEqual(m.nrp_bad(self.cpu_idle), [], 'no CPU band without a local override')
        self.assertEqual(m.nrp_bad({"req": {"cpu": 4, "memory": 8e9}, "cpu": 20, "mem": 40e9, "gpus": []}), [])
        self.assertEqual(m.nrp_bad(self.gpu_idle), ['gpu'], 'the GPU floor is the skill\'s own rule')
        self.assertEqual(m.nrp_bad({"req": {"nvidia_com_gpu": 1}, "gpus": [("0", "A100", 50.0)]}), [])
        self.assertIsNone(m.ACCT_MAX)

    def test_shared_only_cli_run_has_no_cpu_lines_and_no_account_check(self):
        m = self.load()
        a = type('A', (), {"frac": m.POLICY.get("lab_floor"), "n": "ns"})
        self.assertIsNone(a.frac)
        self.assertEqual(m.pod_lines(a, "p1", 3600, dict(self.cpu_idle), 10), "")
        self.assertTrue(m.pod_lines(a, "p2", 3600, dict(self.gpu_idle, cpu=1, mem=1e9), 10).startswith("LOW p2"))

    # ---- local override
    def test_local_override_enables_bands_floor_exemption_and_account_check(self):
        m = self.load(local=OWNER_LOCAL)
        self.assertEqual(m.POLICY_WARNINGS, [])
        self.assertEqual(m.nrp_bad(self.cpu_idle), ['cpu'])
        self.assertEqual(m.nrp_bad({"req": {"cpu": 0.5, "memory": 1e9}, "cpu": 0.01, "mem": 1e8, "gpus": []}), [], 'small pod exempt')
        self.assertEqual(m.nrp_bad({"req": {"cpu": 4, "memory": 8e9}, "cpu": 2, "mem": 13e9, "gpus": []}), ['mem'])
        self.assertEqual(m.ACCT_MAX, 4)
        a = type('A', (), {"frac": m.POLICY["lab_floor"], "n": "ns"})
        line = m.pod_lines(a, "p1", 3600, dict(self.cpu_idle), 10)
        self.assertIn('cpu 0.50/4.00', line)
        self.assertTrue(line.endswith('[NRP violation] rule=nrp'), line)
        small = {"req": {"cpu": 0.5, "memory": 1e9}, "cpu": 0.1, "mem": 1e9, "gpus": []}
        self.assertTrue(m.pod_lines(a, "p2", 3600, small, 10).endswith('[lab 40% rule; NRP-exempt size] rule=lab'))

    def test_flag_line_names_the_rule_that_fired(self):
        # rule=lab: only the lab floor (a pod of NRP-exempt size); rule=nrp: a CPU/memory band; rule=gpu: any GPU flag
        m = self.load(local=OWNER_LOCAL)
        a = type('A', (), {"frac": m.POLICY["lab_floor"], "n": "ns"})
        lab = m.pod_lines(a, "p", 3600, {"req": {"cpu": 1, "memory": 1.9e9}, "cpu": 0.1, "mem": 1.5e9, "gpus": []}, 10)
        self.assertTrue(lab.endswith('rule=lab'), lab)
        # 2 GiB is above the policy's 2e9-byte exemption, so the same idle pod is an NRP-band violation
        big = m.pod_lines(a, "p", 3600, {"req": {"cpu": 1, "memory": 2 * 2 ** 30}, "cpu": 0.1, "mem": 1.9 * 2 ** 30, "gpus": []}, 10)
        self.assertTrue(big.endswith('[NRP violation] rule=nrp'), big)
        gpu = m.pod_lines(a, "p", 3600, {"req": {"cpu": 4, "memory": 8e9, "nvidia_com_gpu": 1}, "cpu": 4, "mem": 8e9,
                                         "gpus": [("0", "A100", 5.0)]}, 10)
        self.assertTrue(gpu.endswith('rule=gpu'), gpu)
        both = m.pod_lines(a, "p", 3600, {"req": {"cpu": 4, "memory": 8e9, "nvidia_com_gpu": 1}, "cpu": 0.1, "mem": 8e9,
                                          "gpus": [("0", "A100", 5.0)]}, 10)
        self.assertTrue(both.endswith('rule=gpu'), 'a GPU flag always wins: ' + both)
        # the lab floor alone can be stricter than NRP's GPU floor: still a GPU flag
        m2 = self.load(local={"lab_floor": 0.6})
        a2 = type('A', (), {"frac": 0.6, "n": "ns"})
        g2 = m2.pod_lines(a2, "p", 3600, {"req": {"cpu": 4, "memory": 8e9, "nvidia_com_gpu": 1}, "cpu": 4, "mem": 8e9,
                                          "gpus": [("0", "A100", 50.0)]}, 10)
        self.assertTrue(g2.endswith('[lab 60% rule] rule=gpu'), g2)

    def test_each_local_check_is_optional(self):
        m = self.load(local={"cpu_band": [0.2, 2.0]})
        self.assertEqual(m.nrp_bad(self.cpu_idle), ['cpu'])
        self.assertEqual(m.nrp_bad({"req": {"cpu": 4, "memory": 8e9}, "cpu": 2, "mem": 100, "gpus": []}), [], 'no memory band')
        self.assertIsNone(m.ACCT_MAX)

    def test_local_override_cannot_loosen_shared_numbers(self):
        m = self.load(local={"gpu_floor": 0.2, "max_concurrent_jobs": 1000, "limit_to_request_tolerance": 0.5, "lab_floor": 0.4})
        self.assertEqual({k: m.POLICY[k] for k in SHARED}, SHARED)
        self.assertEqual(m.POLICY["lab_floor"], 0.4)
        self.assertEqual(len(m.POLICY_WARNINGS), 3)
        for w, k in zip(m.POLICY_WARNINGS, ("gpu_floor", "max_concurrent_jobs", "limit_to_request_tolerance")):
            self.assertIn(k, w)
            self.assertIn('would loosen the shared', w)
            self.assertNotIn('\n', w)
        self.assertEqual(m.nrp_bad({"req": {"nvidia_com_gpu": 1}, "gpus": [("0", "A100", 30.0)]}), ['gpu'])

    def test_local_override_can_tighten_shared_numbers(self):
        m = self.load(local={"gpu_floor": 0.6, "max_concurrent_jobs": 40})
        self.assertEqual((m.POLICY["gpu_floor"], m.POLICY["max_concurrent_jobs"]), (0.6, 40))
        self.assertEqual(m.POLICY_SOURCES["gpu_floor"], 'local override')
        self.assertEqual(m.POLICY_SOURCES["limit_to_request_tolerance"], 'shared file')
        self.assertEqual(m.nrp_bad({"req": {"nvidia_com_gpu": 1}, "gpus": [("0", "A100", 50.0)]}), ['gpu'])

    def test_bad_local_values_and_files_are_ignored_with_a_warning(self):
        m = self.load(local={"cpu_band": [2.0, 0.2], "lab_floor": 0, "bogus": 1, "account_block_after_violating_pods": "four"})
        self.assertEqual(m.POLICY, SHARED)
        self.assertEqual(len(m.POLICY_WARNINGS), 4)
        m = self.load(local='{not json')
        self.assertEqual(m.POLICY, SHARED)
        self.assertIn('ignored', m.POLICY_WARNINGS[0])

    def test_warnings_are_printed_to_stderr_by_the_command(self):
        r = self.run_cli('--policy', local={"gpu_floor": 0.1})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(r.stderr.strip().splitlines()), 1)
        self.assertIn('would loosen', r.stderr)

    # ---- --policy
    def test_policy_command_says_which_keys_come_from_where(self):
        r = self.run_cli('--policy', local=OWNER_LOCAL)
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = {l.split()[0]: l for l in r.stdout.splitlines() if l.startswith('  ') and 'from' in l}
        self.assertIn('from shared file', rows['gpu_floor'])
        self.assertIn('from shared file', rows['limit_to_request_tolerance'])
        self.assertIn('no check uses it', rows['limit_to_request_tolerance'])
        self.assertIn('from local override', rows['max_concurrent_jobs'])
        for k in ('lab_floor', 'cpu_band', 'memory_band', 'small_pod_exempt', 'account_block_after_violating_pods'):
            self.assertIn('from local override', rows[k])
        self.assertIn(str(self.tmp / 'shared.json'), r.stdout)
        self.assertIn(str(self.tmp / 'local.json'), r.stdout)

    def test_policy_command_without_override_lists_the_checks_that_are_off(self):
        r = self.run_cli('--policy')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('local override: none', r.stdout)
        self.assertIn('off (in neither file): lab_floor, cpu_band, memory_band, small_pod_exempt, account_block_after_violating_pods', r.stdout)
        self.assertIn('max_concurrent_jobs', r.stdout)

    def test_default_local_file_is_in_the_state_dir(self):
        state = self.tmp / 'state'
        state.mkdir()
        (state / 'utilization-policy.local.json').write_text(json.dumps({"lab_floor": 0.5}))
        env = dict(os.environ, NRP_MONITOR_STATE=str(state), NRP_UTIL_POLICY=str(self.write('shared.json', SHARED)))
        env.pop('NRP_UTIL_POLICY_LOCAL', None)
        r = subprocess.run([sys.executable, str(SOURCE), '--policy'], capture_output=True, text=True, env=env)
        self.assertIn(str(state / 'utilization-policy.local.json'), r.stdout)
        self.assertIn('lab_floor', r.stdout.split('off (in neither file)')[0])

    # ---- shared file and built-in fallback
    def test_invalid_shared_file_is_reported_and_falls_back_to_the_builtin_numbers(self):
        for bad in ('{not json', dict(SHARED, gpu_floor=0), {"gpu_floor": 0.4}, dict(SHARED, max_concurrent_jobs=0)):
            m = self.load(shared=bad)
            self.assertEqual(m.POLICY_SRC, 'built-in')
            self.assertIn('not a valid utilization policy', m.POLICY_WARNINGS[0])
            self.assertEqual(m.POLICY, m.POLICY_BUILTIN)

    def test_extra_keys_in_the_shared_file_are_not_shared_numbers(self):
        m = self.load(shared=dict(SHARED, cpu_band=[0.2, 2.0], lab_floor=0.4, version='x', description='y'))
        self.assertEqual(m.POLICY, SHARED)
        self.assertEqual(m.nrp_bad(self.cpu_idle), [])
        self.assertIn('cpu_band, lab_floor', m.POLICY_WARNINGS[0])

    def test_builtin_fallback_has_only_the_shared_numbers(self):
        m = self.load()
        self.assertEqual(m.POLICY_BUILTIN, SHARED)

    def test_builtin_fallback_equals_the_shared_file(self):
        shared = next((p for p in SHARED_CANDIDATES if p.exists()), None)
        if shared is None:
            self.skipTest('the shared utilization-policy.json is not available here')
        content = json.loads(shared.read_text())
        self.assertEqual({k: v for k, v in content.items() if k not in ('version', 'description')}, self.load().POLICY_BUILTIN,
                         'update POLICY_BUILTIN (and the shared file) together')
        m = self.load(shared=content)
        self.assertEqual(m.POLICY, m.POLICY_BUILTIN)

    def test_owner_example_is_valid_and_matches_the_documented_values(self):
        ex = json.loads(EXAMPLE.read_text())
        self.assertEqual(ex, OWNER_LOCAL)
        m = self.load(local=ex)
        self.assertEqual(m.POLICY_WARNINGS, [])
        self.assertEqual({k: m.POLICY[k] for k in ex}, ex)


if __name__ == '__main__':
    unittest.main()

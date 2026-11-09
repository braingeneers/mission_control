"""Bounded follow-up escalation; no models, cluster, or notifications."""
import importlib.machinery
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'nrp-watchdog'
loader = importlib.machinery.SourceFileLoader('watchdog_tiers', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
w = importlib.util.module_from_spec(spec)
loader.exec_module(w)


class FollowupTests(unittest.TestCase):
    def run_tiers(self, responses):
        with patch.object(w, 'run_agent', side_effect=responses) as agent, patch.object(w, 'digest'), patch.object(w, 'log'):
            result = w.tiered_job_followup('job', {'authorize': {'attempt': 1, 'max': 3}}, 'notes', ['Read', 'Edit', 'Bash(kubectl apply:*)'], ['Read', 'Bash(kubectl get:*)'])
        return result, agent.call_args_list

    def test_haiku_success_never_starts_sonnet(self):
        result, calls = self.run_tiers(['DONE: outputs checked'])
        self.assertTrue(w.followup_solved(result))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].args[0][3], 'haiku')
        self.assertNotIn('Edit', calls[0].args[0])
        self.assertNotIn('Bash(kubectl apply:*)', calls[0].args[0])
        self.assertIn('READ-ONLY', calls[0].args[1])

    def test_escalates_with_evidence_and_stops_after_repair(self):
        result, calls = self.run_tiers(['ESCALATE: code bug', 'RESUBMITTED: job'])
        self.assertTrue(w.followup_solved(result))
        self.assertEqual([c.args[0][3] for c in calls], ['haiku', 'sonnet'])
        self.assertIn('code bug', calls[1].args[1])
        self.assertIn('BEFORE deleting/applying', calls[1].args[1])

    def test_timeout_and_unstructured_output_do_not_count_as_success(self):
        result, calls = self.run_tiers(['AGENT TIMEOUT', 'looks fine', 'ESCALATE: missing input'])
        self.assertFalse(w.followup_solved(result))
        self.assertEqual(len(calls), 3)
        self.assertIn('looks fine', calls[2].args[1])
        self.assertIn('missing input', result)

    def check(self, res, replacement=None):
        with tempfile.TemporaryDirectory() as d:
            notes = Path(d) / 'notes.md'
            notes.write_text('task notes')
            rec = {'status': 'watching', 'added': 1, 'resume': str(notes)}
            st = {'jobs': {'job': rec}}
            disk = {'jobs': {'job': replacement or rec}}
            with patch.object(w, 'job_state', return_value='ok'), patch.object(w, 'save'), \
                 patch.object(w, 'log'), patch.object(w, 'job_prompt', return_value='prompt'), \
                 patch.object(w, 'tiered_job_followup', return_value=res) as followup, \
                 patch.object(w, 'push') as push, patch.object(w, 'notify') as notify, \
                 patch.object(w, 'load', return_value=disk), patch.object(w, 'SLOCK', Path(d) / 'lock'), \
                 patch.object(w, 'agents_available', return_value=True):
                w.check_jobs(SimpleNamespace(fake_finished='', dry_run=False), st)
                w.check_jobs(SimpleNamespace(fake_finished='', dry_run=False), st) if not replacement else None
                return st, followup.call_count, push.call_count, notify.call_count

    def test_exhaustion_alerts_once(self):
        _, agents, alerts, _ = self.check('STOPPED after bounded attempts')
        self.assertEqual((agents, alerts), (1, 1))

    def test_success_is_silent(self):
        _, agents, alerts, digests = self.check('DONE: verified')
        self.assertEqual((agents, alerts, digests), (1, 0, 1))

    def test_same_name_registration_survives(self):
        replacement = {'status': 'watching', 'added': 2, 'authorize': {'attempt': 2}}
        st, _, alerts, _ = self.check('RESUBMITTED: job', replacement)
        self.assertEqual(st['jobs']['job'], replacement)
        self.assertEqual(alerts, 0)


if __name__ == '__main__':
    unittest.main()

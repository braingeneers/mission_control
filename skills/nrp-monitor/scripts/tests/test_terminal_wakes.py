"""Late failures and settled outcomes, with temporary state and fake CLIs only."""
import argparse
from unittest.mock import patch

import pytest
from test_escalation_costs import monitor, task
from test_ladder import Ladder, Relay
import test_ladder


@pytest.mark.parametrize('status', ['cancelled', 'done'])
def test_terminal_entry_points(monitor, status):
    m = monitor
    t = task(m)
    m.task_txn(t['name'], lambda v: v.update(status=status))
    args = argparse.Namespace(dry_run=False)
    with patch.object(m, 'dispatch_agent', side_effect=AssertionError('no agents')), \
         patch.object(m, 'kubectl', side_effect=AssertionError('no cluster')), \
         patch.object(m, 'push', side_effect=AssertionError('no owner')):
        m.handle_failure(t['name'], args)
        m.to_coordinator(t['name'], 'stale failure', args)
        m.observe_task(t['name'], {})
        m.advance_task(t['name'], {}, args)
        m.escalate(t['name'], 'stale failure', args)
        assert not m.tier0_fix(t['name'], args)
        assert not m.apply_decision(t['name'], args)
        assert not m.do_submit(t['name'], 'a', 'stale retry', 'agent')[0]
        assert m.run_task_agent(t['name'], 'stale prompt', args)[0].startswith('DONE:')
    assert m.task_load(t['name'])['status'] == status
    assert 'failure-ignored' in (m.STATE / 'digest.log').read_text()
    assert len(m.task_load(t['name'])['ignored_failures']) == 1


@pytest.mark.parametrize('kind', ['deputy', 'fixer'])
@pytest.mark.parametrize('answer', ['RESOLVED', 'DONE'])
def test_settled_outcome_verifies_recovery(monitor, kind, answer):
    m = monitor
    t = task(m)
    with patch.object(m, 'job_state', return_value='running'), patch.object(m, 's3_exists', return_value=False):
        assert m.settled_outcome(t['name'], answer + ': healthy; nothing requested', argparse.Namespace(dry_run=False), kind)
    result = m.task_load(t['name'])
    assert result['failure'] is None
    assert result['stages'][0]['state'] == 'running'
    assert not result.get('webhook_outbox')


@pytest.mark.parametrize('status', ['cancelled', 'done'])
def test_failure_detected_after_terminal_state_is_audit_only(monitor, status):
    m = monitor
    t = task(monitor)
    m.task_txn(t['name'], lambda v: v.update(status=status, failure=None))
    with patch.object(m, 'kubectl', side_effect=AssertionError('no cluster')):
        assert not m.task_fail(t['name'], 'a', 'code', 'traceback', 'old Job failed before cancellation')
    result = m.task_load(t['name'])
    assert result['failure'] is None
    assert result['status'] == status
    assert 'old Job failed before cancellation' in (m.STATE / 'digest.log').read_text()


@pytest.mark.parametrize('answer', ['RESOLVED', 'DONE'])
def test_unrecovered_job_still_needs_work(monitor, answer):
    m = monitor
    t = task(m)
    with patch.object(m, 'job_state', return_value='FAILED'), patch.object(m, 's3_exists', return_value=False):
        assert not m.settled_outcome(t['name'], answer + ': claimed success', argparse.Namespace(dry_run=False), 'deputy')
    assert m.task_load(t['name'])['failure']


class TerminalWakeCommands(Ladder):
    def test_cancelled_queued_failure_and_wake(self):
        self.add()
        self.webhook()
        self.unknown_failure()
        self.triage_says('ESCALATE: failure needs review')
        self.sonnet_plan_stop()
        self.env['NRP_MONITOR_NO_WAKE'] = '1'
        self.run_pass()
        before = len(self.prompts())
        rc, _, err = self.wd('task', 'cancel', 't1')
        self.assertEqual(rc, 0, err)
        self.env.pop('NRP_MONITOR_NO_WAKE')
        self.run_pass()
        self.assertEqual(len(self.prompts()), before)
        self.assertEqual(self.task()['status'], 'cancelled')
        self.assertFalse(self.task().get('webhook_outbox'))
        self.assertFalse(Relay.received)
        self.assertFalse(self.pushes())
        self.assertIn('failure-ignored', (self.state / 'digest.log').read_text())

    def test_cancelled_failed_job_never_enters_ladder(self):
        self.add()
        self.unknown_failure()
        rc, _, err = self.wd('task', 'cancel', 't1')
        self.assertEqual(rc, 0, err)
        # Exercise the late observation path explicitly, using the fake kubectl env.
        self.run_pass()
        self.assertFalse(self.prompts())
        self.assertFalse(self.pushes())
        self.assertEqual(self.task()['status'], 'cancelled')

    def assert_deputy_settles(self, answer):
        self.add()
        self.webhook()
        self.run_pass()
        self.set_job('t1-a', state='running')
        self.inject_failure(cls='code', sig='old-event', detail='stale event on recovered Job')
        self.write_task(lambda t: t['failure'].update(triaged=True))
        (self.state / 'config.json').write_text('{}')
        self.plan({'result': 'STOPPED: deputy should verify'},
                  {'result': 'Reviewed the event.\n' + answer + ': Job is healthy, nothing needed'})
        self.run_pass()
        self.assertIsNone(self.task()['failure'])
        self.assertEqual([r['kind'] for r in self.task()['agent_runs']], ['fix', 'deputy'])
        self.assertFalse(self.task().get('webhook_outbox'))
        self.assertFalse(Relay.received)
        self.assertFalse(self.pushes())

    def test_deputy_done_does_not_wake(self):
        self.assert_deputy_settles('DONE')

    def test_deputy_resolved_does_not_wake(self):
        self.assert_deputy_settles('RESOLVED')

    def test_fixer_done_does_not_start_deputy_or_wake(self):
        self.add()
        self.webhook()
        self.run_pass()
        self.set_job('t1-a', state='running')
        self.inject_failure(cls='code', sig='old-event')
        self.write_task(lambda t: t['failure'].update(triaged=True))
        (self.state / 'config.json').write_text('{}')
        self.plan({'cmds': [['nrp-task', 'report', 'DONE', 'event already settled']],
                   'result': 'DONE: nothing requested'})
        self.run_pass()
        self.assertIsNone(self.task()['failure'])
        self.assertEqual([r['kind'] for r in self.task()['agent_runs']], ['fix'])
        self.assertFalse(Relay.received)
        self.assertFalse(self.pushes())

    def test_active_failure_deputy_escalate_still_wakes(self):
        self.add()
        self.webhook()
        self.run_pass()
        self.set_job('t1-a', state='FAILED', log='Traceback\nValueError: dependency missing')
        (self.state / 'config.json').write_text('{}')
        self.plan({'result': 'STOPPED: routine recovery failed'}, {'result': 'ESCALATE: need a decision'})
        self.run_pass()
        self.assertEqual([r['kind'] for r in self.task()['agent_runs']], ['fix', 'deputy'])
        self.assertEqual(self.task()['status'], 'WITH_COORDINATOR')
        self.assertEqual(len([e for e in Relay.received if e['event_type'] == 'escalation']), 1)
        self.assertFalse(self.pushes())


# Reuse only harness helpers; do not collect the unrelated parent test cases.
for _name, _value in vars(test_ladder.LadderTests).items():
    if not _name.startswith(('test_', '__')):
        setattr(TerminalWakeCommands, _name, _value)

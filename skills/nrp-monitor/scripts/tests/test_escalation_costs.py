"""Batch A contracts, with isolated state and fake runners; no external services."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from test_agent_runners import load_module


@pytest.fixture
def monitor(tmp_path):
    m = load_module(tmp_path / 'state')
    m.STATE.mkdir(parents=True)
    m.TASKS.mkdir(parents=True, exist_ok=True)
    m.TPL = Path(__file__).resolve().parents[1] / 'templates'
    return m


def task(m, name='sample', group='workers'):
    d = m.task_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    manifest = d / 'manifest.json'
    manifest.write_text(json.dumps({'kind': 'Job', 'metadata': {'name': 'work-17'},
                                    'spec': {'template': {'spec': {'containers': [
        {'image': 'worker:v1', 'command': ['python', 'run.py', '--shard-index', '7'], 'args': ['--threshold', '0.1']} ]}}}}))
    t = dict(name=name, label=name, namespace='test', status='running', mode='auto', notes='',
             goal='Process approved items', approved='Owner approved this task', max_retries=4,
             origin={'harness': 'codex', 'session': 'fake-session'}, created=1,
             stages=[dict(id='a', job='work-17', state='failed', attempt=1, manifest=str(manifest),
                          resource_group=group, done_s3=['s3://test/key'])], attempts=[],
             failure=dict(stage='a', job='work-17', cls='infra', sig='gone', detail='work-17 vanished after 23s deadbeef', ts=1))
    t['failure']['fingerprint'] = m.fingerprint(t, t['failure'])
    m.task_write(t)
    return t


@pytest.mark.parametrize('count,expected', [(0,4), (1,4), (16,4), (17,5), (81,21)])
def test_scaled_cap(monitor, count, expected):
    assert monitor.scaled_retry_cap([{}] * count) == expected


def test_fingerprint_numbers_hex_job_whitespace(monitor):
    t = task(monitor)
    original = monitor.fingerprint(t, t['failure'])
    t['stages'][0]['job'] = 'different-200'
    t['failure']['detail'] = ' DIFFERENT-200  vanished AFTER 999s abcdef12345 '
    assert monitor.fingerprint(t, t['failure']) == original
    t['stages'][0]['resource_group'] = 'other-group'
    assert monitor.fingerprint(t, t['failure']) != original
    t['stages'][0]['resource_group'] = 'workers'
    t['failure']['cls'] = 'code'
    assert monitor.fingerprint(t, t['failure']) != original


def test_manifest_identity_preserves_image_and_scientific_arguments(monitor):
    t = task(monitor, group=None)
    p = Path(t['stages'][0]['manifest'])
    original = monitor.fingerprint(t, t['failure'])
    doc = json.loads(p.read_text())
    c = doc['spec']['template']['spec']['containers'][0]
    c['command'][-1] = '52'
    p.write_text(json.dumps(doc))
    assert monitor.fingerprint(t, t['failure']) == original
    c['image'] = 'worker:v2'
    p.write_text(json.dumps(doc))
    assert monitor.fingerprint(t, t['failure']) != original
    c['image'] = 'worker:v1'
    c['args'][-1] = '0.2'
    p.write_text(json.dumps(doc))
    assert monitor.fingerprint(t, t['failure']) != original


@pytest.mark.parametrize('action', ['resubmit', 'resubmit_with_manifest'])
def test_decision_tier_zero_without_agent_and_limit(monitor, action):
    m = monitor
    t = task(m)
    fp = t['failure']['fingerprint']
    m.record_decision(t, fp, action, 'Known recovery', max_uses=1)
    with patch.object(m, 'do_submit', return_value=(True, 'submitted')) as submit, \
         patch.object(m, 'run_task_agent', side_effect=AssertionError('no agent')):
        assert m.apply_decision(t['name'], argparse.Namespace(dry_run=False))
        assert not m.apply_decision(t['name'], argparse.Namespace(dry_run=False))
        assert submit.call_count == 1
    rows = m.cost_rows()
    assert rows[-1]['tier'] == '0' and rows[-1]['fingerprint'] == fp
    assert 'applied coordinator decision ' + fp in '\n'.join(m.task_load(t['name'])['events'])
    other = task(m, name='other')
    assert not m.apply_decision(other['name'], argparse.Namespace(dry_run=False))


def test_decision_submit_refusal_does_not_consume_use(monitor):
    t = task(monitor)
    monitor.record_decision(t, t['failure']['fingerprint'], 'resubmit', 'Known recovery')
    with patch.object(monitor, 'do_submit', return_value=(False, 'RETRY CAP REACHED')):
        assert not monitor.apply_decision(t['name'], argparse.Namespace(dry_run=False))
    assert monitor.decisions(t['name'])[0]['uses'] == 0


@pytest.mark.parametrize('present', [False, None, True])
def test_skip_reuse_requires_all_markers(monitor, present):
    t = task(monitor)
    monitor.record_decision(t, t['failure']['fingerprint'], 'skip_reuse', 'Reuse verified work')
    with patch.object(monitor, 's3_exists', return_value=present):
        assert monitor.apply_decision(t['name'], argparse.Namespace(dry_run=False)) is bool(present)
    assert (monitor.task_load(t['name'])['failure'] is None) is bool(present)


def test_stage_scope_and_task_scope(monitor):
    t = task(monitor)
    fp = t['failure']['fingerprint']
    monitor.record_decision(t, fp, 'resubmit', 'Only stage a', scope='stage')
    t['stages'].append(dict(t['stages'][0], id='b'))
    t['failure']['stage'] = 'b'
    monitor.task_write(t)
    with patch.object(monitor, 'do_submit', return_value=(True, 'submitted')) as submit:
        assert not monitor.apply_decision(t['name'], argparse.Namespace(dry_run=False))
        monitor.record_decision(t, fp, 'resubmit', 'All siblings', scope='task')
        assert monitor.apply_decision(t['name'], argparse.Namespace(dry_run=False))
        assert submit.call_count == 1


def test_escalate_decision_bypasses_deputy(monitor):
    t = task(monitor)
    monitor.record_decision(t, t['failure']['fingerprint'], 'escalate', 'Needs scientific judgment')
    with patch.object(monitor, 'run_task_agent', side_effect=AssertionError('no deputy')):
        assert monitor.apply_decision(t['name'], argparse.Namespace(dry_run=False))
    assert monitor.task_load(t['name'])['status'] == 'WITH_COORDINATOR'


@pytest.mark.parametrize('answer,resolved', [('RESOLVED: resubmitted', True), ('ESCALATE: approval needed', False), ('RESOLVED: I think so', False)])
def test_deputy_verified_state_and_escalation(monitor, answer, resolved):
    m = monitor
    t = task(m)
    def runner(n, prompt, args, kind):
        assert kind == 'deputy'
        assert 'Failure fingerprint:' in prompt and 'Task decisions:' in prompt
        assert 'Never change thresholds' in prompt
        if resolved:
            m.task_txn(n, lambda v: v.update(failure=None))
        return answer, []
    with patch.object(m, 'run_task_agent', side_effect=runner) as run:
        m.to_coordinator(t['name'], 'fixer exhausted', argparse.Namespace(dry_run=False))
        assert run.call_count == 1
    result = m.task_load(t['name'])
    assert (result['status'] == 'WITH_COORDINATOR') is not resolved
    if not resolved:
        assert result['webhook_outbox'][0]['summary'].startswith('Deputy:')
        assert 'Deputy:' in result['webhook_outbox'][0]['summary']
        # A second call for the same fingerprint and attempt must not start an agent.
        m.task_txn(t['name'], lambda v: v.update(status='running'))
        with patch.object(m, 'run_task_agent', side_effect=AssertionError('once only')):
            m.to_coordinator(t['name'], 'still failed', argparse.Namespace(dry_run=False))


def test_deputy_switch_and_failures(monitor):
    t = task(monitor)
    with patch.dict(monitor.OWNER, deputy_enabled=False), patch.object(monitor, 'run_task_agent') as run:
        monitor.to_coordinator(t['name'], 'fixer exhausted', argparse.Namespace(dry_run=False))
        run.assert_not_called()
    monitor.task_txn(t['name'], lambda v: v.update(status='running'))
    with patch.object(monitor, 'run_task_agent', side_effect=TimeoutError):
        monitor.to_coordinator(t['name'], 'fixer exhausted', argparse.Namespace(dry_run=False))
    assert monitor.task_load(t['name'])['status'] == 'WITH_COORDINATOR'


def test_deputy_default_config_and_overrides(monitor):
    assert monitor.OWNER.get('deputy_enabled', True)
    assert monitor.tier_backends('deputy') == [{'runner': 'claude', 'model': 'sonnet'}]
    cfg = monitor.parse_agent_cfg({'tiers': {'deputy': [{'runner':'codex', 'model':'custom'}]},
                                  'limits': {'deputy': {'turns': 5, 'budget': 1, 'timeout': 20}}})
    assert cfg['tiers']['deputy'][0]['model'] == 'custom'
    assert cfg['limits']['deputy']['timeout'] == 20


def test_ledger_report_and_review(monitor, capsys):
    t = task(monitor)
    monitor.queue_task_webhook(t, 'done')
    monitor.cost_event(t['name'], 'fixer', '2', 'resolved', stage='a', model='sonnet', runner='claude',
                       fingerprint=t['failure']['fingerprint'], result={'total_cost_usd': .12, 'usage': {'input_tokens':10, 'output_tokens':5}})
    monitor.cmd_wake_review(argparse.Namespace(name=t['name'], by='rule', why='Known signature'))
    rows = monitor.cost_rows()
    assert rows[-1]['wake_id'] == rows[0]['event_id']
    assert rows[1]['input_tokens'] == 10 and rows[1]['output_tokens'] == 5
    monitor.cmd_costs(argparse.Namespace(days=1, task=t['name']))
    text = capsys.readouterr().out
    assert 'sample / done: 1' in text and '$0.120000' in text
    assert '2: 1 (100.0%)' in text and 'rule / Known signature: 1' in text
    monitor.cmd_costs(argparse.Namespace(days=1, task='other'))
    assert '$0.120000' not in capsys.readouterr().out


def test_task_agent_runner_usage(monitor):
    m = monitor
    t = task(m)
    response = json.dumps({'result': 'ESCALATE: need approval', 'total_cost_usd': .02,
                           'usage': {'input_tokens':23}, 'model': 'custom-sonnet'})
    with patch.object(m, 'agents_available', return_value=True), \
         patch.object(m, 'dispatch_agent', return_value=('claude', 'ok', response, '', 0)):
        m.run_task_agent(t['name'], 'prompt', argparse.Namespace(dry_run=False), kind='deputy')
    row = m.cost_rows()[-1]
    assert row['kind'] == 'deputy' and row['cost_usd'] == .02
    assert row['model'] == 'custom-sonnet' and row['input_tokens'] == 23


# Real command parsing and real nrp-task execution, with fake kubectl/aws/claude.
from test_ladder import Ladder


class BatchACommands(Ladder):
    def enable_deputy(self):
        (self.state / 'config.json').write_text('{}')

    def failure(self):
        self.run_pass()
        self.set_job('t1-a', state='FAILED', term={'reason':'Error', 'exitCode':1},
                     log='Traceback\nValueError: missing environment dependency')

    def test_deputy_resubmits_with_real_fake_runner(self):
        self.add()
        self.failure()
        self.enable_deputy()
        self.plan({'result':'STOPPED: routine environment fix remains'},
                  {'cmds':[['nrp-task','submit','t1-a','--reason','routine environment fixed']],
                   'result':'RESOLVED: fixed environment and resubmitted'})
        self.run_pass()
        t = self.task()
        self.assertIsNone(t['failure'])
        self.assertEqual(t['attempts'][-1]['by'], 'agent')
        self.assertEqual([r['kind'] for r in t['agent_runs']], ['fix', 'deputy'])
        rows = [json.loads(l) for l in (self.state/'costs.jsonl').read_text().splitlines()]
        self.assertEqual(rows[-1]['kind'], 'deputy')
        self.assertEqual(rows[-1]['outcome'], 'resolved')
        self.assertEqual(self.pushes(), [])

    def test_deputy_escalates_then_resume_records_decision(self):
        self.add()
        self.failure()
        self.enable_deputy()
        self.plan({'result':'STOPPED: cannot safely fix'}, {'result':'ESCALATE: dependency failed; tried approved fix; need coordinator judgment'})
        self.run_pass()
        # With no origin wake target the existing owner fallback remains, after the deputy.
        self.assertEqual(self.task()['status'], 'NEEDS_OWNER')
        fp = self.task()['failure']['fingerprint']
        rc, out, err = self.wd('task','resume','t1','--note','Known old code; retry unchanged', '--decide','resubmit')
        self.assertEqual(rc, 0, err)
        entries = json.loads((self.state/'tasks/t1/decisions.json').read_text())
        self.assertEqual(entries[0]['fingerprint'], fp)
        self.assertEqual(entries[0]['scope'], 'task')
        self.assertEqual(self.task()['attempts'][-1]['fingerprint'], fp)

    def test_decide_cli_applies_before_any_agent(self):
        self.add()
        self.run_pass()
        t = self.task()
        # A legacy failure still gets a deterministic fingerprint when inspected.
        f = dict(stage='a', job='t1-a', cls='infra', sig='gone', detail='Job vanished', ts=1)
        m = load_module(self.state)
        fp = m.fingerprint(t, f)
        t['failure'] = dict(f, fingerprint=fp)
        t['stages'][0]['state'] = 'failed'
        (self.state/'tasks/t1/task.json').write_text(json.dumps(t))
        self.set_job('t1-a', state='FAILED')
        rc, out, err = self.wd('decide','t1',fp,'--action','resubmit','--scope','task','--max-uses','1','--why','Known transient')
        self.assertEqual(rc, 0, err)
        self.run_pass()
        self.assertIsNone(self.task()['failure'])
        self.assertEqual(self.prompts(), [])
        self.assertEqual(self.task()['attempts'][-1]['by'], 'decision')
        self.assertEqual(self.task()['attempts'][-1]['fingerprint'], fp)

    def test_default_scaled_cap_and_explicit_override(self):
        stages = [dict(id='s%d'%i, job='job-%d'%i, manifest=self.manifest('job-%d'%i),
                       done_s3=['s3://braingeneersdev/t/%d'%i]) for i in range(21)]
        rc, out, err = self.add(stages=stages)
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.task()['max_retries'], 6)
        stages = [dict(s, job='explicit-%d'%i, manifest=self.manifest('explicit-%d'%i)) for i, s in enumerate(stages)]
        rc, out, err = self.add(name='explicit', stages=stages, max_retries=2)
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.task('explicit')['max_retries'], 2)


def test_setup_preserves_deputy_backend(monitor):
    old = {'tiers': {'deputy': [{'runner':'codex','model':'custom'}]}}
    cfg = monitor.setup_config(old, {'task':[{'runner':'claude','model':'sonnet'}],
                                     'triage':[{'runner':'claude','model':'haiku'}]})
    assert cfg['tiers']['deputy'] == old['tiers']['deputy']
    assert 'codex' in cfg['runners']


def test_deputy_new_attempt_can_run_again(monitor):
    m = monitor
    t = task(m)
    with patch.object(m, 'run_task_agent', return_value=('ESCALATE: need choice', [])) as run:
        m.to_coordinator(t['name'], 'failed', argparse.Namespace(dry_run=False))
        m.task_txn(t['name'], lambda v: (v.update(status='running'), v['attempts'].append(dict(stage='a', job='work-17', cls='infra', sig='gone', detail='vanished', fix='changed environment'))))
        m.to_coordinator(t['name'], 'failed again', argparse.Namespace(dry_run=False))
        assert run.call_count == 2


def test_retry_cap_tool_is_deputy_only_and_bounded(monitor, monkeypatch):
    m = monitor
    t = task(m)
    t['stages'] *= 21
    m.task_write(t)
    monkeypatch.setenv('NRP_TASK', t['name'])
    monkeypatch.setenv('NRP_MONITOR_AGENT_ROLE', 'fix')
    with pytest.raises(SystemExit, match='deputy-only'):
        m.cmd_tool(argparse.Namespace(rest=['retry-cap','6']))
    monkeypatch.setenv('NRP_MONITOR_AGENT_ROLE', 'deputy')
    assert m.cmd_tool(argparse.Namespace(rest=['retry-cap','6'])) == 0
    assert m.task_load(t['name'])['max_retries'] == 6
    with pytest.raises(SystemExit, match='exceeds scaled cap'):
        m.cmd_tool(argparse.Namespace(rest=['retry-cap','7']))


def test_task_failure_persists_fingerprint(monitor):
    t = task(monitor)
    monitor.task_txn(t['name'], lambda v: v.update(failure=None))
    monitor.task_fail(t['name'], 'a', 'infra', 'gone', 'Job work-17 vanished after 21 seconds')
    f = monitor.task_load(t['name'])['failure']
    assert len(f['fingerprint']) == 16
    assert f['fingerprint'] == monitor.fingerprint(t, f)


def test_decision_budget_real_submit_refuses_before_cluster(monitor):
    t = task(monitor)
    t['max_retries'] = 0
    monitor.task_write(t)
    monitor.record_decision(t, t['failure']['fingerprint'], 'resubmit', 'Known failure')
    with patch.object(monitor, 'apply_manifest', side_effect=AssertionError('no apply')):
        assert not monitor.apply_decision(t['name'], argparse.Namespace(dry_run=False))
    assert monitor.task_load(t['name'])['failure']
    assert monitor.decisions(t['name'])[0]['uses'] == 0


def test_dry_run_and_watch_do_not_apply_decision(monitor):
    t = task(monitor)
    monitor.record_decision(t, t['failure']['fingerprint'], 'resubmit', 'Known failure')
    with patch.object(monitor, 'do_submit', side_effect=AssertionError('no submit')):
        assert not monitor.apply_decision(t['name'], argparse.Namespace(dry_run=True))
        monitor.task_txn(t['name'], lambda v: v.update(mode='watch'))
        assert not monitor.apply_decision(t['name'], argparse.Namespace(dry_run=False))

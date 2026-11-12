"""Plan group completion contracts. All subprocesses and state are isolated."""
import argparse
import json
import subprocess
from unittest.mock import patch

import pytest
from test_escalation_costs import monitor, task


def header(m, extra='groups: collect=1,2\n'):
    h = m.parse_run_block('```run\nplan: sample\napproval: Owner 2026-11-12 approved\nsteps: 1,2,3\napproved_through: 2\nstop_for_hunter: 3\n' + extra + '```')
    m.plan_dir('sample').mkdir(parents=True, exist_ok=True)
    m.write_json(m.plan_dir('sample') / 'header.json', h)
    return h


def member(m, name, step, status='done'):
    t = task(m, name)
    t.update(status=status, on_done=dict(plan='sample', from_step=step), failure=None,
             continuation=dict(state='closed', status='WAITING', line='checked outputs; result note saved'))
    t['stages'][0]['state'] = 'done'
    m.task_write(t)
    m.plan_txn('sample', lambda st: st['ledger'].setdefault(step, []).append({'task': name}))
    return t


def test_parse_defaults_and_overrides(monitor):
    h = header(monitor, 'groups: collect=1,2; review=3\nretries: collect=40; review=8\nwake_review: digest\n')
    assert h['wake'] == 'group'
    assert h['retries'] == {'collect': 40, 'review': 8}
    assert h['wake_overrides'] == {'review': 'digest'}
    assert header(monitor, '')['wake'] == 'task'


@pytest.mark.parametrize('extra', ['groups: collect=9\n', 'groups: x=1; y=1\n', 'wake: wrong\n',
                                   'groups: x=1\nretries: x=-2\n', 'wake_x: digest\n'])
def test_bad_headers(monitor, extra):
    with pytest.raises(monitor.ChainError):
        header(monitor, extra)


def test_membership_waits_for_every_step_and_review(monitor):
    m = monitor
    h = header(m)
    a = member(m, 'alpha', '1')
    assert not m.group_ready(h, 'collect', [a])
    b = member(m, 'beta', '2')
    assert m.group_ready(h, 'collect', [a, b])
    for status in ('running', 'WITH_COORDINATOR', 'failed', 'cancelled'):
        b['status'] = status
        assert not m.group_ready(h, 'collect', [a, b])
    b['status'] = 'done'
    b['continuation']['status'] = 'NOT-DONE'
    assert not m.group_ready(h, 'collect', [a, b])


def test_group_one_wake_and_costs(monitor):
    m = monitor
    header(m)
    member(m, 'alpha', '1')
    b = member(m, 'beta', '2')
    with patch.object(m, 'wake_target', return_value={'harness': 'codex', 'session': 'fake'}):
        m.terminal_wake(b)
        assert not b.get('webhook_outbox')
        m.process_group_wakes(argparse.Namespace(dry_run=False))
        m.process_group_wakes(argparse.Namespace(dry_run=False))
    assert len(m.task_load('beta')['webhook_outbox']) == 1
    rows = m.cost_rows()
    assert sum(r['kind'] == 'group_wake' for r in rows) == 1
    assert sum(r['kind'] == 'wake_avoided' for r in rows) == 1
    summary = m.task_load('beta')['webhook_outbox'][0]['summary']
    assert 'alpha' in summary and 'beta' in summary and 'results.md' in summary


def test_digest_no_wake_but_stop_and_not_done_wake_reason(monitor):
    m = monitor
    header(m, 'wake: digest\n')
    a = member(m, 'alpha', '2')
    a['continuation']['registered'] = []
    m.task_write(a)
    with patch.object(m, 'wake_target', return_value={'harness': 'codex', 'session': 'fake'}):
        m.terminal_wake(a)
        assert not a.get('webhook_outbox')
        m.close_continuation('alpha', 'WAITING', 'ready for review')
        assert 'Planned stop' in m.task_load('alpha')['webhook_outbox'][-1]['summary']
        m.close_continuation('alpha', 'NOT-DONE', 'checked sidecar; count missing')
        assert 'count missing' in m.task_load('alpha')['webhook_outbox'][-1]['summary']


def test_legacy_terminal_behavior(monitor):
    m = monitor
    header(m, '')
    a = member(m, 'alpha', '1')
    with patch.object(m, 'step_siblings', return_value=[]), patch.object(m, 'queue_task_webhook', return_value='event') as q:
        m.terminal_wake(a)
    assert q.call_count == 1 and a['done_event_id'] == 'event'


def test_postcheck_exact_command_and_timeout(monitor):
    m = monitor
    t = task(m)
    t['postcheck'] = {'cmd': ['python', 'checker.py'], 'expect': 'PASS'}
    with patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'PASS\n', '')) as run:
        assert m.run_postcheck(t)['ok']
        assert run.call_args.args[0] == t['postcheck']['cmd']
        assert run.call_args.kwargs['timeout'] == 120
    with patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'FAIL', '')):
        assert not m.run_postcheck(t)['ok']
    with patch.object(m.subprocess, 'run', side_effect=subprocess.TimeoutExpired([], 120)):
        assert not m.run_postcheck(t)['ok']


def test_success_logs_refresh_and_extract_stdout_only(monitor):
    m = monitor
    t = task(m)
    p = m.task_dir(t['name']) / 'logs' / 'work-17-a1.txt'
    p.parent.mkdir()
    p.write_text('old describe only' * 100)
    def kube(*args, **kw):
        return subprocess.CompletedProcess(args, 0, 'COUNT=42\nRESULT_URI=s3://bucket/result\n' if 'logs' in args else 'EVENT=ignored', '')
    with patch.object(m, 'kubectl', side_effect=kube) as k:
        m.save_task_logs(t, t['stages'][0], 'Job succeeded')
    assert k.call_count == 3
    assert m.task_load(t['name'])['stages'][0]['outputs'] == {'COUNT': '42', 'RESULT_URI': 's3://bucket/result'}
    assert 'COUNT=42' in p.read_text()


def test_plan_retry_default_and_explicit_override(monitor):
    m = monitor
    header(m, 'groups: collect=1,2\nretries: collect=40\n')
    od = dict(plan='sample', from_step='1')
    # Stop after validation; inspect exactly what registration passed to it.
    for explicit, expected in ((None, 40), (7, 7)):
        raw = {'on_done': od.copy()}
        if explicit is not None:
            raw['max_retries'] = explicit
        with patch.object(m, 'check_on_done', return_value=od), \
             patch.object(m, 'validate_task', side_effect=m.ChainError('stop here')) as validate:
            with pytest.raises(SystemExit):
                m.task_add_raw(raw, 'TASK.json')
        assert validate.call_args.args[0]['max_retries'] == expected


@pytest.mark.parametrize('destination', ['s3://other/key', '/tmp/outside'])
def test_copy_scope_refused_before_subprocess(monitor, monkeypatch, destination):
    m = monitor
    header(m, 'groups: collect=1,2\nmay_touch: s3://test/allowed/\n')
    t = member(m, 'alpha', '1')
    monkeypatch.setenv('NRP_TASK', t['name'])
    with patch.object(m.subprocess, 'run', side_effect=AssertionError('must not call externally')):
        with pytest.raises(SystemExit):
            m.cmd_tool(argparse.Namespace(rest=['s3', 'cp', 's3://test/allowed/object', destination]))


def test_success_copy_bounded_and_exact(monitor, monkeypatch):
    m = monitor
    header(m, 'groups: collect=1,2\nmay_touch: s3://test/allowed/\n')
    t = member(m, 'alpha', '1')
    monkeypatch.setenv('NRP_TASK', t['name'])
    results = [subprocess.CompletedProcess([], 0, '{"ContentLength":42}', ''), subprocess.CompletedProcess([], 0, 'copied', '')]
    with patch.object(m.subprocess, 'run', side_effect=results) as run:
        assert m.cmd_tool(argparse.Namespace(rest=['s3', 'cp', 's3://test/allowed/in', 's3://test/allowed/out'])) == 0
        assert run.call_args.args[0][-4:] == ['s3', 'cp', 's3://test/allowed/in', 's3://test/allowed/out']
    with patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '{"ContentLength":262145}', '')) as run:
        with pytest.raises(SystemExit):
            m.cmd_tool(argparse.Namespace(rest=['s3', 'cp', 's3://test/allowed/in', 's3://test/allowed/out']))
        assert run.call_count == 1


def test_ungrouped_step_retains_task_wake(monitor):
    header(monitor)
    t = member(monitor, 'review', '3')
    assert monitor.completion_policy(t) == 'task'


def test_deleted_member_blocks_group_and_claim_survives_plan_state_loss(monitor):
    m = monitor
    h = header(m)
    a = member(m, 'alpha', '1')
    b = member(m, 'beta', '2')
    m.plan_txn('sample', lambda st: st['ledger'].update({'1': [{'task': 'lost'}]}))
    assert not m.group_ready(h, 'collect', [a, b])
    m.plan_txn('sample', lambda st: st['ledger'].clear())
    with patch.object(m, 'wake_target', return_value={'harness': 'codex', 'session': 'fake'}):
        m.process_group_wakes(argparse.Namespace(dry_run=False))
        m.write_json(m.plan_dir('sample') / 'state.json', {})
        m.process_group_wakes(argparse.Namespace(dry_run=False))
    assert len(m.task_load('beta')['webhook_outbox']) == 1


def test_group_policy_runs_each_task_continuation(monitor):
    m = monitor
    header(m)
    for name in ('alpha', 'beta'):
        t = member(m, name, '1')
        t.pop('continuation')
        m.task_write(t)
    with patch.object(m, 'continue_task') as cont:
        m.process_continuations(argparse.Namespace(dry_run=False))
        assert {call.args[0] for call in cont.call_args_list} == {'alpha', 'beta'}


def test_failed_postcheck_enters_ladder_without_done_wake(monitor):
    m = monitor
    t = task(m)
    t['failure'] = None
    t['stages'][0].update(state='done', after=[])
    t['postcheck'] = {'cmd': ['checker'], 'expect': 'PASS'}
    m.task_write(t)
    with patch.object(m, 'observe_task'), patch.object(m, 'report_long_pending'), \
         patch.object(m, 'process_util_event'), patch.object(m, 'run_postcheck', return_value={'ok': False, 'output': 'bad count'}), \
         patch.object(m, 'handle_failure') as ladder, patch.object(m, 'queue_task_webhook') as wake:
        m.advance_task(t['name'], {}, argparse.Namespace(dry_run=False))
    assert ladder.call_count == 1
    assert wake.call_count == 0
    current = m.task_load(t['name'])
    assert current['status'] != 'done'
    assert current['failure']['sig'] == 'postcheck'
    assert 'bad count' in current['failure']['detail']


def test_digest_stop_once_after_all_step_members(monitor):
    m = monitor
    header(m, 'wake: digest\n')
    for name in ('alpha', 'beta'):
        t = member(m, name, '2')
        t['continuation'] = {'state': 'running', 'registered': []}
        m.task_write(t)
    with patch.object(m, 'wake_target', return_value={'harness': 'codex', 'session': 'fake'}):
        m.close_continuation('alpha', 'WAITING', 'review ready')
        assert not m.task_load('alpha').get('webhook_outbox')
        m.close_continuation('beta', 'WAITING', 'review ready')
        m.close_continuation('alpha', 'WAITING', 'review ready')
    assert sum(len(m.task_load(n).get('webhook_outbox', [])) for n in ('alpha', 'beta')) == 1


def test_not_done_replaces_sibling_legacy_event(monitor):
    m = monitor
    header(m, '')
    member(m, 'alpha', '1')
    b = member(m, 'beta', '1')
    with patch.object(m, 'wake_target', return_value={'harness': 'codex', 'session': 'fake'}):
        m.terminal_wake(b)
        m.task_write(b)
        m.close_continuation('alpha', 'NOT-DONE', 'checked sidecars; missing count')
    events = [e for n in ('alpha', 'beta') for e in m.task_load(n).get('webhook_outbox', [])]
    assert len(events) == 1
    assert 'missing count' in events[0]['summary']

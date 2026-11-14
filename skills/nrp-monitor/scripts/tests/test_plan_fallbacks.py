"""Late registration and bounded backup coordinator wakes, with isolated state."""
import argparse
from unittest.mock import patch
import pytest
from test_plan_groups import header, member
from test_escalation_costs import monitor

ARGS = argparse.Namespace(dry_run=False)


@pytest.fixture(autouse=True)
def _armed(monitor):
    monitor.FALLBACK_SINCE = 0

@pytest.mark.parametrize('status,started,covered', [('NOT-DONE',300,False), ('STOPPED',300,False), ('FAILED',300,False), ('CONTINUED',100,False), ('WAITING',100,False), ('CONTINUED',300,True), ('WAITING',300,True)])
def test_sibling_coverage(monitor, status, started, covered):
    m = monitor
    header(m, '')
    a = member(m, 'alpha', '1')
    a['continuation'].update(status=status, started=started)
    m.task_write(a)
    b = member(m, 'beta', '1')
    b['created'] = 200
    b.pop('continuation')
    m.task_write(b)
    with patch.object(m, 'continue_task') as cont:
        m.process_continuations(ARGS)
    assert bool(cont.call_count) != covered
    assert ((m.task_load('beta').get('continuation') or {}).get('status') == 'COVERED') == covered


def test_group_late_registration(monitor):
    m = monitor
    header(m)
    member(m, 'alpha', '1')
    member(m, 'beta', '2')
    m.process_group_wakes(ARGS)
    t = member(m, 'late', '1')
    t.pop('continuation')
    m.task_write(t)
    with patch.object(m, 'continue_task') as cont:
        m.process_continuations(ARGS)
    cont.assert_called_once_with('late', ARGS)
    assert sum(r['kind'] == 'group_wake' for r in m.cost_rows()) == 1
    t['continuation'] = dict(state='closed', status='WAITING')
    m.task_write(t)
    m.process_group_wakes(ARGS)
    m.process_group_wakes(ARGS)
    assert sum(r['kind'] == 'group_wake' for r in m.cost_rows()) == 2


def idle(m, extra=''):
    header(m, extra)
    t = member(m, 'alpha', '1')
    t['finished'] = 100
    m.task_write(t)
    m.plan_txn('sample', lambda st: st.update(status='waiting'))
    return t


def sweep(m, ts, dry=False):
    with patch.object(m, 'now', return_value=ts):
        m.process_plan_fallbacks(argparse.Namespace(dry_run=dry))


def wakes(m):
    return [r for r in m.cost_rows() if r['kind'] == 'plan-fallback']


def test_threshold_single_wake_and_dry_run(monitor):
    m = monitor
    idle(m)
    first = 100 + 3 * 3600
    sweep(m, first - 1)
    sweep(m, first, dry=True)
    assert not wakes(m)
    sweep(m, first)
    sweep(m, first + 86400 - 1)
    assert len(wakes(m)) == 1
    m.cost_event('alpha', 'coordinator_result', 'coordinator', 'done', wake_kind='plan-fallback')
    for day in (1, 2, 3, 4):
        sweep(m, first + day * 86400)
    assert len(wakes(m)) == 1
    assert "exhausted" not in m.plan_state("sample")["fallback_period"]


@pytest.mark.parametrize('extra', ['fallback: off\n', 'fallback_hours: 12\n'])
def test_disabled_or_custom_threshold(monitor, extra):
    idle(monitor, extra)
    sweep(monitor, 100 + 4 * 3600)
    assert not wakes(monitor)


@pytest.mark.parametrize('activity', ['registration', 'sync', 'review', 'delivered'])
def test_activity_resets_period(monitor, activity):
    m = monitor
    idle(m)
    first = 100 + 3 * 3600
    sweep(m, first)
    ts = first + 86400
    with patch.object(m, 'now', return_value=ts):
        if activity == 'registration':
            t = member(m, 'beta', '1')
            t.update(created=ts, finished=ts)
            m.task_write(t)
        elif activity == 'sync':
            m.plan_txn('sample', lambda st: st.update(activity_at=ts))
        else:
            m.cost_event('alpha', 'wake_review' if activity == 'review' else 'coordinator_result', 'coordinator', 'done', wake_kind='done')
    sweep(m, ts + 1)
    assert len(wakes(m)) == 1
    sweep(m, ts + 3 * 3600)
    assert len(wakes(m)) == 2
    assert m.plan_state('sample')['fallback_period']['count'] == 1


def test_owner_stop_after_delivery(monitor):
    m = monitor
    t = idle(m)
    t['on_done']['from_step'] = '2'
    t['stop_event_id'] = 'stop-id'
    m.task_write(t)
    with patch.object(m, 'now', return_value=110):
        m.cost_event('alpha', 'coordinator_result', 'coordinator', 'done', event_id='stop-id')
    sweep(m, 100 + 4 * 3600)
    assert not wakes(m)


@pytest.mark.parametrize('status', ['running', 'WITH_COORDINATOR', 'NEEDS_OWNER', 'blocked'])
def test_live_or_held_prevents_fallback(monitor, status):
    m = monitor
    t = idle(m)
    t['status'] = status
    m.task_write(t)
    sweep(m, 100 + 4 * 3600)
    assert not wakes(m)


def test_cancelled_task_delivers_fallback(monitor, monkeypatch):
    m = monitor
    t = idle(m)
    t['status'] = 'cancelled'
    m.task_write(t)
    sweep(m, 100 + 4 * 3600)
    monkeypatch.delenv('NRP_MONITOR_NO_WAKE', raising=False)
    with patch.dict(m.WAKE_EXEC, {'codex': lambda target, text: {}}):
        m.process_task_webhooks(ARGS, {})
    assert not m.task_load('alpha')['webhook_outbox']
    assert any(r['kind'] == 'coordinator_result' and r.get('wake_kind') == 'plan-fallback' for r in m.cost_rows())


def test_late_task_gets_terminal_wake(monitor):
    m = monitor
    header(m, '')
    a = member(m, 'alpha', '1')
    with patch.object(m, 'now', return_value=100):
        m.terminal_wake(a)
    # Older claims can reconstruct their creation time from the cost ledger.
    a.pop('done_wake_started')
    m.task_write(a)
    b = member(m, 'beta', '1')
    b['created'] = 200
    m.terminal_wake(b)
    assert b.get('done_event_id') and b['done_event_id'] != a['done_event_id']


@pytest.mark.parametrize('raw', ['fallback_hours: 0', 'fallback_hours: nan', 'fallback_hours: inf', 'fallback_hours: text', 'fallback: invalid'])
def test_fallback_bad_header(monitor, raw):
    with pytest.raises(monitor.ChainError):
        header(monitor, raw + '\n')


def test_running_continuation_covers_and_live_sibling_holds(monitor):
    m = monitor
    header(m, '')
    a = member(m, 'alpha', '1')
    a['continuation'] = dict(state='running', started=m.now())
    m.task_write(a)
    b = member(m, 'beta', '1')
    b.pop('continuation')
    m.task_write(b)
    with patch.object(m, 'continue_task') as cont:
        m.process_continuations(ARGS)
    cont.assert_not_called()
    assert m.task_load('beta')['continuation']['status'] == 'COVERED'
    a['status'] = 'running'
    m.task_write(a)
    b.pop('continuation', None)
    m.task_write(b)
    with patch.object(m, 'continue_task') as cont:
        m.process_continuations(ARGS)
    cont.assert_not_called()
    assert 'step_waits_for' in m.task_load('beta')


def test_undelivered_stop_still_gets_backup(monitor):
    m = monitor
    t = idle(m)
    t['on_done']['from_step'] = '2'
    t['stop_event_id'] = 'not-delivered'
    m.task_write(t)
    sweep(m, 100 + 4 * 3600)
    assert len(wakes(m)) == 1


def test_real_plan_sync_resets_idle(monitor, tmp_path):
    m = monitor
    idle(m)
    first = 100 + 3 * 3600
    sweep(m, first)
    src = tmp_path / 'PLAN.md'
    src.write_text('```run\nplan: sample\napproval: Owner approved 2026-11-12\nsteps: 1,2,3\napproved_through: 2\nstop_for_hunter: 3\n```\n')
    with patch.object(m, 'now', return_value=first + 100):
        m.plan_sync(src, 'sample')
    sweep(m, first + 101)
    assert len(wakes(m)) == 1
    sweep(m, first + 100 + 3 * 3600)
    assert len(wakes(m)) == 2


@pytest.mark.parametrize('kind', ['wake_review', 'coordinator_result'])
def test_activity_before_first_wake_delays_threshold(monitor, kind):
    m = monitor
    idle(m)
    activity = 100 + 2 * 3600
    with patch.object(m, 'now', return_value=activity):
        m.cost_event('alpha', kind, 'coordinator', 'done', wake_kind='done')
    sweep(m, 100 + 3 * 3600)
    sweep(m, activity + 3 * 3600 - 1)
    assert not wakes(m)
    sweep(m, activity + 3 * 3600)
    sweep(m, activity + 6 * 3600)
    assert len(wakes(m)) == 1


def close(m, force=False, why='All results reviewed and delivered'):
    return m.cmd_plan_close(argparse.Namespace(id='sample', why=why, force=force))


def test_closed_plan_no_fallback_or_continuation_or_wait(monitor, capsys):
    m = monitor
    t = idle(m)
    t.pop('continuation')
    m.task_write(t)
    with patch.object(m, 'now', return_value=200):
        close(m)
    st = m.plan_state('sample')
    assert st['status'] == 'closed' and st['closed_at'] == 200
    assert st['reason'] == 'All results reviewed and delivered'
    assert any(m.iso(200) in e and st['reason'] in e for e in st['events'])
    before = st['ledger']
    with patch.object(m, 'continue_task') as cont, patch.object(m, 'run_task_agent') as agent:
        sweep(m, 100 + 4 * 3600)
        m.process_continuations(ARGS)
        m.process_continuations(ARGS)
        cont.assert_not_called()
        agent.assert_not_called()
    assert not wakes(m)
    assert m.task_load('alpha')['continuation']['status'] == 'PLAN-CLOSED'
    assert m.plan_state('sample')['ledger'] == before
    assert '0 waiting on the owner' in m.render_digest(24)
    m.cmd_plan_list(ARGS)
    assert 'sample [closed]' in capsys.readouterr().out


@pytest.mark.parametrize('status,continuation', [
    ('running', None), ('NEEDS_OWNER', None), ('blocked', None),
    ('done', {'state': 'running', 'started': 100}),
    ('failed', {'state': 'running', 'started': 100}),
    ('cancelled', {'state': 'running', 'started': 100}),
])
def test_close_refuses_live_tasks_force_preserves_them(monitor, capsys, status, continuation):
    m = monitor
    t = idle(m)
    t.update(status=status, continuation=continuation)
    m.task_write(t)
    with pytest.raises(SystemExit, match='alpha'):
        close(m)
    assert m.plan_state('sample')['status'] == 'waiting'
    close(m, force=True)
    assert 'Live tasks left unchanged: alpha' in capsys.readouterr().out
    assert m.task_load('alpha') == t
    assert m.plan_state('sample')['status'] == 'closed'
    assert 'forced with live tasks: alpha' in m.plan_state('sample')['events'][-1]


@pytest.mark.parametrize('status', ['done', 'failed', 'cancelled'])
def test_close_accepts_terminal_tasks(monitor, status):
    t = idle(monitor)
    t['status'] = status
    monitor.task_write(t)
    assert close(monitor) == 0


def test_closed_sync_requires_explicit_reopen(monitor, tmp_path):
    m = monitor
    idle(m)
    close(m)
    src = tmp_path / 'PLAN.md'
    src.write_text('```run\nplan: sample\napproval: Owner approved 2026-11-12\nsteps: 1,2,3\napproved_through: 2\nstop_for_hunter: 3\n```\n')
    m.cmd_plan_sync(argparse.Namespace(ref=str(src) + '#sample', reopen=False))
    assert m.plan_state('sample')['status'] == 'closed'
    with pytest.raises(m.ChainError, match='closed'):
        m.check_on_done({'plan': 'sample', 'from_step': '2'}, {}, None, 'continuation', 'alpha')
    # A continuation already running when forced closed cannot reopen the plan on return.
    t = m.task_load('alpha')
    t['continuation'] = {'state': 'running', 'started': 100}
    m.task_write(t)
    m.close_continuation('alpha', 'WAITING', 'late result')
    assert m.plan_state('sample')['status'] == 'closed'
    m.plan_set('sample', 'waiting', 'late status update')
    assert m.plan_state('sample')['status'] == 'closed'
    m.cmd_plan_sync(argparse.Namespace(ref=str(src) + '#sample', reopen=True))
    assert m.plan_state('sample')['status'] == 'running'
    assert any('reopened' in e for e in m.plan_state('sample')['events'])


def test_close_cli_help_and_required_reason(monitor):
    import os
    import subprocess
    import sys
    env = dict(os.environ, NRP_MONITOR_STATE=str(monitor.STATE))
    command = [sys.executable, monitor.__file__, 'plan', 'close']
    help_result = subprocess.run(command + ['--help'], env=env, capture_output=True, text=True)
    assert help_result.returncode == 0
    assert '--why' in help_result.stdout and '--force' in help_result.stdout
    missing = subprocess.run(command + ['sample'], env=env, capture_output=True, text=True)
    assert missing.returncode == 2 and '--why' in missing.stderr
    idle(monitor)
    result = subprocess.run(command + ['sample', '--why', 'Reviewed'], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert monitor.plan_state('sample')['status'] == 'closed'


def test_forced_close_late_task_finish_records_only(monitor):
    m = monitor
    t = idle(m)
    t.update(status='running')
    t.pop('continuation')
    m.task_write(t)
    close(m, force=True)
    m.task_txn('alpha', lambda t: t.update(status='done'))
    m.process_continuations(ARGS)
    late = m.task_load('alpha')
    assert late['status'] == 'done'
    assert not late.get('webhook_outbox')
    assert late['continuation']['status'] == 'PLAN-CLOSED'
    assert m.plan_state('sample')['status'] == 'closed'

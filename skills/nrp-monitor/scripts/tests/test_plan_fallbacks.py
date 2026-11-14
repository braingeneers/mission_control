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

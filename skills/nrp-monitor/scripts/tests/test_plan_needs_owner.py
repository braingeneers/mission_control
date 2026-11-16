"""Plan owner decisions with isolated state and mocked notifications."""
import argparse
from unittest.mock import patch
import pytest
from test_escalation_costs import monitor
from test_plan_fallbacks import idle, sweep, wakes


def request(m, reason='The owner must decide the next limit', by=None):
    return m.cmd_plan_needs_owner(argparse.Namespace(id='sample', reason=reason, by=by))


def resume(m, note=None):
    return m.cmd_plan_resume(argparse.Namespace(id='sample', note=note))


def test_wait_single_dm_and_repeat_wait(monitor, capsys):
    m = monitor
    idle(m)
    with patch.object(m, 'push') as dm, patch.object(m, 'now', return_value=200), patch.dict(m.os.environ, {'CODEX_THREAD_ID': 'synthetic-chat', 'CLAUDE_CODE_SESSION_ID': ''}):
        request(m)
        st = m.plan_state('sample')
        assert st['status'] == 'waiting' and st['since'] == 200
        assert st['owner_wait'] == dict(reason=st['reason'], since=200, by='synthetic-chat')
        assert any('needs the owner' in e for e in st['events'])
        dm.assert_called_once()
        assert dm.call_args.args[1] == 'plan-owner:sample:1'
        assert 'nrp-monitor plan resume sample' in dm.call_args.args[0]
        with pytest.raises(SystemExit, match=st['reason']):
            request(m)
        assert dm.call_count == 1
        resume(m, 'The owner approved the next step')
        request(m, by='synthetic-coordinator')
        assert dm.call_args.args[1] == 'plan-owner:sample:2'
        assert m.plan_state('sample')['owner_wait']['by'] == 'synthetic-coordinator'
    assert 'plan sample now waits on the owner' in capsys.readouterr().out


@pytest.mark.parametrize('status', ['done', 'failed', 'cancelled'])
def test_terminal_task_redirect(monitor, status, capsys):
    m = monitor
    t = idle(m)
    t['status'] = status
    m.task_write(t)
    with patch.object(m, 'push') as dm:
        m.cmd_task_needs_owner(argparse.Namespace(name='alpha', reason='The owner must decide next', by='synthetic-coordinator'))
        dm.assert_called_once()
    assert m.task_load('alpha') == t
    assert m.plan_state('sample')['owner_wait']['by'] == 'synthetic-coordinator'
    assert 'plan sample now waits' in capsys.readouterr().out


@pytest.mark.parametrize('status', ['done', 'failed', 'cancelled'])
def test_terminal_without_plan_hint(monitor, status):
    m = monitor
    t = idle(m)
    t.update(status=status, on_done=None)
    m.task_write(t)
    with patch.object(m, 'push') as dm, pytest.raises(SystemExit, match='plan needs-owner'):
        m.cmd_task_needs_owner(argparse.Namespace(name='alpha', reason='The owner must decide next'))
    dm.assert_not_called()


def test_live_task_unchanged(monitor):
    m = monitor
    t = idle(m)
    t['status'] = 'WITH_COORDINATOR'
    m.task_write(t)
    with patch.object(m, 'escalate') as escalate, patch.object(m, 'cmd_plan_needs_owner') as plan:
        m.cmd_task_needs_owner(argparse.Namespace(name='alpha', reason='The owner must decide next'))
    escalate.assert_called_once_with('alpha', 'the coordinator chat needs you: The owner must decide next', None)
    plan.assert_not_called()


def test_fallback_suppressed_resume_rearms(monitor):
    m = monitor
    m.FALLBACK_SINCE = 0
    idle(m)
    with patch.object(m, 'push'), patch.object(m, 'now', return_value=200):
        request(m)
    sweep(m, 100 + 4 * 3600)
    assert not wakes(m)
    resumed = 100 + 5 * 3600
    with patch.object(m, 'now', return_value=resumed):
        resume(m)
    st = m.plan_state('sample')
    assert not st.get('owner_wait') and st['status'] == 'running' and st['activity_at'] == resumed
    sweep(m, resumed + 3 * 3600 - 1)
    assert not wakes(m)
    sweep(m, resumed + 3 * 3600)
    assert len(wakes(m)) == 1
    with pytest.raises(SystemExit, match='no owner wait'):
        resume(m)


def test_sync_digest_and_display(monitor, tmp_path, capsys):
    m = monitor
    idle(m)
    with patch.object(m, 'push'):
        request(m)
    digest = m.render_digest(24)
    assert '## Needs the owner (1)' in digest
    assert 'plan sample (since ' in digest and 'nrp-monitor plan show sample' in digest
    m.cmd_plan_show(argparse.Namespace(id='sample'))
    m.cmd_plan_list(argparse.Namespace())
    assert capsys.readouterr().out.count('owner wait since') == 2
    src = tmp_path / 'PLAN.md'
    src.write_text('```run\nplan: sample\napproval: The owner approved this change\nsteps: 1,2,3\napproved_through: 3\n```\n')
    m.plan_sync(src, 'sample')
    st = m.plan_state('sample')
    assert not st.get('owner_wait') and st['status'] == 'running'
    assert any('owner wait cleared by plan sync' in e for e in st['events'])
    assert '## Needs the owner (0)' in m.render_digest(24)


def test_refusals(monitor):
    m = monitor
    with pytest.raises(SystemExit, match='no plan'):
        request(m)
    idle(m)
    with pytest.raises(SystemExit, match='--reason'):
        request(m, reason='short')
    m.plan_txn('sample', lambda st: st.update(status='closed'))
    with patch.object(m, 'push') as dm, pytest.raises(SystemExit, match='closed'):
        request(m)
    dm.assert_not_called()


def test_push_path_records_one_dm_per_wait(monitor):
    m = monitor
    idle(m)
    with patch.dict(m.os.environ, {'NRP_MONITOR_NO_PUSH': '1'}), patch.object(m, 'banner') as sink, patch.object(m, 'slack_dm', side_effect=AssertionError('real DM forbidden')), patch.object(m, 'claude_push', side_effect=AssertionError('real push forbidden')):
        request(m)
        with pytest.raises(SystemExit, match='already waits'):
            request(m)
        assert sink.call_count == 1
        resume(m)
        request(m)
        assert sink.call_count == 2
    rows = [r for r in m.cost_rows() if r['kind'] == 'owner_dm']
    assert [r['notification_key'] for r in rows] == ['plan-owner:sample:1', 'plan-owner:sample:2']


def test_cli_commands(monitor):
    import os
    import subprocess
    import sys
    from test_isolation import wake_env
    m = monitor
    idle(m)
    env = dict(os.environ, **wake_env(m.STATE.parent / 'cli'), NRP_MONITOR_STATE=str(m.STATE), NRP_MONITOR_NO_PUSH='1')
    from pathlib import Path
    binaries = Path(env['NRP_MONITOR_T3_BIN']).parent
    banner = binaries / 'osascript'
    banner.write_text('#!/bin/sh\nexit 0\n')
    banner.chmod(0o755)
    env['PATH'] = str(binaries) + os.pathsep + env['PATH']
    cmd = [sys.executable, m.__file__, 'plan']
    for args in [['needs-owner', 'sample', '--reason', 'The owner must decide next', '--by', 'synthetic-cli'], ['resume', 'sample', '--note', 'Decision recorded']]:
        result = subprocess.run(cmd + args, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    assert not m.plan_state('sample').get('owner_wait')

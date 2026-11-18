"""Synthetic comparator evidence; no cluster or installed monitor execution."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('shadow_compare', Path(__file__).resolve().parents[2] / 'rewrite/shadow/compare.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
TASKS = {'t': {'stages': [{'id': 'a', 'job': 'job-a', 'state': 'running'}, {'id': 'b', 'job': 'job-b', 'state': 'pending'}]}}


def row(category='submit'):
    return dict(task='t', stage='a', category=category, start='2026-11-18T10:00:00', deadline='2026-11-18T10:10:00')


def event(category='submit', time='2026-11-18T10:05:00', stage='a'):
    return dict(task='t', stage=stage, category=category, time=time, evidence='synthetic line 1')


def test_future_match_resolves_pending():
    pending = c.judge(row(), [], '2026-11-18T10:01:00')
    assert pending['verdict'] == 'pending'
    assert c.judge(pending, [event()], '2026-11-18T10:15:00')['verdict'] == 'matched'


def test_no_evidence_expires_unknown():
    assert c.judge(row('wait'), [], '2026-11-18T10:15:00')['verdict'] == 'unknown'


def test_first_conflict_not_hidden_by_later_match():
    assert c.judge(row(), [event('mark_failed'), event(time='2026-11-18T10:06:00')], '2026-11-18T10:07:00')['verdict'] == 'unexplained'


def test_stage_and_window_bounds():
    assert c.judge(row(), [event(stage='b'), event(time='2026-11-18T09:59:59'), event(time='2026-11-18T10:10:01')], '2026-11-18T10:09:00')['verdict'] == 'pending'


def test_cascade_never_assigned_to_siblings():
    actions = [dict(task='t', stage='a', time='now', would_do='kubectl apply'), dict(task='t', stage='a', time='now', would_do='observation', message='stage a FAILED [infra] submit skipped'), dict(task='t', stage='b', time='now', would_do='agents.dispatch_agent')]
    rows, provisional = c.shadow_decisions(actions, TASKS)
    assert [r['category'] for r in rows] == ['submit', 'unobserved']
    assert len(provisional) == 2


def test_failure_before_skipped_agent():
    actions = [dict(task='t', stage=None, time='now', would_do='observation', message='stage a FAILED [code] problem'), dict(task='t', stage='a', time='now', would_do='agents.dispatch_agent')]
    rows, _ = c.shadow_decisions(actions, TASKS)
    assert rows[0]['category'] == 'mark_failed'


def test_write_block_is_suppression():
    actions = [dict(task='t', stage='a', time='now', would_do='filesystem write outside isolated state'), dict(task='t', stage='a', time='now', would_do='observation', message='stage a FAILED write blocked')]
    rows, provisional = c.shadow_decisions(actions, TASKS)
    assert rows[0]['category'] == 'suppressed_write'
    assert len(provisional) == 1


def test_installed_context_and_sanitized_evidence():
    events = c.installed_events(['2026-11-18T10:00:00 task t: stage a FAILED [code] private detail', '2026-11-18T10:00:01 task t: fix agent start', '2026-11-18T10:00:02 task t: submitted job-b (attempt 1) by monitor'], TASKS)
    assert [(e['stage'], e['category']) for e in events] == [('a', 'mark_failed'), ('a', 'fix_agent'), ('b', 'submit')]
    assert 'private detail' not in str(events)


def test_explicit_wait_and_safety_stop():
    assert c.category('stage a waits on 1 S3 key(s): private') == 'wait'
    assert c.category('WITH_COORDINATOR: NRP band violation safety stop: private') == 'safety_stop'


def test_completion_before_suppressed_delete_survives():
    actions = [dict(task='t', stage='a', time='now', would_do='decision', category='mark_done'), dict(task='t', stage=None, time='now', would_do='kubectl delete'), dict(task='t', stage=None, time='now', would_do='observation', message='stage a FAILED postcheck skipped')]
    rows, provisional = c.shadow_decisions(actions, TASKS)
    assert rows[0]['category'] == 'mark_done'
    assert len(provisional) == 1


def test_utilization_measurement_is_not_review_decision():
    assert c.category('utilization observation (stage keeps running): LOW job-a') is None
    events = c.installed_events(['2026-11-18T10:00:00 task t: utilization observation (stage keeps running): LOW job-a', '2026-11-18T10:00:01 task t: triage agent start'], TASKS)
    assert [(e['stage'], e['category']) for e in events] == [('a', 'utilization_review')]


def test_agent_in_flight_at_snapshot_matches():
    early = event('fix_agent', time='2026-11-18T09:58:00')
    later = event('submit', time='2026-11-18T10:00:30')
    assert c.judge(row('fix_agent'), [early, later], '2026-11-18T10:01:00')['verdict'] == 'matched'
    # A finished earlier ladder step (submit) does not excuse a different first decision.
    assert c.judge(row('fix_agent'), [early, event('submit', time='2026-11-18T09:59:00'), later], '2026-11-18T10:01:00')['verdict'] == 'unexplained'

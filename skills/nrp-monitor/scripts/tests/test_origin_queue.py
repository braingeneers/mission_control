"""Origin replacement and queue ceilings, using scratch state and isolated wakes only."""
import copy
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import test_tasks
from test_agent_runners import load_module

Base = type('Base', (test_tasks.T,), {k: None for k in dir(test_tasks.T) if k.startswith('test_')})


class Origins(Base):
    def test_replace_and_show_history(self):
        old = {'title': 'Old chat', 'link': 't3-thread://v2/test-env/old-thread',
               'assistant': 'old assistant', 'harness': 't3', 'cwd': '/tmp/old', 'collaborator': 'Sam'}
        assert self.add(origin=old)[0] == 0
        for args, expected in [
            (['--chat', '<t3-thread://v2/test-env/new-thread>'], {'harness': 't3', 'link': 't3-thread://v2/test-env/new-thread'}),
            (['--chat', 'synthetic-session', '--harness', 'claude'], {'harness': 'claude', 'session': 'synthetic-session'}),
            (['--chat', 'synthetic-codex-session', '--harness', 'codex'], {'harness': 'codex', 'session': 'synthetic-codex-session'}),
        ]:
            before = self.task()['origin']
            rc, out, err = self.wd('task', 'origin', 't1', '--replace', '--evidence', 'fixture verified', '--by', 'test-editor', *args)
            assert rc == 0, err
            task = self.task()
            assert all(task['origin'][k] == v for k, v in expected.items())
            assert 'title' not in task['origin'] and 'assistant' not in task['origin']
            assert task['origin']['collaborator'] == 'Sam'
            assert task['origin_history'][-1]['recorded'] == before['recorded']
            assert task['origin_history'][-1]['replacement_evidence'] == 'fixture verified'
            assert 'by test-editor' in task['events'][-1]
        assert self.wd('task', 'show', 't1')[1].count('previous origin (') == 3
        assert 'synthetic-codex-session' in self.wd('task', 'origin', 't1')[1]
        assert self.wd('task', 'origin', 't1', '--chat', 'bare-session', '--replace', '--evidence', 'fixture')[0] != 0


@pytest.fixture
def queue(tmp_path, monkeypatch):
    w = load_module(tmp_path / 'state')
    clock = [10000]
    stage = {'id': 'a', 'job': 'fake-job', 'state': 'running', 'attempt': 1, 'submitted': 0, 'manifest': 'fake.yaml'}
    task = {'name': 'test-task', 'namespace': 'fake', 'status': 'running', 'stages': [stage], 'events': []}
    monkeypatch.setattr(w, 'now', lambda: clock[0])
    monkeypatch.setattr(w, 'task_load', lambda n: copy.deepcopy(task))
    monkeypatch.setattr(w, 'task_txn', lambda n, f: f(task) is not False)
    monkeypatch.setattr(w, 'digest', Mock())
    monkeypatch.setattr(w, 'manifest_gpu', lambda p: 1)
    pods = [{'status': {'phase': 'Pending', 'conditions': [{'type': 'PodScheduled', 'status': 'False', 'reason': 'Unschedulable'}]}}]
    monkeypatch.setattr(w, 'job_pods', lambda *a: pods)
    monkeypatch.setattr(w, 'pending_reason', lambda *a: 'Insufficient nvidia.com/gpu')
    def hold(n, reason):
        task.update(status='WITH_COORDINATOR', reason=reason)
    coordinator = Mock(side_effect=hold)
    monkeypatch.setattr(w, 'to_coordinator', coordinator)
    return w, task, stage, clock, pods, coordinator


def report(q):
    q[0].report_long_pending('test-task', {'fake-job': {'state': 'pending'}})


def test_gpu_ceiling_once_resume_double_and_auto_clear(queue):
    w, task, stage, clock, pods, coordinator = queue
    report(queue)
    clock[0] += 21600 - 1
    report(queue)
    assert not coordinator.called
    clock[0] += 1
    report(queue)
    report(queue)
    assert coordinator.call_count == 1
    assert task['status'] == 'WITH_COORDINATOR'
    assert 'CPU fallback' not in task['reason']
    assert 'cancel' in task['reason'] and 'resume test-task' in task['reason']
    task.update(attempts=[], failure=None)
    w.cmd_task_resume(SimpleNamespace(name='test-task', note='wait', skip=[], retries=None))
    assert stage['queue_wait']['multiplier'] == 2
    report(queue)
    assert coordinator.call_count == 1
    clock[0] += 21600
    report(queue)
    assert coordinator.call_count == 2
    pods[0]['spec'] = {'nodeName': 'fake-node'}
    report(queue)
    assert task['status'] == 'running'
    assert 'queue_wait' not in stage and 'queue_hold' not in task
    assert any('cleared automatically' in e for e in task['events'])


@pytest.mark.parametrize('explicit', [False, True])
def test_cpu_default_and_explicit_ceiling(queue, monkeypatch, explicit):
    w, task, stage, clock, pods, coordinator = queue
    monkeypatch.setattr(w, 'manifest_gpu', lambda p: 0)
    if explicit:
        stage.update(queue_wait_ceiling='1h', cpu_fallback={'requests': {'cpu': '2'}})
    report(queue)
    clock[0] += 86400
    report(queue)
    assert coordinator.call_count == int(explicit)
    if explicit:
        assert 'CPU fallback' in task['reason']


def test_pending_reports_bounded_and_reason_changes(queue, monkeypatch):
    w, task, stage, clock, pods, coordinator = queue
    report(queue)
    for _ in range(11):
        clock[0] += 300
        report(queue)
    assert len(task['events']) == 1
    clock[0] += 300
    report(queue)
    assert len(task['events']) == 2
    monkeypatch.setattr(w, 'pending_reason', lambda *a: 'different reason')
    report(queue)
    assert len(task['events']) == 3


def test_queue_attempt_reset_and_scheduled_reset(queue):
    w, task, stage, clock, pods, coordinator = queue
    report(queue)
    stage['attempt'] = 2
    clock[0] += 30000
    report(queue)
    assert stage['queue_wait']['since'] == clock[0]
    assert not coordinator.called
    pods[0]['spec'] = {'nodeName': 'fake-node'}
    report(queue)
    assert 'queue_wait' not in stage


@pytest.mark.parametrize('value', ['0h', '-1h', 'bad', None, True])
def test_invalid_queue_duration(tmp_path, value):
    with pytest.raises(ValueError):
        load_module(tmp_path / 'state').queue_ceiling_seconds(value)


def test_digest_shows_current_pending_once(queue, monkeypatch):
    w, task, stage, clock, pods, coordinator = queue
    report(queue)
    clock[0] += 3600
    report(queue)
    monkeypatch.setattr(w, 'task_names', lambda: ['test-task'])
    monkeypatch.setattr(w, 'plan_names', lambda: [])
    monkeypatch.setattr(w, 'bad_node_lines', lambda: [])
    monkeypatch.setattr(w, 'jwt_days_left', lambda: None)
    monkeypatch.setattr(w, 'lookup_origin', lambda n: (None, None))
    w.DIGEST.parent.mkdir(parents=True, exist_ok=True)
    w.DIGEST.write_text('\n'.join(json.dumps({'t': w.iso(), 'kind': 'pending', 'task': 'test-task', 'msg': 'old Pending wait'}) for _ in range(3)))
    out = w.render_digest(24)
    assert out.count('Pending') == 1
    assert 'old Pending wait' not in out


def test_queue_hold_stops_stage_advancement(queue, monkeypatch):
    w, task, stage, clock, pods, coordinator = queue
    task['status'] = 'WITH_COORDINATOR'
    monkeypatch.setattr(w, 'observe_task', Mock())
    monkeypatch.setattr(w, 'report_long_pending', Mock())
    util = Mock(side_effect=AssertionError('held task must not advance'))
    monkeypatch.setattr(w, 'process_util_event', util)
    w.advance_task('test-task', {}, SimpleNamespace(dry_run=False))
    assert not util.called


def test_adopted_gpu_without_manifest_uses_pod_request(queue, monkeypatch):
    w, task, stage, clock, pods, coordinator = queue
    stage['manifest'] = None
    monkeypatch.setattr(w, 'manifest_gpu', lambda p: 0)
    pods[0]['spec'] = {'containers': [{'resources': {'requests': {'nvidia.com/gpu': '1'}}}]}
    report(queue)
    clock[0] += 21600
    report(queue)
    assert coordinator.call_count == 1

"""Manifest edit rollback and task-pass exception escalation, with no live services."""
import argparse
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import test_agent_runners as runners
from test_escalation_costs import task


@pytest.fixture
def monitor(tmp_path, monkeypatch):
    if os.environ.get('MONITOR'):
        monkeypatch.setattr(runners, 'SOURCE', Path(os.environ['MONITOR']))
    m = runners.load_module(tmp_path / 'state')
    m.TASKS.mkdir(parents=True)
    return m


def valid_task(m):
    t = task(m)
    path = Path(t['stages'][0]['manifest'])
    doc = json.loads(path.read_text())
    doc.update(kind='Job', metadata={'name': 'work-17'})
    doc['spec']['template']['spec']['containers'][0]['resources'] = {
        'requests': {'cpu': '4'}, 'limits': {'cpu': '4'}}
    path.write_text(json.dumps(doc))
    return t, path


@pytest.mark.parametrize('kind', ['fix', 'deputy', 'continue'])
@pytest.mark.parametrize('result_status', ['ok', 'unavailable'])
def test_agent_invalid_manifest_restored_and_failure_recorded(monitor, kind, result_status):
    m = monitor
    t, path = valid_task(m)
    if kind == 'continue':
        t['on_done'] = {'plan': 'example'}
        m.task_write(t)
    before = path.read_bytes()

    def edit(*args, **kwargs):
        path.write_text('kind: Job\nspec:\n  limits:\n    memory: 4Gi\n  cpu: 1\n    ephemeral-storage: 1Gi\n')
        return 'claude', result_status, json.dumps({'result': 'DONE: resized'}), '', 0

    with patch.object(m, 'agents_available', return_value=True), \
         patch.object(m, 'dispatch_agent', side_effect=edit), patch.object(m, 'handoff_record'):
        line, _ = m.run_task_agent(t['name'], 'Resize manifest', argparse.Namespace(dry_run=False), kind=kind)
    assert path.read_bytes() == before
    cur = m.task_load(t['name'])
    assert cur['manifest_rejections'] and 'previous manifest restored' in cur['manifest_rejections'][-1]
    assert 'manifest edit rejected' in line
    assert cur['agent_runs'][-1]['result'].startswith('ESCALATE:')
    assert cur['status'] == 'WITH_COORDINATOR'


def test_submit_rejects_agent_edit_before_applying(monitor):
    m = monitor
    t, path = valid_task(m)
    before = path.read_bytes()
    m.agent_manifest_checkpoint(t['name'])
    path.write_text('kind: Job\nspec: [broken\n')
    with patch.object(m, 'apply_manifest') as apply:
        ok, why = m.do_submit(t['name'], 'a', 'resize', 'fixer')
    assert not ok and 'manifest edit rejected' in why
    assert path.read_bytes() == before
    apply.assert_not_called()


@pytest.mark.parametrize('bad', [None, 'cpu', ['cpu']])
def test_resources_mapping_required(monitor, bad):
    m = monitor
    t, path = valid_task(m)
    doc = json.loads(path.read_text())
    doc['spec']['template']['spec']['containers'][0]['resources']['requests'] = bad
    path.write_text(json.dumps(doc))
    assert any('requests must be a mapping' in x for x in m.manifest_check(path, 'test', 'work-17'))


def test_unparsable_task_manifest_escalates_once_with_location(monitor):
    m = monitor
    t, path = valid_task(m)
    path.write_text('kind: Job\nspec: [broken\n')
    original = path.read_bytes()
    with patch.object(m, 'fetch_jobs', return_value={}), patch.object(m, 'advance_task') as advance:
        for _ in range(5):
            m.process_tasks(argparse.Namespace(dry_run=False), {})
    cur = m.task_load(t['name'])
    assert cur['status'] == 'WITH_COORDINATOR'
    assert cur['coordinator_wakes'] == 1
    assert str(path) + ':3:1' in cur['reason']
    assert path.read_bytes() == original
    advance.assert_not_called()


def test_repeated_task_exceptions_escalate_at_limit_and_stop(monitor):
    m = monitor
    t, _ = valid_task(m)
    with patch.object(m, 'fetch_jobs', return_value={}), \
         patch.object(m, 'advance_task', side_effect=RuntimeError('same failure')) as advance:
        for i in range(6):
            m.process_tasks(argparse.Namespace(dry_run=False), {})
            if i < 2:
                assert m.task_load(t['name'])['status'] == 'running'
    cur = m.task_load(t['name'])
    assert m.TASK_EXCEPTION_LIMIT == 3
    assert advance.call_count == 3
    assert cur['coordinator_wakes'] == 1
    assert cur['task_exception']['count'] == 3


def test_successful_task_pass_resets_exception_streak(monitor):
    m = monitor
    t, _ = valid_task(m)
    with patch.object(m, 'fetch_jobs', return_value={}), \
         patch.object(m, 'advance_task', side_effect=[RuntimeError('one'), None, RuntimeError('one')]):
        for _ in range(3):
            m.process_tasks(argparse.Namespace(dry_run=False), {})
    assert m.task_load(t['name'])['task_exception']['count'] == 1


def test_structural_writer_preserves_previous_manifest_on_invalid_resources(monitor):
    m = monitor
    _, path = valid_task(m)
    before = path.read_bytes()
    doc = json.loads(path.read_text())
    doc['spec']['template']['spec']['containers'][0]['resources'] = 'cpu: 1'
    with pytest.raises(ValueError, match='resources must be a mapping'):
        m.manifest_write(path, doc)
    assert path.read_bytes() == before


def test_repeated_task_exception_owner_fallback_once(monitor):
    m = monitor
    t, _ = valid_task(m)
    t['origin'] = None
    m.task_write(t)
    with patch.object(m, 'fetch_jobs', return_value={}), \
         patch.object(m, 'advance_task', side_effect=RuntimeError('same failure')) as advance, \
         patch.object(m, 'push') as push:
        for _ in range(6):
            m.process_tasks(argparse.Namespace(dry_run=False), {})
    assert advance.call_count == 3
    assert push.call_count == 1
    assert m.task_load(t['name'])['status'] == 'NEEDS_OWNER'


def test_different_exception_resets_streak(monitor):
    m = monitor
    t, _ = valid_task(m)
    with patch.object(m, 'fetch_jobs', return_value={}), \
         patch.object(m, 'advance_task', side_effect=[RuntimeError('one'), RuntimeError('one'), ValueError('two')]):
        for _ in range(3):
            m.process_tasks(argparse.Namespace(dry_run=False), {})
    assert m.task_load(t['name'])['task_exception']['count'] == 1
    assert m.task_load(t['name'])['status'] == 'running'

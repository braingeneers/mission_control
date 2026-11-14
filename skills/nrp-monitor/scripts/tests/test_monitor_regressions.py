"""Offline regressions for decision loops and replacement artifacts after resume."""
import argparse
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import test_agent_runners as runners
from test_escalation_costs import task
import test_tasks as TT
import json


@pytest.fixture
def monitor(tmp_path, monkeypatch):
    if os.environ.get('MONITOR'):
        monkeypatch.setattr(runners, 'SOURCE', Path(os.environ['MONITOR']))
    m = runners.load_module(tmp_path / 'state')
    m.STATE.mkdir(parents=True)
    m.TASKS.mkdir(parents=True, exist_ok=True)
    m.TPL = Path(__file__).resolve().parents[1] / 'templates'
    return m


class TestPostcheckPasses:
    @pytest.mark.parametrize('coordinator', [False, True])
    def test_postcheck_stored_skip_reuse_escalates(self, coordinator):
        h = TT.T('test_add_warns_on_existing_output')
        h.setUp()
        try:
            checker = h.tmp / 'check.py'
            checker.write_text('raise SystemExit("broken acceptance script")\n')
            rc, out, err = h.add(postcheck={'cmd': ['python3', str(checker)], 'expect': 'PASS'})
            assert rc == 0, err
            path = h.state / 'tasks/t1/task.json'
            t = h.task()
            t['stages'][0]['state'] = 'done'
            t['failure'] = None
            if coordinator:
                # The isolated T3 target queues a wake; no real session is contacted.
                t['origin'] = {'harness': 'codex', 'session': 'fake-coordinator'}
            path.write_text(json.dumps(t))
            m = runners.load_module(h.state)
            f = dict(stage='a', job='t1-a', cls='outputs', sig='postcheck',
                     detail='postcheck failed: broken acceptance script')
            fp = m.fingerprint(t, f)
            decisions = h.state / 'tasks/t1/decisions.json'
            decisions.write_text(json.dumps([dict(fingerprint=fp, action='skip_reuse', scope='task',
                                                   stage='a', max_uses=None, uses=0, why='Reuse markers', ts=1)]))
            (h.fake / 's3.json').write_text(json.dumps(t['stages'][0]['done_s3']))
            for _ in range(5):
                h.run_pass()
            t = h.task()
            assert t['status'] in ('WITH_COORDINATOR', 'NEEDS_OWNER')
            assert t['stages'][0]['state'] == 'failed'
            assert json.loads(decisions.read_text())[0]['uses'] == 0
            assert 'postcheck' in t['reason']
            assert t.get('coordinator_wakes', 0) or h.pushes()
            assert h.prompts() == []
        finally:
            h.tearDown()


def test_postcheck_skip_reuse_record_refused(monitor, monkeypatch):
    m = monitor
    t = task(m)
    t['failure'].update(sig='postcheck', cls='outputs')
    m.task_write(t)
    monkeypatch.setenv('NRP_TASK', t['name'])
    monkeypatch.setenv('NRP_MONITOR_AGENT_ROLE', 'deputy')
    with pytest.raises(ValueError, match='postcheck'):
        m.cmd_tool(argparse.Namespace(rest=['decide', t['failure']['fingerprint'], '--action', 'skip_reuse', '--why', 'reuse']))
    assert m.decisions(t['name']) == []


def test_postcheck_stored_decision_direct_apply_refused(monitor):
    m = monitor
    t = task(m)
    m.record_decision(t, t['failure']['fingerprint'], 'skip_reuse', 'reuse')
    m.task_txn(t['name'], lambda cur: cur['failure'].update(sig='postcheck'))
    with patch.object(m, 's3_exists', return_value=True), patch.object(m, 'run_task_agent', side_effect=AssertionError('no deputy')):
        m.apply_decision(t['name'], argparse.Namespace(dry_run=False))
    assert m.task_load(t['name'])['status'] == 'WITH_COORDINATOR'
    assert m.decisions(t['name'])[0]['uses'] == 0


def test_resubmit_no_progress_limit(monitor):
    m = monitor
    t = task(m)
    m.record_decision(t, t['failure']['fingerprint'], 'resubmit', 'Known failure')
    with patch.object(m, 'do_submit', return_value=(True, 'submitted')) as submit, \
         patch.object(m, 'run_task_agent', side_effect=AssertionError('no deputy')):
        for _ in range(5):
            m.apply_decision(t['name'], argparse.Namespace(dry_run=False))
        assert submit.call_count == 3
    assert m.DECISION_NO_PROGRESS_LIMIT == 3
    assert m.task_load(t['name'])['status'] == 'WITH_COORDINATOR'
    assert 'without progress' in m.task_load(t['name'])['reason']


def test_new_stage_completion_resets_decision_streak(monitor):
    m = monitor
    t = task(m)
    t['stages'].append(dict(t['stages'][0], id='b', state='running'))
    m.task_write(t)
    m.record_decision(t, t['failure']['fingerprint'], 'resubmit', 'Known failure')
    with patch.object(m, 'do_submit', return_value=(True, 'submitted')) as submit:
        for _ in range(3):
            m.apply_decision(t['name'], argparse.Namespace(dry_run=False))
        m.task_txn(t['name'], lambda cur: cur['stages'][1].update(state='done'))
        for _ in range(3):
            m.apply_decision(t['name'], argparse.Namespace(dry_run=False))
        assert submit.call_count == 6
        m.apply_decision(t['name'], argparse.Namespace(dry_run=False))
    assert m.task_load(t['name'])['status'] == 'WITH_COORDINATOR'


def test_resume_note_in_followup_prompt(monitor):
    m = monitor
    t = task(m)
    t.update(status='NEEDS_OWNER', followup='Verify s3://old-run/results', code=None)
    m.task_write(t)
    note = 'Replacement s3://new-run/results: 47 passed; old run is obsolete.'
    m.cmd_task_resume(argparse.Namespace(name=t['name'], skip=['a'], note=note, retries=None))
    with patch.object(m, 'observe_task'), patch.object(m, 'report_long_pending'), \
         patch.object(m, 'process_util_event'), patch.object(m, 'run_postcheck', return_value={'ok': True}), \
         patch.object(m, 'digest'), patch.object(m, 'run_task_agent', return_value=('DONE: verified', [])) as agent:
        m.advance_task(t['name'], {}, argparse.Namespace(dry_run=False))
    prompt = agent.call_args.args[1]
    assert note in prompt
    assert "supersede the original brief's artifact locations" in prompt


def test_legacy_resume_note_in_continuation_prompt(monitor):
    from test_plan_groups import header
    m = monitor
    t = task(m)
    t['on_done'] = dict(plan='sample', from_step='1')
    note = 'resumed by a person: use s3://replacement/results, 47 passed'
    t['attempts'] = [dict(by='person', fix=note, ts=1)]
    prompt = m.continue_prompt(t, header(m), ['2'], [])
    assert note in prompt
    assert "supersede the original brief's artifact locations" in prompt

"""Offline first-submission output reuse and retry isolation."""
import json
from unittest.mock import patch
from types import SimpleNamespace

import pytest
from test_agent_runners import load_module
import test_tasks as TT


def test_existing_outputs_complete_task_and_release_dependents():
    h = TT.T('test_add_warns_on_existing_output')
    h.setUp()
    try:
        uris = ['s3://braingeneersdev/test/a', 's3://braingeneersdev/test/b']
        stages = [dict(id=sid, job='t1-'+sid, manifest=h.manifest('t1-'+sid),
                       done_s3=[uri], after=[] if sid == 'a' else ['a'])
                  for sid, uri in zip(('a', 'b'), uris)]
        (h.fake/'s3.json').write_text(json.dumps(uris))
        assert h.add(stages=stages, digest_only='no remaining work after completion')[0] == 0
        h.run_pass()
        t = h.task()
        assert t['status'] == 'done'
        assert all(s['state'] == 'done' and 'submitted' not in s for s in t['stages'])
        assert not h.cl()
        assert 'reused, not rerun' in json.dumps(t['events'])
    finally:
        h.tearDown()


@pytest.mark.parametrize('answers,extra,gate,expected', [
    ([True, True], {}, [], 'done'),
    ([True, False], {}, [], 'pending'),
    ([True, None], {}, [], 'pending'),
    ([True, True], {'attempt': 2}, [], 'pending'),
    ([True, True], {'submitted': 1}, [], 'pending'),
    ([True, True], {}, ['s3://bucket/gate'], 'pending'),
])
def test_reuse_requires_all_markers_first_attempt_and_open_gates(tmp_path, answers, extra, gate, expected):
    m = load_module(tmp_path/'state')
    s = dict(id='a', job='work', state='pending', after=[], done_s3=['s3://bucket/a', 's3://bucket/b'], **extra)
    t = dict(name='t', status='running', stages=[s], attempts=[], events=[], created=m.now(), label='test')
    def txn(n, f):
        f(t)
        return True
    with patch.object(m, 'task_load', return_value=t), patch.object(m, 'task_txn', side_effect=txn), \
         patch.object(m, 'observe_task'), patch.object(m, 'report_long_pending'), patch.object(m, 'process_util_event'), \
         patch.object(m, 's3_gate', return_value=gate), patch.object(m, 'note_waiting'), \
         patch.object(m, 's3_exists', side_effect=answers) as exists, \
         patch.object(m, 'do_submit', return_value=(True, 'ok')) as submit, \
         patch.object(m, 'digest'):
        # Held gate setup must enter the after_s3 branch.
        if gate:
            s['after_s3'] = gate
        # Avoid the completion-delivery branch here; the integration test covers it.
        t['stages'].append(dict(id='later', job='later', state='pending', after=['never']))
        original = m.tstage
        with patch.object(m, 'tstage', side_effect=lambda task, sid: {'state':'pending'} if sid=='never' else original(task, sid)):
            m.advance_task('t', {}, SimpleNamespace(dry_run=False))
        assert s['state'] == expected
        assert submit.call_count == (0 if expected == 'done' or gate else 1)
        if extra or gate:
            exists.assert_not_called()

"""A submit NRP refuses for utilization: one namespace-wide check, one wake, no retry loop. Fake kubectl / nrp-util-check, scratch state."""
import argparse
import json
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from test_escalation_costs import monitor, task

USER = 'http://cilogon.org/serverE/users/1'
REFUSAL = 'admission webhook "job.nrp-nautilus.io" denied the request: Your pods resources utilization is too low'
LOW_CPU = 'LOW {} age 20m, 10m mean: cpu 0.10/2.00 (5%) [NRP violation] rule=nrp'
LOW_GPU = 'LOW {} age 20m, 10m mean: gpu 3% (gpu 0, A100) [NRP violation] rule=gpu'
LAB_ONLY = 'LOW {} age 20m, 10m mean: cpu 0.30/1.00 (30%) [lab 40% rule] rule=lab'


def pod(name, user=None, job=None, sa='default', phase='Running', owner_kind='Job', gpu=0):
    meta = {'name': name, 'annotations': {'nrp.ai/username': user} if user else {}}
    if job:
        meta['ownerReferences'] = [{'kind': owner_kind, 'name': job}]
    res = {'requests': {'nvidia.com/gpu': str(gpu)}} if gpu else {}
    return {'metadata': meta, 'spec': {'serviceAccountName': sa, 'containers': [{'resources': res}]}, 'status': {'phase': phase}}


class Cluster:
    """Fake kubectl + nrp-util-check; records every call."""
    def __init__(self):
        self.pods, self.flags, self.calls, self.util_calls = [], {}, [], []
        self.fail_pods = self.fail_util = False

    def kubectl(self, *args, **kw):
        self.calls.append(args)
        assert args[2:4] == ('get', 'pods'), args
        if self.fail_pods:
            return SimpleNamespace(returncode=1, stdout='', stderr='metrics unavailable')
        return SimpleNamespace(returncode=0, stdout=json.dumps({'items': self.pods}), stderr='')

    def run(self, cmd, **kw):
        assert cmd[0] == 'nrp-util-check', cmd
        self.util_calls.append(cmd)
        if self.fail_util:
            return SimpleNamespace(returncode=2, stdout='ERROR thanos down', stderr='')
        lines = [fmt.format(n) for n, fmt in self.flags.items() if n in cmd]
        return SimpleNamespace(returncode=4 if lines else 0, stdout='\n'.join(lines + ['checked %d pods' % len(cmd)]), stderr='')


class Blocked:
    """A task with one pending stage whose submit NRP refuses, a clock, and a switch for the refusal."""
    def __init__(self, m):
        self.m, self.cl, self.blocked, self.applies, self.clock = m, Cluster(), True, 0, [1000.0]
        m.USER_ANN = USER
        t = task(m)
        m.task_txn(t['name'], lambda v: v['stages'][0].update(state='pending', after=[]) or v.update(failure=None, status='running'))
        self.name = t['name']
        self.stack = [patch.object(m, 'kubectl', self.cl.kubectl), patch.object(m.subprocess, 'run', self.cl.run),
                      patch.object(m, 'apply_manifest', self.apply), patch.object(m, 'job_state', return_value='missing'),
                      patch.object(m, 'manifest_check', return_value=[]), patch.object(m, 'gpu_expired', return_value=None),
                      patch.object(m, 'bad_nodes', return_value={}), patch.object(m, 'now', lambda: self.clock[0]),
                      patch.object(m, 'observe_task'), patch.object(m, 'report_long_pending'), patch.object(m, 'process_util_event'),
                      patch.object(m, 'push')]
        self.pushes = self.stack[-1]

    def apply(self, ns, path):
        self.applies += 1
        if self.blocked:
            self.m.LAST_BLOCK['msg'] = REFUSAL
            return 'blocked'
        return 'ok'

    def __enter__(self):
        self.mocks = [p.start() for p in self.stack]
        return self

    def __exit__(self, *exc):
        for p in reversed(self.stack):
            p.stop()

    def submit(self):
        return self.m.do_submit(self.name, 'a', 'stage ready', 'monitor')

    def pass_(self, dry=False, minutes=5):
        self.clock[0] += minutes * 60
        self.m.advance_task(self.name, {}, argparse.Namespace(dry_run=dry))

    @property
    def t(self):
        return self.m.task_load(self.name)

    @property
    def wakes(self):
        return [e for e in self.t.get('webhook_outbox') or [] if e['event_type'] == 'escalation']

    @property
    def push_mock(self):
        return self.mocks[-1]


def standard_pods(cl):
    cl.pods = [pod('t1-a-abc', USER, 't1-a'), pod('workflows-run-1', None, 'wf', sa='braingeneers-ingest', owner_kind='Workflow'),
               pod('other-user-xyz', 'http://cilogon.org/serverE/users/9', 'theirs'), pod('healthy-1', USER, 'ok'),
               pod('pending-1', USER, 'q', phase='Pending'), pod('gpu-hog', None, 'g', sa='gpu-sa', gpu=2)]
    cl.flags = {'t1-a-abc': LOW_CPU, 'workflows-run-1': LOW_CPU, 'other-user-xyz': LOW_CPU, 'pending-1': LOW_CPU,
                'gpu-hog': LOW_GPU}


def test_first_block_checks_once_and_wakes_once_with_offenders(monitor):
    with Blocked(monitor) as b:
        standard_pods(b.cl)
        ok, msg = b.submit()
        assert ok and msg.startswith('BLOCKED')
        t = b.t
        assert t['status'] == 'blocked'
        assert len(b.cl.util_calls) == 1 and len(b.wakes) == 1
        # every Running pod regardless of annotation is checked; the Pending pod is not
        assert set(b.cl.util_calls[0][5:]) == {'t1-a-abc', 'workflows-run-1', 'other-user-xyz', 'healthy-1', 'gpu-hog'}
        assert [o['pod'] for o in t['pending']['offenders']] == ['gpu-hog', 'other-user-xyz', 't1-a-abc', 'workflows-run-1']
        summary = b.wakes[0]['summary']
        for name in ('t1-a-abc', 'workflows-run-1', 'other-user-xyz', 'gpu-hog'):
            assert name in summary
        assert 'utilization is too low' in summary and 'ask the owner before touching anyone else' in summary
        assert 'workflows-run-1' in (monitor.STATE / 'digest.log').read_text()
        assert '"kind": "block"' in (monitor.STATE / 'digest.log').read_text()
        b.push_mock.assert_not_called()                       # the owner is not DMed; the coordinator chat is woken


def test_ours_and_others_are_labelled(monitor):
    with Blocked(monitor) as b:
        standard_pods(b.cl)
        b.submit()
        by = {o['pod']: o for o in b.t['pending']['offenders']}
        assert by['t1-a-abc']['ours'] and by['t1-a-abc']['owner'] == 'Job/t1-a'
        assert not by['other-user-xyz']['ours'] and by['other-user-xyz']['username'].endswith('/9')
        wf = by['workflows-run-1']
        assert not wf['ours'] and wf['username'] == '' and wf['service_account'] == 'braingeneers-ingest' and wf['owner'] == 'Workflow/wf'
        assert wf['usage']['cpu'] == {'use': 0.1, 'request': 2.0, 'pct': 5}
        assert by['gpu-hog']['usage']['gpu'] == {'pct': 3, 'request': 2}
        summary = b.wakes[0]['summary']
        ours, others = summary.split('OURS (annotation matches): ')[1].split(" | OTHERS' (not launched by us): ")
        assert 't1-a-abc' in ours and 'workflows-run-1' not in ours and 'other-user-xyz' not in ours
        assert 'workflows-run-1' in others and 'other-user-xyz' in others and 't1-a-abc' not in others
        assert 'service account braingeneers-ingest' in others


def test_lab_floor_only_flags_are_not_offenders(monitor):
    with Blocked(monitor) as b:
        b.cl.pods = [pod('t1-a-abc', USER, 't1-a')]
        b.cl.flags = {'t1-a-abc': LAB_ONLY}
        b.submit()
        assert b.t['pending']['offenders'] == []


def test_unchanged_offenders_do_not_reapply_or_wake_again(monitor):
    with Blocked(monitor) as b:
        standard_pods(b.cl)
        b.submit()
        applies, checks = b.applies, len(b.cl.util_calls)
        for _ in range(3):                                    # 3-minute passes: inside the 10-minute re-check window
            b.pass_(minutes=3)
        assert (b.applies, len(b.cl.util_calls), len(b.wakes)) == (applies, checks, 1)
        b.pass_(minutes=6)                                    # 15 minutes since the check: re-checks, set unchanged
        assert len(b.cl.util_calls) == checks + 1
        assert b.applies == applies and len(b.wakes) == 1 and b.t['status'] == 'blocked'
        assert b.t['pending']['rechecked'] > b.t['pending']['checked']
        b.pass_(minutes=11)
        assert b.applies == applies and len(b.wakes) == 1


def test_changed_offender_set_reapplies_without_a_second_wake(monitor):
    with Blocked(monitor) as b:
        standard_pods(b.cl)
        b.submit()
        applies = b.applies
        del b.cl.flags['t1-a-abc']                            # we fixed our own pod; the others remain
        b.pass_(minutes=11)
        assert b.applies == applies + 1 and len(b.wakes) == 1
        assert 't1-a-abc' not in [o['pod'] for o in b.t['pending']['offenders']]
        assert b.t['status'] == 'blocked'
        b.pass_(minutes=1)                                    # same new set, inside the window: waits again
        assert b.applies == applies + 1


def test_no_offenders_left_reapplies_and_the_task_goes_on(monitor):
    with Blocked(monitor) as b:
        standard_pods(b.cl)
        b.submit()
        applies = b.applies
        b.cl.flags.clear()
        b.blocked = False
        b.pass_(minutes=11)
        assert b.applies == applies + 1
        t = b.t
        assert t['status'] == 'running' and 'pending' not in t and t['stages'][0]['state'] == 'running'
        assert len(b.wakes) == 1


def test_a_new_block_after_recovery_is_a_new_episode(monitor):
    with Blocked(monitor) as b:
        standard_pods(b.cl)
        b.submit()
        b.blocked = False
        b.cl.flags.clear()
        b.pass_(minutes=11)
        b.m.task_txn(b.name, lambda t: t['stages'][0].update(state='pending'))
        b.blocked = True
        b.submit()
        assert len(b.wakes) == 2 and len(b.cl.util_calls) == 3     # check, re-check that found none, new episode's check


def test_block_without_offenders_keeps_old_behaviour_and_wakes_once(monitor):
    with Blocked(monitor) as b:
        b.cl.pods = [pod('healthy-1', USER, 'ok')]
        b.submit()
        assert b.t['pending']['offenders'] == [] and len(b.wakes) == 1
        assert 'no Running pod outside the bands' in b.wakes[0]['summary']
        applies = b.applies
        b.pass_()
        b.pass_()
        assert b.applies == applies + 2 and len(b.wakes) == 1          # unexplained: re-applied each pass
        b.pass_(minutes=361)                                            # the 6 h fallback still escalates
        assert b.t['status'] == 'NEEDS_OWNER' and 'submits refused' in b.t['reason']


@pytest.mark.parametrize('how', ['kubectl', 'util'])
def test_failed_check_still_wakes_once_with_the_raw_refusal(monitor, how):
    with Blocked(monitor) as b:
        standard_pods(b.cl)
        setattr(b.cl, 'fail_pods' if how == 'kubectl' else 'fail_util', True)
        ok, _ = b.submit()
        assert ok
        t = b.t
        assert t['status'] == 'blocked' and t['pending']['offenders'] == [] and t['pending']['check_error']
        assert len(b.wakes) == 1
        assert 'utilization is too low' in b.wakes[0]['summary'] and 'check FAILED' in b.wakes[0]['summary']
        b.pass_()
        b.pass_()
        assert len(b.wakes) == 1 and len(b.cl.util_calls) <= 1


def test_no_wake_target_leaves_a_digest_line_and_the_six_hour_fallback(monitor):
    with Blocked(monitor) as b:
        standard_pods(b.cl)
        monitor.task_txn(b.name, lambda t: t.update(origin={}))
        b.submit()
        assert b.t['status'] == 'blocked' and not b.wakes
        assert 'workflows-run-1' in (monitor.STATE / 'digest.log').read_text()
        b.push_mock.assert_not_called()
        b.pass_(minutes=361)
        assert b.t['status'] == 'NEEDS_OWNER' and 'workflows-run-1' in b.t['reason']


def test_dry_run_changes_nothing_and_wakes_nobody(monitor, capsys):
    with Blocked(monitor) as b:
        standard_pods(b.cl)
        b.submit()
        before = json.dumps(b.t, sort_keys=True)
        calls, applies = len(b.cl.calls), b.applies
        b.pass_(dry=True, minutes=30)
        assert json.dumps(b.t, sort_keys=True) == before
        assert (len(b.cl.calls), b.applies) == (calls, applies)
        assert 'would re-check the namespace' in capsys.readouterr().out
    with Blocked(monitor) as c:                                       # a never-checked block: dry-run does not run the check either
        monitor.task_txn(c.name, lambda t: t.update(status='blocked', pending={'stage': 'a', 'reason': 'r', 'by': 'monitor', 'since': 1}))
        before = json.dumps(c.t, sort_keys=True)
        c.pass_(dry=True)
        assert json.dumps(c.t, sort_keys=True) == before and not c.cl.calls and not c.wakes

"""Patch P: offline resource actions, with fake cluster and Thanos responses."""
import argparse
import json
import importlib
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from test_escalation_costs import monitor, task


def running(m, resumable=False):
    task(m)
    m.task_txn('sample', lambda t: (t.update(failure=None), t['stages'][0].update(state='running', submitted=1, pod_started=1, resumable=resumable)))
    t = m.task_load('sample')
    doc = m.manifest_doc(t['stages'][0]['manifest'])
    doc['spec']['template']['spec']['containers'][0]['name'] = 'worker'
    m.manifest_write(t['stages'][0]['manifest'], doc)
    return t


def result(items):
    return SimpleNamespace(returncode=0, stdout=json.dumps({'items': items}), stderr='')


@pytest.mark.parametrize('cpu,mem', [('2', '4Gi'), (None, None)])
def test_restart_without_failure_budget_or_wake(monitor, cpu, mem):
    m = monitor
    running(m)
    m.task_txn('sample', lambda t: t.update(webhook_outbox=[{'event_type': 'failure'}]))
    with patch.object(m, 'save_task_logs') as logs, patch.object(m, 'kubectl', return_value=result([])) as kc, patch.object(m, 'push') as push:
        assert m.utilization_restart('sample', 'a', cpu, mem)[0]
    t = m.task_load('sample')
    assert t['failure'] is None and t['attempts'] == [] and t['webhook_outbox'] == []
    assert t['stages'][0]['state'] == 'pending' and t['status'] == 'running'
    logs.assert_called_once()
    assert 'work-17' in kc.call_args.args
    push.assert_not_called()
    if cpu:
        res = m.manifest_doc(t['stages'][0]['manifest'])['spec']['template']['spec']['containers'][0]['resources']
        assert res['requests'] == res['limits'] == {'cpu': cpu, 'memory': mem}


def test_restart_terminal_refused(monitor):
    running(monitor)
    monitor.task_txn('sample', lambda t: t.update(status='done'))
    with patch.object(monitor, 'kubectl') as kc:
        assert not monitor.utilization_restart('sample')[0]
        kc.assert_not_called()


@pytest.mark.parametrize('unsched,labels,zero', [(False, {'gpu': 'A10'}, False), (True, {'gpu': 'A10'}, True), (False, {'gpu': '3090'}, True)])
def test_node_selector_cache(monitor, unsched, labels, zero):
    doc = {'spec': {'template': {'spec': {'nodeSelector': {'gpu': 'A10'}}}}}
    node = {'metadata': {'name': 'node', 'labels': labels}, 'spec': {'unschedulable': unsched}}
    with patch.object(monitor, 'kubectl', return_value=result([node])) as kc:
        assert bool(monitor.zero_node_reason(doc)) == zero
        monitor.zero_node_reason(doc)
        kc.assert_called_once()


def test_affinity_or_and_read_failure(monitor):
    spec = {'affinity': {'nodeAffinity': {'requiredDuringSchedulingIgnoredDuringExecution': {'nodeSelectorTerms': [
        {'matchExpressions': [{'key': 'gpu', 'operator': 'In', 'values': ['A10']}, {'key': 'region', 'operator': 'In', 'values': ['west']}]}]}}}}
    doc = {'spec': {'template': {'spec': spec}}}
    with patch.object(monitor, 'kubectl', return_value=result([{'metadata': {'name': 'n', 'labels': {'gpu': 'A10', 'region': 'east'}}}])):
        assert 'zero' in monitor.zero_node_reason(doc)
    monitor.PASS.clear()
    with patch.object(monitor, 'kubectl', side_effect=RuntimeError):
        assert monitor.zero_node_reason(doc) is None


@pytest.mark.parametrize('resumable,elapsed,count,stop', [(True, 0, 0, False), (False, 0, 0, False), (False, 1801, 0, True), (True, 0, 3, True)])
def test_violation_actions(monitor, resumable, elapsed, count, stop):
    m = monitor
    running(m, resumable)
    m.task_txn('sample', lambda t: t['stages'][0].update(nrp_flag_since=10000-elapsed))
    evidence = {'right_gi': 10, 'need_gi': 6.1}
    line = 'LOW work-17-abc cpu 0.1/8 (1%) mem 1/32Gi (3%) rule=nrp'
    with patch.object(m, 'job_pods', return_value=[]), patch.object(m, 'now', return_value=10000), patch.object(m, 'namespace_offenders', return_value=[{'ours': True}]*count), patch.object(m, 'memory_low_evidence', return_value=evidence), patch.object(m, 'thanos_query', return_value=[{'value': [0, '2']}]), patch.object(m, 'save_task_logs'), patch.object(m, 'kubectl', return_value=result([])) as kc, patch.object(m, 'utilization_restart', return_value=(True, 'ok')) as restart, patch.object(m, 'push') as push:
        m.utilization_band_action('sample', 'a', 'work-17-abc', line)
        m.utilization_band_action('sample', 'a', 'work-17-abc', line)
        if stop:
            assert kc.called and push.call_count == 1
            assert m.task_load('sample')['status'] == 'WITH_COORDINATOR'
        elif resumable:
            assert restart.called and restart.call_args.args[2:] == ('3.0', str(10*2**30))
            push.assert_not_called()
        else:
            wakes = m.task_load('sample')['webhook_outbox']
            assert len(wakes) == 1 and 'spiky' in wakes[0]['summary'] and 'deadline' in wakes[0]['summary']
            assert 'No change' in wakes[0]['summary']
            push.assert_not_called()


def test_spiky_check_reads_the_lower_rss(monitor):
    m = monitor
    running(m, False)
    m.task_txn('sample', lambda t: t['stages'][0].update(nrp_flag_since=10000))
    evidence = {'right_gi': 10, 'need_gi': 6.1}

    def summary(line):
        m.task_txn('sample', lambda t: t.update(webhook_outbox=[]))
        with patch.object(m, 'job_pods', return_value=[]), patch.object(m, 'now', return_value=10000), patch.object(m, 'namespace_offenders', return_value=[]), patch.object(m, 'memory_low_evidence', return_value=evidence), patch.object(m, 'thanos_query', return_value=[{'value': [0, '2']}]), patch.object(m, 'save_task_logs'), patch.object(m, 'kubectl', return_value=result([])), patch.object(m, 'push'):
            m.utilization_band_action('sample', 'a', 'work-17-abc', line)
        return m.task_load('sample')['webhook_outbox'][-1]['summary']
    # working set 4Gi fits a 10Gi request's 20 % floor; RSS 1.5Gi does not
    assert 'spiky' in summary('LOW work-17-abc cpu 2/2 (100%), mem 4.0/32.0Gi (12%, max 6.1, rss 1.5Gi 5%) rule=nrp')


def test_working_set_precedes_cgroup_and_oom_minimum(monitor):
    m = monitor
    t = running(m)
    s = t['stages'][0]
    m.task_txn('sample', lambda t: t['stages'][0].update(oom_limits_gi=[8]))
    s = m.task_load('sample')['stages'][0]
    doc = m.manifest_doc(s['manifest'])
    doc['spec']['template']['spec']['containers'][0]['name'] = 'worker'
    m.manifest_write(s['manifest'], doc)
    with patch.object(m, 'job_pods', return_value=[]), patch.object(m, 'thanos_peak_mem', return_value={'pod': 6*2**30}), patch.object(m, 'saved_memory_peak', return_value=20*2**30):
        assert m.memory_low_evidence(t, s, 'pod')['need_gi'] == 8
    with patch.object(m, 'job_pods', return_value=[]), patch.object(m, 'thanos_peak_mem', return_value={}), patch.object(m, 'saved_memory_peak', return_value=20*2**30):
        s.pop('memory_peaks_gi', None)
        assert m.memory_low_evidence(t, s, 'pod')['need_gi'] == 20


def test_watch_failure_coordinator_first(monitor):
    task(monitor)
    monitor.task_txn('sample', lambda t: t.update(mode='watch'))
    with patch.object(monitor, 'apply_decision', return_value=False), patch.object(monitor, 'push') as push:
        monitor.handle_failure('sample', argparse.Namespace(dry_run=False))
        assert monitor.task_load('sample')['status'] == 'WITH_COORDINATOR'
        push.assert_not_called()


def test_zero_nodes_routes_without_apply_or_retry(monitor):
    m = monitor
    running(m)
    m.task_txn('sample', lambda t: t['stages'][0].update(state='pending'))
    with patch.object(m, 'manifest_check', return_value=[]), patch.object(m, 'gpu_expired', return_value=None), patch.object(m, 'red_alert', return_value=False), patch.object(m, 'zero_node_reason', return_value='zero GPU nodes'), patch.object(m, 'apply_manifest') as apply:
        assert not m.do_submit('sample', 'a', 'initial', 'monitor')[0]
        t = m.task_load('sample')
        assert t['failure']['cls'] == 'unschedulable' and t['status'] == 'WITH_COORDINATOR'
        assert t['attempts'] == []
        apply.assert_not_called()


def test_delete_failure_preserves_running_state(monitor):
    running(monitor)
    with patch.object(monitor, 'save_task_logs'), patch.object(monitor, 'kubectl', return_value=SimpleNamespace(returncode=1, stderr='denied')):
        assert not monitor.utilization_restart('sample', 'a', '2', '4Gi')[0]
        assert monitor.task_load('sample')['stages'][0]['state'] == 'running'


@pytest.mark.parametrize('runtime,age,acted', [
    (None, 300, False), (None, 600, True),
    (1200, 299, False), (1200, 300, True),
    (7200, 899, False), (7200, 900, True)])
@pytest.mark.parametrize('kind', ['LOW', 'HIGH'])
def test_band_flag_ramp_up(monitor, runtime, age, acted, kind):
    m = monitor
    running(m, True)
    m.task_txn('sample', lambda t: t['stages'][0].update(measured_runtime_seconds=runtime))
    pod = {'metadata': {'name': 'work-17-abc', 'creationTimestamp': '1970-01-01T00:00:01Z'},
           'status': {'startTime': datetime.fromtimestamp(10000-age, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}}
    with patch.object(m, 'now', return_value=10000), patch.object(m, 'job_pods', return_value=[pod]), \
         patch.object(m, 'namespace_offenders', return_value=[{'ours': True}]*3) as offenders, \
         patch.object(m, 'save_task_logs'), patch.object(m, 'kubectl', return_value=result([])) as kc, \
         patch.object(m, 'utilization_restart') as restart, patch.object(m, 'push'):
        for _ in range(2):
            m.task_pod_flag({}, 'sample', 'a', 'work-17-abc', kind, kind + ' work-17-abc cpu 12/2 (600%) rule=nrp')
    t = m.task_load('sample')
    if acted:
        assert kc.called and 'nrp_flag_since' in t['stages'][0]
    else:
        offenders.assert_not_called()
        kc.assert_not_called()
        restart.assert_not_called()
        assert not t.get('webhook_outbox')
        assert 'nrp_flag_since' not in t['stages'][0]
        assert sum('band flag during ramp-up' in e for e in t['events']) == 1


@pytest.mark.parametrize('ours,stop', [(0, False), (2, False), (3, True)])
def test_safety_stop_counts_only_our_account(monitor, ours, stop):
    m = monitor
    running(m)
    offenders = [{'ours': False}]*5 + [{'ours': True}]*ours
    with patch.object(m, 'now', return_value=10000), patch.object(m, 'job_pods', return_value=[]), \
         patch.object(m, 'namespace_offenders', return_value=offenders), \
         patch.object(m, 'memory_low_evidence', return_value={'right_gi': 10, 'need_gi': 6.1}), \
         patch.object(m, 'thanos_query', return_value=[{'value': [0, '2']}]), \
         patch.object(m, 'save_task_logs'), patch.object(m, 'kubectl', return_value=result([])) as kc, patch.object(m, 'push'):
        m.utilization_band_action('sample', 'a', 'pod', 'LOW pod mem 1/32Gi (3%) rule=nrp')
    assert kc.called == stop


def test_coordinator_sized_wakes_once_then_stops_after_grace(monitor):
    m = monitor
    running(m, True)
    m.task_txn('sample', lambda t: t['stages'][0].update(coordinator_sized=1))
    with patch.object(m, 'now', return_value=10000), patch.object(m, 'job_pods', return_value=[]), \
         patch.object(m, 'namespace_offenders', return_value=[]), \
         patch.object(m, 'memory_low_evidence', return_value={'right_gi': 10, 'need_gi': 6.1}), \
         patch.object(m, 'thanos_query', return_value=[{'value': [0, '2']}]), \
         patch.object(m, 'utilization_restart') as restart, patch.object(m, 'save_task_logs'), \
         patch.object(m, 'kubectl', return_value=result([])) as kc, patch.object(m, 'push'):
        for _ in range(2):
            m.utilization_band_action('sample', 'a', 'pod', 'LOW pod mem 1/32Gi (3%) rule=nrp')
        assert len(m.task_load('sample')['webhook_outbox']) == 1
        kc.assert_not_called()
        m.task_txn('sample', lambda t: t['stages'][0].update(nrp_flag_since=8000))
        m.utilization_band_action('sample', 'a', 'pod', 'LOW pod mem 1/32Gi (3%) rule=nrp')
        assert kc.called
        restart.assert_not_called()


@pytest.mark.parametrize('flag', ['nrp_stopped', 'nrp_woken', 'util_deleted', None])
def test_resume_preserves_coordinator_sizing(monitor, flag):
    m = monitor
    task(m)
    def setup(t):
        t['status'] = 'WITH_COORDINATOR'
        if flag:
            t['stages'][0].update({flag: True, 'nrp_flag_since': 1})
    m.task_txn('sample', setup)
    with patch.object(m, 'now', return_value=10000):
        m.cmd_task_resume(argparse.Namespace(name='sample', skip=[], note=None, retries=None))
    stage = m.task_load('sample')['stages'][0]
    assert ('coordinator_sized' in stage) == bool(flag)
    if flag:
        assert stage['coordinator_sized'] == 10000
        assert not any(k in stage for k in ('nrp_flag_since', 'nrp_stopped', 'nrp_woken'))


def test_operator_resize_sets_coordinator_sized(monitor):
    m = monitor
    cli_args = importlib.import_module(m._modules["state"].__package__ + ".cli_args")
    running(m)
    args = cli_args.monitor_parser().parse_args(['task', 'resize', 'sample', '--cpu', '2', '--mem', '4Gi'])
    with patch.object(m, 'now', return_value=10000), patch.object(m, 'save_task_logs'), patch.object(m, 'kubectl', return_value=result([])):
        assert args.f(args) == 0
    assert m.task_load('sample')['stages'][0]['coordinator_sized'] == 10000


@pytest.mark.parametrize('uri,valid', [
    ('s3://test/new/done.json', True), ('s3://test', False), ('s3://test/', False),
    ('s3://test/folder/', False), ('https://test/done', False), ('', False)])
def test_stage_done_marker(monitor, uri, valid):
    m = monitor
    cli_args = importlib.import_module(m._modules["state"].__package__ + ".cli_args")
    task(m)
    args = cli_args.monitor_parser().parse_args(['task', 'stage', 'sample', 'a', '--done-s3', uri])
    if valid:
        assert args.f(args) == 0
        t = m.task_load('sample')
        assert t['stages'][0]['done_s3'] == [uri]
        assert any('stage a done marker changed from s3://test/key to ' + uri + ' by operator' in e for e in t['events'])
    else:
        with pytest.raises(SystemExit, match='done_s3'):
            args.f(args)
        assert m.task_load('sample')['stages'][0]['done_s3'] == ['s3://test/key']


def test_multicontainer_restart_uses_each_containers_measurements(monitor):
    m = monitor
    t = running(m, True)
    doc = m.manifest_doc(t['stages'][0]['manifest'])
    doc['spec']['template']['spec']['containers'].append({'name': 'helper'})
    m.manifest_write(t['stages'][0]['manifest'], doc)
    with patch.object(m, 'job_pods', return_value=[]), patch.object(m, 'namespace_offenders', return_value=[]), patch.object(m, 'memory_low_evidence', return_value={'right_gi': 10, 'need_gi': 6.1}), patch.object(m, 'thanos_query', return_value=[{'value': [0, '2']}]), patch.object(m, 'thanos_peak_mem', return_value=2*2**30), patch.object(m, 'utilization_restart', return_value=(True, 'queued')) as restart:
        m.utilization_band_action('sample', 'a', 'work-17-p', 'LOW work-17-p mem 1/32Gi (3%) rule=nrp')
        sizes = restart.call_args.kwargs['container_resources']
        assert sizes['worker']['memory'] == str(10*2**30)
        assert sizes['helper']['memory'] == str(3*2**30)


@pytest.mark.parametrize('line,hi', [
    ('LOW checked 3 pods; account: 1 of 90 running pods outside NRP bands, +2 started under 5 min ago (not judged yet)', True),
    ('LOW checked 3 pods; account: 1 of 90 running pods outside NRP bands', False),
    ('LOW checked 3 pods; account: 5 of 90 running pods outside NRP bands (NRP blocks submits past 4)', True)])
def test_account_alarm_still_counts_starting_pods(monitor, line, hi):
    st = {'acct_hi': 1}
    with patch.object(monitor, 'push') as push:
        monitor.acct_alarm(st, [line], [], False)
    assert push.called == hi and st['acct_hi'] == (2 if hi else 0)


@pytest.mark.parametrize('line,pods,acted', [
    ('LOW work-17-abc age 5m, 4m mean: mem 0.5/3.0Gi (16%) rule=nrp', [], False),      # the flag line's own age
    ('LOW work-17-abc age 12m, 10m mean: mem 0.5/3.0Gi (16%) rule=nrp', [], True),
    ('LOW work-17-abc mem 0.5/3.0Gi (16%) rule=nrp', RuntimeError('kubectl'), True)])  # unknown age never holds the action back
def test_ramp_up_age_from_line_or_unknown(monitor, line, pods, acted):
    m = monitor
    running(m, True)
    kw = {'side_effect': pods} if isinstance(pods, Exception) else {'return_value': pods}
    with patch.object(m, 'now', return_value=10000), patch.object(m, 'job_pods', **kw), \
         patch.object(m, 'namespace_offenders', return_value=[{'ours': True}]*3), \
         patch.object(m, 'save_task_logs'), patch.object(m, 'kubectl', return_value=result([])) as kc, patch.object(m, 'push'):
        m.task_pod_flag({}, 'sample', 'a', 'work-17-abc', 'LOW', line)
    assert kc.called == acted

"""Offline regressions for true peaks, resource budgets and sibling propagation."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from test_agent_runners import load_module

GI = 2**30


@pytest.fixture
def monitor(tmp_path):
    return load_module(tmp_path / 'state')


def manifest(path, memory='1Gi', cpu='500m', image='worker:v1'):
    doc = {'spec': {'template': {'spec': {'containers': [{'name': 'worker', 'image': image,
        'resources': {'requests': {'memory': memory, 'cpu': cpu}, 'limits': {'memory': memory, 'cpu': cpu}}}]}}}}
    path.write_text(json.dumps(doc))
    return str(path)


def test_resource_infra_queue_budgets_are_per_stage_others_task_wide(monitor):
    t = {'attempts': [{'cls': 'resources', 'stage': 'a'}] * 3 + [{'cls': 'infra', 'stage': 'a'},
         {'cls': 'queue', 'stage': 'a'}, {'cls': 'code', 'stage': 'a'}], 'max_retries': 4}
    assert monitor.class_retries(t, {'cls': 'resources', 'stage': 'b'}) == 0
    assert monitor.class_retries(t, {'cls': 'resources', 'stage': 'a'}) == 3
    assert monitor.class_retries(t, {'cls': 'infra', 'stage': 'b'}) == 0
    assert monitor.class_retries(t, {'cls': 'infra', 'stage': 'a'}) == 1
    assert monitor.class_retries(t, {'cls': 'queue', 'stage': 'b'}) == 0
    assert monitor.class_retries(t, {'cls': 'code', 'stage': 'b'}) == 1
    t['budget_from'] = 3
    assert monitor.class_retries(t, {'cls': 'resources', 'stage': 'a'}) == 0


def test_true_peak_parser_rejects_invalid_and_rss(monitor):
    rows = ['garbage', 'NRP_MEMORY_PEAK {', 'NRP_MEMORY_PEAK []',
            'NRP_MEMORY_PEAK ' + json.dumps({'source': 'cgroup_v2', 'bytes': True}),
            'NRP_MEMORY_PEAK ' + json.dumps({'source': 'ru_maxrss', 'bytes': 10*GI}),
            'NRP_MEMORY_PEAK ' + json.dumps({'source': 'cgroup_v1', 'bytes': GI}),
            'NRP_MEMORY_PEAK ' + json.dumps({'source': 'cgroup_v2', 'bytes': 2*GI}),
            'NRP_MEMORY_PEAK ' + json.dumps({'source': 'cgroup_v2', 'bytes': 3*GI, 'container': 'sidecar'})]
    assert monitor.true_memory_peak('\n'.join(rows)) == 2*GI
    assert monitor.true_memory_peak('\n'.join(rows), 'sidecar') == 3*GI


@pytest.mark.parametrize('sample,true,expected', [(0.1*GI, None, '2Gi'), (.5*GI, None, '2Gi'),
                                                   (.1*GI, 3*GI, '4Gi'), (None, 2*GI, '3Gi')])
def test_oom_backstop_and_true_peak_precedence(monitor, tmp_path, sample, true, expected):
    s = {'id': 'a', 'job': 'work', 'manifest': manifest(tmp_path/'a.json')}
    t = {'name': 't', 'namespace': 'test'}
    with patch.object(monitor, 'job_pods', return_value=[]), patch.object(monitor, 'saved_memory_peak', return_value=true), \
         patch.object(monitor, 'thanos_peak_mem', return_value=sample), patch.object(monitor, 'util_policy', return_value={}):
        result = monitor.tier0_oom(t, s, {'sig': 'oom@1Gi'})
    assert result[2]['memory'] == expected


def test_saved_peaks_are_scoped_to_attempt(monitor):
    t, s = {'name': 't'}, {'job': 'work', 'attempt': 2}
    folder = monitor.task_dir('t') / 'logs'
    folder.mkdir(parents=True)
    for attempt, peak in [(1, 8*GI), (2, GI)]:
        (folder / ('work-a%d.txt' % attempt)).write_text('NRP_MEMORY_PEAK '+json.dumps({'source': 'cgroup_v2', 'bytes': peak}))
    assert monitor.saved_memory_peak(t, s) == GI
    assert monitor.saved_memory_peak(t, s, all_attempts=True) == 8*GI


def test_siblings_only_raise_files_after_successful_resource_retry(monitor, tmp_path):
    stages = []
    for sid, state, group, memory, cpu, image in [('a','done','shared','2Gi','2','worker:v1'),
            ('b','running','shared','1Gi','3','worker:v1'), ('c','pending','shared','4Gi','500m','worker:v1'),
            ('d','done','shared','1Gi','500m','worker:v1'), ('e','pending','other','1Gi','500m','worker:v1'),
            ('f','pending','shared','1Gi','500m','other:v1')]:
        stages.append({'id':sid,'state':state,'resource_group':group,
                       'manifest':manifest(tmp_path/(sid+'.json'),memory,cpu,image)})
    t = {'name':'t','stages':stages,'attempts':[],'events':[]}
    before = {s['id']:Path(s['manifest']).read_text() for s in stages}
    monitor.propagate_resources(t, stages[0])
    assert not t['events']
    t['attempts']=[{'stage':'a','cls':'resources','by':'agent','resources_changed':True,
                    'resource_template':monitor.resource_template(monitor.manifest_doc(stages[0]['manifest']))}]
    with patch.object(monitor,'kubectl',side_effect=AssertionError('no live mutations')):
        monitor.propagate_resources(t,stages[0])
    for sid, memory, cpu in [('b','2Gi','3'),('c','4Gi','2')]:
        res=monitor.manifest_doc(tmp_path/(sid+'.json'))['spec']['template']['spec']['containers'][0]['resources']
        assert res['requests'] == {'memory':memory,'cpu':cpu}
        assert res['limits'] == res['requests']
    for sid in ['a','d','e','f']:
        assert (tmp_path/(sid+'.json')).read_text() == before[sid]
    assert len(t['events']) == 2
    monitor.propagate_resources(t,stages[0])
    assert len(t['events']) == 2


def test_helper_cgroup_and_rss_fallback(tmp_path):
    path=Path(__file__).resolve().parents[3]/'nrp-cluster/references/memory_peak.py'
    spec=importlib.util.spec_from_file_location('memory_peak',path)
    helper=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    def read(p):
        if str(p)=='/proc/self/cgroup': return '0::/worker\n'
        if str(p)=='/sys/fs/cgroup/worker/memory.peak': return str(2*GI)
        raise OSError('unavailable')
    with patch.object(Path,'read_text',read):
        assert helper.measure()=={'bytes':2*GI,'source':'cgroup_v2'}
    with patch.object(Path,'read_text',side_effect=OSError('unavailable')):
        assert helper.measure()['source']=='ru_maxrss'


def test_submit_enforces_stage_budget_and_task_cap(monitor):
    stage = {'id':'b','job':'work','manifest':'unused','state':'failed'}
    t = {'stages':[stage],'namespace':'test','mode':'auto','max_retries':4,
         'failure':{'stage':'b','cls':'resources'},
         'attempts':[{'stage':'a','cls':'resources'}]*3}
    with patch.object(monitor,'task_load',return_value=t), \
         patch.object(monitor,'manifest_check',return_value=['sentinel: budget passed']), \
         patch.object(monitor,'kubectl',side_effect=AssertionError('no cluster')):
        assert 'sentinel' in monitor.do_submit('t','b','retry','agent')[1]
        t['attempts'].append({'stage':'a','cls':'resources'})
        assert 'RETRY CAP' in monitor.do_submit('t','b','retry','agent')[1]
        t['attempts']=[{'stage':'b','cls':'resources'}]*3
        assert 'BUDGET USED' in monitor.do_submit('t','b','retry','agent')[1]


def test_wrapper_preserves_status_and_updates_only_success_marker(tmp_path):
    import subprocess
    import sys
    path=Path(__file__).resolve().parents[3]/'nrp-cluster/references/memory_peak.py'
    marker=tmp_path/'done.json'
    marker.write_text('{"done":true}')
    result=subprocess.run([sys.executable,str(path),'--done-json',str(marker),'--',sys.executable,'-c','pass'],capture_output=True,text=True)
    assert result.returncode==0
    assert result.stdout.startswith('NRP_MEMORY_PEAK ')
    assert json.loads(marker.read_text())['done'] is True
    assert 'memory_peak' in json.loads(marker.read_text())
    before=marker.read_text()
    result=subprocess.run([sys.executable,str(path),'--done-json',str(marker),'--',sys.executable,'-c','raise SystemExit(7)'],capture_output=True,text=True)
    assert result.returncode==7
    assert marker.read_text()==before


def test_verified_completion_triggers_propagation(monitor, tmp_path):
    a={'id':'a','job':'source','state':'running','manifest':manifest(tmp_path/'a.json','2Gi'),
       'resource_group':'shared','done_s3':['s3://bucket/success']}
    b={'id':'b','job':'sibling','state':'pending','manifest':manifest(tmp_path/'b.json'),
       'resource_group':'shared'}
    t={'name':'t','namespace':'test','status':'running','stages':[a,b], 'events':[],
       'attempts':[{'stage':'a','cls':'resources','by':'tier0','resources_changed':True,
                    'resource_template':monitor.resource_template(monitor.manifest_doc(a['manifest']))}]}
    manifest(Path(a['manifest']), '1Gi')  # a review prepared a smaller size for later runs
    monitor.task_write(t)
    with patch.object(monitor,'save_task_logs',return_value=('log','')), \
         patch.object(monitor,'s3_exists',return_value=True), patch.object(monitor,'kubectl'), \
         patch.object(monitor,'digest'):
        monitor.observe_task('t',{'source':{'state':'ok'}})
    result=monitor.task_load('t')
    assert result['stages'][0]['state']=='done'
    res=monitor.manifest_doc(b['manifest'])['spec']['template']['spec']['containers'][0]['resources']
    assert res['limits']['memory']=='2Gi'
    assert any('resource propagation a -> b' in event for event in result['events'])


@pytest.mark.parametrize('changed', [False, True])
def test_retry_records_actual_resource_change(monitor, tmp_path, changed):
    path=tmp_path/'job.json'
    s={'id':'a','job':'work','manifest':manifest(path),'state':'running'}
    t={'name':'t','namespace':'test','status':'running','stages':[s],'mode':'auto',
       'attempts':[],'failure':None,'events':[],'max_retries':4}
    monitor.task_write(t)
    monitor.task_fail('t','a','resources','oom@1Gi','oom')
    if changed:
        manifest(path,'2Gi')
    with patch.object(monitor,'manifest_check',return_value=[]), patch.object(monitor,'gpu_expired',return_value=None), \
         patch.object(monitor,'job_state',return_value='missing'), patch.object(monitor,'bad_nodes',return_value={}), \
         patch.object(monitor,'apply_manifest',return_value='ok'), \
         patch.object(monitor,'kubectl',side_effect=AssertionError('no cluster')):
        assert monitor.do_submit('t','a','memory repair','agent')[0]
    assert monitor.task_load('t')['attempts'][0]['resources_changed'] is changed

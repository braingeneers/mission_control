"""Regression coverage for the November 11 real-CLI followups; no cluster writes."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_agent_runners import load_module
import pytest

@pytest.fixture
def w(tmp_path):
    state = tmp_path / 'state'; state.mkdir()
    m = load_module(state)
    with patch.object(m, 'log'), patch.object(m, 'digest'):
        yield m


def test_shared_bad_nodes_refresh_decay_and_digest(w):
    with patch.object(w, 'now', return_value=100): w.record_bad_node('node-a', 'Xid')
    with patch.object(w, 'now', return_value=500): w.record_bad_node('node-a', 'ECC')
    with patch.object(w, 'now', return_value=86500):
        assert w.bad_nodes()['node-a']['expires'] == 86900
        assert 'node-a until' in '\n'.join(w.bad_node_lines())
        assert 'node-a' in w.render_digest(24)
    with patch.object(w, 'now', return_value=86900): assert not w.bad_nodes()


def test_thanos_vanished_node(w):
    t={'namespace':'test'}; s={'job':'job-a', 'submitted':w.now()-1000}
    with patch.object(w,'job_pods',return_value=[]), patch.object(w,'thanos_query',return_value=[{'metric':{'node':'bad'}}]) as q:
        assert w.node_fault_of(t,s,{'cls':'unknown'})[0]=='bad'
        assert 'kube_pod_info' in q.call_args.args[0]
        assert 'job' in q.call_args.args[0]
    with patch.object(w,'job_pods',return_value=[]), patch.object(w,'thanos_query',return_value=[]):
        assert w.node_fault_of(t,s,{'cls':'unknown'}) is None


def test_auth_eligibility_and_failover(w,tmp_path):
    raw=json.dumps({'is_error':True,'error':{'type':'IneligibleTierError','message':'UNSUPPORTED_CLIENT'}})
    assert w.auth_hit(1,raw,'')
    with patch.object(w,'tier_backends',return_value=[{'runner':'gemini'},{'runner':'claude'}]), patch.object(w,'runner_ready',return_value=True), patch.object(w,'runner_blocked',return_value=False), patch.object(w,'block_runner'), patch.dict(w.RUNNER_EXEC,gemini=lambda *a:('auth',raw,'',1),claude=lambda *a:('ok','CLOSE: healthy','',0)):
        assert w.dispatch_agent({'tier':'triage'},'',tmp_path)[0]=='claude'


def test_task_help_and_missing_task(w):
    with patch.dict('os.environ',{'NRP_TASK':''}), contextlib.redirect_stdout(io.StringIO()) as out:
        assert w.cmd_tool(SimpleNamespace(rest=['reship','--help']))==0
    assert 'NRP_TASK=<name>' in out.getvalue()
    with patch.dict('os.environ',{'NRP_TASK':''}), patch.object(w,'task_names',return_value=['live']), patch.object(w,'task_load',side_effect=lambda n: {'status':'running'} if n=='live' else None):
        with pytest.raises(SystemExit,match='live tasks: live'): w.cmd_tool(SimpleNamespace(rest=['show']))


def test_open_claude_deferred_without_invoking_resume(w):
    with patch.object(w,'claude_session_open',return_value=True), patch.object(w.subprocess,'run') as run:
        with pytest.raises(w.WakeError,match='deferred'): w.wake_session({'harness':'claude','session':'abc'},'wake')
        run.assert_not_called()


def test_open_session_process_and_transcript(w,tmp_path):
    with patch.object(w.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='claude --resume abc\n')):
        assert w.claude_session_open('abc')
    p=tmp_path/'.claude/projects/project/abc.jsonl'; p.parent.mkdir(parents=True);p.touch()
    with patch.object(w.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='')), patch.object(w.Path,'home',return_value=tmp_path):
        assert w.claude_session_open('abc')
        with patch.object(w,'now',return_value=p.stat().st_mtime+301): assert not w.claude_session_open('abc')


def test_agy_gate(w,tmp_path):
    w.agy_workspace(tmp_path,['Bash(nrp-task logs:*)',f'Read(/{tmp_path}/data/**)'])
    data=tmp_path/'data'; data.mkdir()
    def gate(name,args):
        r=subprocess.run([sys.executable,str(tmp_path/'.agents/gate.py'),str(tmp_path/'.agents/allow.json')],input=json.dumps({'toolCall':{'name':name,'args':args}}),text=True,capture_output=True,check=True)
        return json.loads(r.stdout)['decision']
    assert gate('run_command',{'CommandLine':'nrp-task logs job --tail 20'})=='allow'
    for cmd in ('touch /tmp/no','nrp-task logs job; touch /tmp/no','nrp-task logs $(id)','nrp-task submit job','nrp-task logs job > out'):
        assert gate('run_command',{'CommandLine':cmd})=='deny'
    assert gate('view_file',{'AbsolutePath':str(data/'a')})=='allow'
    assert gate('view_file',{'AbsolutePath':str(data/'../outside')})=='deny'
    assert gate('replace_file_content',{})=='deny'


def test_agy_config_restriction_and_setup(w):
    assert w.check_backend('triage',0,{'runner':'agy'})['runner']=='agy'
    with pytest.raises(ValueError): w.check_backend('task',0,{'runner':'agy'})
    assert w.suggest_tiers(['agy','claude'])['triage'][0]['runner']=='agy'


def test_submit_blocks_live_job_and_cleans_terminal(w,tmp_path):
    manifest=tmp_path/'job.json'; manifest.write_text(json.dumps({'kind':'Job','metadata':{'name':'job'},'spec':{'template':{'spec':{'containers':[{'name':'worker','image':'worker:v1'}]}}}}))
    t={'name':'t','namespace':'test','failure':None,'stages':[{'id':'s','job':'job','state':'pending','manifest':str(manifest)}]}
    for status in ('running','pending','error','FAILED','ok','missing'):
        def apply(ns,path):
            assert 'bad' in Path(path).read_text()
            return 'ok'
        with patch.object(w,'task_load',return_value=t), patch.object(w,'manifest_check',return_value=[]), patch.object(w,'gpu_expired',return_value=None), patch.object(w,'job_state',return_value=status), patch.object(w,'save_task_logs') as logs, patch.object(w,'kubectl',return_value=SimpleNamespace(returncode=0)) as kube, patch.object(w,'apply_manifest',side_effect=apply) as submit, patch.object(w,'bad_nodes',return_value={'bad':{}}), patch.object(w,'task_txn',side_effect=RuntimeError('submitted')):
            if status in ('running','pending','error'):
                assert w.do_submit('t','s','reason','test')[0] is False
                kube.assert_not_called();submit.assert_not_called()
            else:
                with pytest.raises(RuntimeError,match='submitted'): w.do_submit('t','s','reason','test')
                assert logs.called == (status in ('FAILED','ok'))
                assert kube.called == logs.called
    assert 'bad' not in manifest.read_text()


def test_same_fault_does_not_refresh_forever(w):
    with patch.object(w,'now',return_value=100): w.record_bad_node('bad','fault','task/stage/100')
    with patch.object(w,'now',return_value=90000):
        w.record_bad_node('bad','fault','task/stage/100')
        assert not w.bad_nodes()
        w.record_bad_node('bad','fault','task/stage/90000')
        assert w.bad_nodes()['bad']['expires']==176400


def test_stage_node_cli(w,tmp_path):
    path=tmp_path/'manifest'; path.write_text(json.dumps({'kind':'Job','metadata':{'name':'job'},'spec':{'template':{'spec':{'containers':[{'name':'worker','image':'worker:v1'}]}}}}))
    t={'stages':[{'id':'s','manifest':str(path)}]}
    with patch.object(w,'task_load',return_value=t):
        assert w.cmd_task_stage(SimpleNamespace(name='t',stage='s',resumable=False,exclude_node=['bad']))==0
        assert 'bad' in path.read_text()
        with pytest.raises(SystemExit,match='invalid node'): w.cmd_task_stage(SimpleNamespace(name='t',stage='s',resumable=False,exclude_node=['bad;echo']))


def test_agy_argv_and_result(w,tmp_path):
    def run(argv,**kw):
        assert argv[0]=='agy'
        assert argv[argv.index('--mode')+1]=='plan'
        assert argv[argv.index('--effort')+1]=='low'
        assert '--dangerously-skip-permissions' not in argv
        assert '--disable-slash-commands' not in argv
        assert (Path(kw['cwd'])/'.agents/hooks.json').exists()
        return SimpleNamespace(returncode=0,stdout=json.dumps({'result':'CLOSE: healthy'}),stderr='')
    with patch.object(w.subprocess,'run',side_effect=run):
        result=w.exec_agy({'tier':'triage','allowed':[],'json':True},'fixture',tmp_path,10,{})
    assert w.triage_verdict(json.loads(result[1])['result'])[0]=='CLOSE'

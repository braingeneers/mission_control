"""Robustness regressions: scratch state and fake runners only."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from test_wake import Base, FAKE


class T3Wake(Base):
    def test_cli_link_and_wrapping_deliver_once(self):
        binary = self.bin / 't3'
        binary.write_text(FAKE.replace('@FAKE@', str(self.fake)))
        binary.chmod(0o755)
        for link in ('t3-thread://v2/env/thread-id', '<t3-thread://v2/env/thread-id>'):
            t = self.task(origin={'link': link})
            self.assertEqual(self.w.wake_target(t), {'harness': 't3-cli', 'session': 'thread-id'})
            self.w.task_txn('t1', lambda t: self.w.queue_task_webhook(t, 'done'))
            with patch.dict(os.environ, NRP_MONITOR_T3_BIN=str(binary)):
                self.deliver()
                self.deliver()
            self.assertEqual(self.argv('t3'), ['thread', 'send', 'thread-id', '-'])
            self.assertIn('NRP task t1 finished', (self.fake / 't3.stdin').read_text())
            self.assertEqual(self.outbox(), [])
        self.assertEqual(self.calls('t3'), 2)

    def test_cli_failure_and_missing_binary_retry_then_owner(self):
        binary = self.bin / 't3'
        binary.write_text('#!/bin/sh\nexit 7\n')
        binary.chmod(0o755)
        for path in (str(binary), str(self.bin / 'absent')):
            self.task(origin={'link': 't3-thread://v2/env/thread-id'})
            self.w.to_coordinator('t1', 'needs review')
            with patch.dict(os.environ, NRP_MONITOR_T3_BIN=path):
                for i in range(self.w.WAKE_MAX_TRIES):
                    self.deliver()
                    self.assertEqual(self.w.task_load('t1')['status'], 'NEEDS_OWNER' if i+1 == self.w.WAKE_MAX_TRIES else 'WITH_COORDINATOR')
            self.assertEqual(self.outbox(), [])

    def test_webhook_preferred_over_cli(self):
        t = self.task(origin={'link': 't3-thread://v2/env/thread-id'})
        p = self.w.STATE / 'webhooks' / 't1'
        p.parent.mkdir(exist_ok=True)
        p.write_text('{}')
        self.assertEqual(self.w.wake_target(t), {'harness': 't3'})


class Memory(Base):
    def stage(self):
        manifest = self.tmp / 'job.json'
        manifest.write_text(json.dumps({'spec': {'template': {'spec': {'containers': [
            {'name': 'worker', 'resources': {'requests': {'memory': '12Gi'}, 'limits': {'memory': '12Gi'}}}
        ]}}}}))
        self.w.TPL = Path(__file__).resolve().parents[1] / 'templates'
        t = self.task(goal='goal', notes='', attempts=[{'stage': 'a', 'sig': 'oom@6Gi'}])
        t['stages'][0].update(manifest=str(manifest), submitted=self.w.now()-3600, pod_started=self.w.now()-1020)
        self.w.task_write(t)
        return t, t['stages'][0]

    def evidence(self, t, s, peaks=None, pods=None):
        with patch.object(self.w, 'job_pods', return_value=pods or []), patch.object(self.w, 'thanos_peak_mem', return_value=peaks or {'p1': 4.5*2**30, 'p2': 7.7*2**30}):
            return self.w.memory_low_evidence(t, s, 'p2')

    def test_big_s_example_and_history_ramp(self):
        t, s = self.stage()
        e = self.evidence(t, s)
        self.assertTrue(e['ramp_up'])
        self.assertEqual((e['need_gi'], e['right_gi'], e['suggested_verdict']), (7.7, 10, 'sized correctly'))
        self.assertAlmostEqual(e['spread'], 7.7/6.1)
        s['measured_runtime_seconds'] = 3600
        e = self.evidence(t, s)
        self.assertFalse(e['ramp_up'])
        s['measured_runtime_seconds'] = 7200
        self.assertTrue(self.evidence(t, s)['ramp_up'])

    def test_oom_floor_and_missing_peaks(self):
        t, s = self.stage()
        e = self.evidence(t, s, {'p2': 1*2**30})
        self.assertEqual((e['need_gi'], e['right_gi']), (6, 8))
        with patch.object(self.w, 'job_pods', return_value=[]), patch.object(self.w, 'thanos_peak_mem', return_value={}):
            s.pop('memory_peaks_gi', None)
            e = self.w.memory_low_evidence(t, s, 'p2')
        self.assertIn('missing peaks', e['suggested_verdict'])

    def test_split_only_with_whole_life_low_pods(self):
        t, s = self.stage()
        peaks = {'small1': .5*2**30, 'small2': .6*2**30, 'p2': 8*2**30}
        pods = [{'metadata': {'name': 'small1'}, 'status': {'phase': 'Succeeded'}}]
        self.assertEqual(self.evidence(t, s, peaks, pods)['suggested_verdict'], 'inputs differ in size')
        self.assertNotEqual(self.evidence(t, s, peaks)['suggested_verdict'], 'inputs differ in size')

    def test_ramp_flag_is_suppressed_and_mature_flag_keeps_running(self):
        t, s = self.stage()
        line = 'LOW p2 age 17m, 10m mean: mem 1.2/12Gi (10%) [NRP violation] rule=nrp'
        st = {'strikes': {}}
        with patch.object(self.w, 'memory_low_evidence', return_value={'ramp_up': True}):
            self.w.task_pod_flag(st, 't1', 'a', 'p2', 'LOW', line)
        self.assertNotIn('util_event', self.w.task_load('t1'))
        with patch.object(self.w, 'memory_low_evidence', return_value=dict(self.evidence(t, s), ramp_up=False)):
            self.w.task_pod_flag(st, 't1', 'a', 'p2', 'LOW', line)
        result = self.w.task_load('t1')
        self.assertEqual(result['stages'][0]['state'], 'running')
        self.assertIsNone(result['failure'])
        self.assertEqual(result['status'], 'running')
        self.assertIn('util_event', result)

    def test_per_pod_query(self):
        with patch.object(self.w, 'thanos_query', return_value=[{'metric': {'pod': 'p'}, 'value': [0, '123']}]) as query:
            self.assertEqual(self.w.thanos_peak_mem('ns', 'job', 'c', self.w.now()-3600, per_pod=True), {'p': 123})
            self.assertIn('max by (pod)', query.call_args.args[0])
            self.assertIn('max_over_time', query.call_args.args[0])

    def test_watch_only_observation_never_starts_a_fixer(self):
        t, s = self.stage()
        t.update(mode='watch', util_event={'stage': 'a', 'job': 't1-a', 'cls': 'util', 'sig': 'low', 'detail': 'low', 'ts': 1, 'evidence': None})
        t['attempts'] = []
        self.w.task_write(t)
        def judge(n, prompt, a, kind='fix'):
            self.assertEqual(kind, 'triage')
            self.w.task_txn(n, lambda t: t.setdefault('agent_runs', []).append({'verdict': 'ESCALATE'}))
            return 'ESCALATE: sizing needs review', []
        with patch.object(self.w, 'run_task_agent', side_effect=judge) as agent:
            self.w.process_util_event('t1', SimpleNamespace(dry_run=False))
        agent.assert_called_once()
        self.assertEqual(self.w.task_load('t1')['status'], 'running')

    def test_judge_contract_rejects_every_other_reply(self):
        for text in ('RESUBMITTED: changed resources', 'BENIGN: old contract', 'CLOSE: fine\nI edited the manifest', ''):
            self.assertEqual(self.w.triage_verdict(text)[0], 'ESCALATE')
        self.assertEqual(self.w.triage_verdict('CLOSE: need 7.7Gi, right 10Gi, request 12Gi')[0], 'CLOSE')

    def test_configured_roles_share_memory_evidence_and_only_fixer_changes(self):
        for triage, fixer in [('claude', 'claude'), ('codex', 'codex'), ('gemini', 'claude'), ('agy', 'claude'), (None, None)]:
            if triage:
                self.w.AGENTS_CFG.write_text(json.dumps({'tiers': {'triage': [{'runner': triage}], 'task': [{'runner': fixer}]}}))
            elif self.w.AGENTS_CFG.exists():
                self.w.AGENTS_CFG.unlink()
            t, s = self.stage()
            e = self.evidence(t, s)
            t.update(util_event={'stage': 'a', 'job': 't1-a', 'cls': 'util', 'sig': 'low', 'detail': 'low', 'ts': 1, 'evidence': e})
            t['attempts'] = []
            self.w.task_write(t)
            seen = []
            def runner(spec, prompt, cwd, timeout, env):
                kind = 'triage' if spec['tier'] == 'triage' else 'fix'
                seen.append((kind, prompt, spec['backend']['runner']))
                if kind == 'triage':
                    self.assertEqual(env['NRP_MONITOR_AGENT_ROLE'], 'triage')
                    self.assertFalse(any(x.startswith(('Edit(', 'Write(', 'Bash(nrp-task:')) for x in spec['allowed']))
                return 'ok', json.dumps({'result': 'ESCALATE: review numbers' if kind == 'triage' else 'DONE: manifest prepared'}), '', 0
            with patch.dict(self.w.RUNNER_EXEC, {r: runner for r in self.w.KNOWN_RUNNERS}), patch.object(self.w, 'runner_ready', return_value=True), patch.object(self.w, 'task_prompt', return_value='fixer'):
                self.w.process_util_event('t1', SimpleNamespace(dry_run=False))
            self.assertEqual([x[0] for x in seen], ['triage', 'fix'])
            self.assertEqual([x[2] for x in seen], [triage or 'claude', fixer or 'claude'])
            for _, prompt, _ in seen:
                self.assertIn('7.7', prompt)
                self.assertIn('right_gi', prompt)
                self.assertIn('fixer alone changes', prompt)
            self.assertEqual(self.w.task_load('t1')['status'], 'running')


class Held(Base):
    def test_complete_with_markers_clears_hold_and_advances(self):
        for status in self.w.TASK_HELD:
            t = self.task(status=status, failure={'stage': 'a'}, reason='needs review')
            t['stages'][0].update(state='failed', done_s3=['s3://bucket/done'])
            self.w.task_write(t)
            with patch.object(self.w, 'fetch_jobs', return_value={'t1-a': {'state': 'ok'}}), patch.object(self.w, 's3_exists', return_value=True), patch.object(self.w, 'advance_task') as advance:
                self.w.process_tasks(SimpleNamespace(dry_run=False), {})
            self.assertEqual(self.w.task_load('t1')['status'], 'running')
            self.assertEqual(self.w.task_load('t1')['stages'][0]['state'], 'done')
            advance.assert_called_once()

    def test_complete_without_markers_keeps_hold(self):
        t = self.task(status='NEEDS_OWNER', failure={'stage': 'a'})
        t['stages'][0].update(state='failed', done_s3=['s3://bucket/done'])
        self.w.task_write(t)
        with patch.object(self.w, 's3_exists', return_value=False):
            self.assertFalse(self.w.recover_held_completion('t1', {'t1-a': {'state': 'ok'}}))
        self.assertEqual(self.w.task_load('t1')['status'], 'NEEDS_OWNER')
        self.assertIn('success markers missing', self.w.task_load('t1')['reason'])

    def test_recovery_finishes_normally_before_stale_wake_alarm(self):
        t = self.task(status='WITH_COORDINATOR', failure={'stage': 'a'}, coordinator_since=self.w.now()-2*self.w.COORD_STALE_S)
        t['stages'][0].update(state='failed', done_s3=['s3://bucket/done'])
        self.w.task_write(t)
        with patch.object(self.w, 'fetch_jobs', return_value={'t1-a': {'state': 'ok'}}), patch.object(self.w, 's3_exists', return_value=True):
            self.w.process_tasks(SimpleNamespace(dry_run=False), {})
        self.assertEqual(self.w.task_load('t1')['status'], 'done')
        self.assertIsNone(self.w.task_load('t1')['failure'])
        self.push.assert_not_called()

    def test_recovery_starts_ready_next_stage(self):
        t = self.task(status='NEEDS_OWNER', failure={'stage': 'a'})
        t['stages'][0].update(state='failed', done_s3=['s3://bucket/done'])
        t['stages'].append({'id': 'b', 'job': 't1-b', 'state': 'pending', 'after': ['a'], 'done_s3': ['s3://bucket/next']})
        self.w.task_write(t)
        with patch.object(self.w, 'fetch_jobs', return_value={'t1-a': {'state': 'ok'}}), patch.object(self.w, 's3_exists', return_value=True), patch.object(self.w, 'do_submit', return_value=(True, 'submitted')) as submit:
            self.w.process_tasks(SimpleNamespace(dry_run=False), {})
        submit.assert_called_once_with('t1', 'b', 'stage ready', 'monitor')


class Runners(Base):
    def test_agents_test_includes_tier_only_runner_and_setup_records_it(self):
        for runner in ('gemini', 'agy'):
            tiers = {'triage': [{'runner': runner}], 'task': [{'runner': 'claude'}]}
            self.w.AGENTS_CFG.write_text(json.dumps({'runners': ['claude'], 'tiers': tiers}))
            calls = []
            def fake(spec, *args):
                calls.append(spec['backend']['runner'])
                return 'ok', 'OK', '', 0
            with patch.object(self.w, 'runner_ready', return_value=True), patch.dict(self.w.RUNNER_EXEC, {r: fake for r in self.w.KNOWN_RUNNERS}):
                self.assertEqual(self.w.cmd_agents(SimpleNamespace(acmd='test', runner=None)), 0)
            self.assertEqual(calls, ['claude', runner])
            self.assertEqual(self.w.setup_config({}, tiers)['runners'], ['claude', runner])

    def test_triage_task_commands_reject_mutations_in_code(self):
        self.task()
        with patch.dict(os.environ, NRP_TASK='t1', NRP_MONITOR_AGENT_ROLE='triage'):
            for command in ('submit', 'delete', 'report', 'commit', 'configmap', 'next-add'):
                with self.assertRaisesRegex(SystemExit, 'judge only'):
                    self.w.cmd_tool(SimpleNamespace(rest=[command]))

    def test_codex_judge_uses_read_only_sandbox(self):
        auth = self.tmp / 'auth.json'
        auth.write_text('{}')
        def fake(argv, **kwargs):
            self.assertEqual(argv[argv.index('-s')+1], 'read-only')
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        with patch.dict(os.environ, NRP_MONITOR_CODEX_AUTH=str(auth)), patch.object(self.w.subprocess, 'run', side_effect=fake):
            self.w.exec_codex({'tier': 'triage', 'allowed': [], 'json': False}, 'judge', self.tmp, 10, {})

    def test_high_flag_is_an_observation(self):
        self.task()
        line = 'HIGH p age 60m: cpu 4/1 (400%) rule=nrp'
        self.assertIsNotNone(self.w.FLAG.match(line))
        self.w.task_pod_flag({'strikes': {}}, 't1', 'a', 'p', 'HIGH', line)
        t = self.w.task_load('t1')
        self.assertEqual(t['stages'][0]['state'], 'running')
        self.assertIsNone(t['failure'])

    def test_running_util_delete_requires_resumability_and_measured_time(self):
        for resumable, remaining in ((False, 10000), (True, 7200), (True, None)):
            t = self.task(util_event={'job': 't1-a', 'ts': self.w.now(), 'evidence': {'remaining_seconds': remaining}})
            t['stages'][0].update(resumable=resumable)
            self.w.task_write(t)
            with patch.dict(os.environ, NRP_TASK='t1'), patch.object(self.w, 'job_state', return_value='running'):
                with self.assertRaisesRegex(SystemExit, 'leave running Job'):
                    self.w.cmd_tool(SimpleNamespace(rest=['delete', 't1-a']))

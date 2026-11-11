"""Agent runners: per-tier models and ladder from agents.json, Claude -> Codex fallback on a usage limit, and work that waits
(without using a retry or sending a false alert) when every runner is out of usage. No models, cluster or notifications."""
import importlib.machinery
import importlib.util
import json
import os
import shutil
import stat
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import test_tasks as TT          # the fake kubectl/aws/claude harness; used as a helper, not subclassed (its tests would rerun)

SOURCE = Path(__file__).resolve().parents[1] / 'nrp-watchdog'
LIMIT_JSON = json.dumps({"type": "result", "is_error": True, "result": "You've hit your weekly limit · resets 2pm (America/Los_Angeles)"})


def load_module(state):
    old = os.environ.get('NRP_WATCHDOG_STATE')
    os.environ['NRP_WATCHDOG_STATE'] = str(state)       # STATE is read once at import; restore so other test modules are not affected
    try:
        loader = importlib.machinery.SourceFileLoader('watchdog_agents_%d' % time.time_ns(), str(SOURCE))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        m = importlib.util.module_from_spec(spec)
        loader.exec_module(m)
        return m
    finally:
        if old is None:
            os.environ.pop('NRP_WATCHDOG_STATE', None)
        else:
            os.environ['NRP_WATCHDOG_STATE'] = old


class Unit(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='wdagents_'))
        (self.tmp / 'state').mkdir()
        self.w = load_module(self.tmp / 'state')
        w = self.w
        for name, kw in (('log', {}), ('digest', {}), ('push', {}), ('push_clear', {}), ('runner_ready', {'return_value': True})):
            p = patch.object(w, name, **kw)
            setattr(self, name, p.start())
            self.addCleanup(p.stop)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def cfg(self, obj):
        self.w.AGENTS_CFG.write_text(obj if isinstance(obj, str) else json.dumps(obj))

    # ---------------------------------------------------------------- commands and config
    def test_default_commands_are_what_they_were(self):
        w = self.w
        self.assertEqual(list(w.agent_cmd('triage', ['Bash(kubectl get:*)'])),
                         ['claude', '-p', '--model', 'haiku', '--max-turns', '12', '--max-budget-usd', '0.50', '--permission-mode',
                          'dontAsk', '--no-session-persistence', '--allowedTools', 'Bash(kubectl get:*)'])
        self.assertEqual(list(w.agent_cmd('task', ['A', 'B'], json_out=True, deny=['C'])),
                         ['claude', '-p', '--model', 'sonnet', '--max-turns', '60', '--max-budget-usd', '6.00', '--permission-mode',
                          'dontAsk', '--no-session-persistence', '--output-format', 'json', '--allowedTools', 'A', 'B',
                          '--disallowedTools', 'C'])
        self.assertEqual(w.agent_cmd('repair_auth', ['A'])[3:8], ['sonnet', '--max-turns', '45', '--max-budget-usd', '4.00'])
        self.assertEqual(w.agent_cfg()['followup_ladder'], ['triage', 'repair', 'repair'])
        self.assertEqual(w.agent_cfg()['runners'], ['claude'])

    def test_empty_allowlist_drops_the_flag(self):
        self.assertNotIn('--allowedTools', self.w.agent_cmd('triage', []))

    def test_agents_json_overrides_models_limits_and_ladder(self):
        self.cfg({'models': {'triage': {'claude': 'opus', 'codex': 'gpt-x'}}, 'limits': {'triage': {'turns': 5, 'timeout': 99}},
                  'followup_ladder': ['repair']})
        w = self.w
        cmd = w.agent_cmd('triage', ['A'])
        self.assertEqual(cmd[3], 'opus')
        self.assertEqual(cmd[5], '5')
        self.assertEqual(w.tier_settings('triage', 'codex')['model'], 'gpt-x')
        self.assertEqual(w.tier_settings('triage', 'claude')['timeout'], 99)
        self.assertEqual(w.tier_settings('repair', 'claude')['model'], 'sonnet')       # untouched tiers keep the defaults
        self.assertEqual(w.agent_cfg()['followup_ladder'], ['repair'])

    def test_invalid_config_falls_back_to_defaults_and_says_why(self):
        for bad in ('[1]', '{not json', {'runners': ['nope']}, {'runners': []}, {'runners': ['claude', 'claude']},
                    {'models': {'nope': {'claude': 'x'}}}, {'models': {'triage': {'claude': 'a b'}}}, {'followup_ladder': ['triage', 'x']},
                    {'followup_ladder': []}, {'limits': {'repair': {'turns': -1}}}, {'limits': {'repair': {'color': 1}}}, {'extra': 1}):
            self.cfg(bad)
            cfg, problem = self.w.load_agent_cfg()
            self.assertTrue(problem, bad)
            self.assertEqual(cfg, self.w.default_agent_cfg(), bad)

    # ---------------------------------------------------------------- usage-limit detection
    def test_limit_detection(self):
        w = self.w
        self.assertTrue(w.limit_hit(1, LIMIT_JSON, ''))                                           # claude --output-format json
        self.assertTrue(w.limit_hit(1, "You've hit your weekly limit · resets 2pm", ''))
        self.assertTrue(w.limit_hit(0, "You've hit your weekly limit · resets 2pm", ''))      # rc 0 but that is the whole answer
        self.assertTrue(w.limit_hit(1, '', 'ERROR: You\'ve hit your usage limit. Try again at 3:00 PM.'))   # codex
        self.assertFalse(w.limit_hit(0, 'ESCALATE: S3 rate limit exceeded on the bucket', ''))      # an agent REPORTING a rate limit
        self.assertFalse(w.limit_hit(0, 'DONE: outputs checked', ''))
        self.assertFalse(w.limit_hit(1, '', 'Traceback ... KeyError'))

    def test_reset_time(self):
        t = self.w.reset_time("You've hit your weekly limit · resets 2pm (America/Los_Angeles)")
        self.assertTrue(time.time() < t <= time.time() + 24 * 3600 + 120, t)
        self.assertIsNone(self.w.reset_time('no time here'))
        self.assertTrue(time.time() < self.w.reset_time('resets 9:30am') <= time.time() + 24 * 3600 + 120)

    # ---------------------------------------------------------------- fallback
    def run_dispatch(self, claude, codex):
        w = self.w
        calls = []

        def fake(name, result):
            def f(spec, prompt, cwd, timeout, env):
                calls.append(name)
                return result
            return f
        self.cfg({'runners': ['claude', 'codex']})
        with patch.dict(w.RUNNER_EXEC, {'claude': fake('claude', claude), 'codex': fake('codex', codex)}):
            res = w.dispatch_agent(w.agent_cmd('repair', ['A']).spec, 'p', self.tmp / 'cwd')
            res2 = w.dispatch_agent(w.agent_cmd('repair', ['A']).spec, 'p', self.tmp / 'cwd')
        return res, res2, calls

    def test_claude_limit_moves_work_to_codex_and_stays_there_until_reset(self):
        limit = ('limit', LIMIT_JSON, '', 1)
        res, res2, calls = self.run_dispatch(limit, ('ok', 'DONE: x', '', 0))
        self.assertEqual((res[0], res[1], res[2]), ('codex', 'ok', 'DONE: x'))
        self.assertEqual(calls, ['claude', 'codex', 'codex'], 'the second call skips the blocked runner')
        self.assertTrue(self.w.runner_blocked('claude'))
        until = self.w.read_json(self.w.RUNNER_STATE, {})['claude']['until']
        self.assertTrue(time.time() < until <= time.time() + 24 * 3600 + 120)
        self.push.assert_not_called()                                                     # a backup took over: nobody needs to know

    def test_every_runner_out_of_usage_waits_and_alerts_once(self):
        limit = ('limit', LIMIT_JSON, '', 1)
        res, res2, calls = self.run_dispatch(limit, limit)
        self.assertEqual(res[1], 'unavailable')
        self.assertTrue(self.w.is_unavailable(res[2]))
        self.assertIn('claude out of usage until', res[2])
        self.assertEqual(calls, ['claude', 'codex'], 'nothing is retried while both are blocked')
        self.assertEqual(self.push.call_count, 1)
        self.assertEqual(self.push.call_args.args[1], 'agents:unavailable')
        self.assertFalse(self.w.agents_available())

    def test_success_rearms_the_alert_and_unblock_clears_the_block(self):
        self.cfg({'runners': ['claude']})
        w = self.w
        w.block_runner('claude', LIMIT_JSON, '')
        self.assertFalse(w.agents_available())
        w.RUNNER_STATE.write_text(json.dumps({'claude': {'until': time.time() - 5}}))      # reset time passed: tried again
        self.assertTrue(w.agents_available())
        with patch.dict(w.RUNNER_EXEC, {'claude': lambda *a: ('ok', 'DONE', '', 0)}):
            w.dispatch_agent(w.agent_cmd('repair', ['A']).spec, 'p', self.tmp / 'cwd')
        self.push_clear.assert_called_with('agents:unavailable')

    def test_a_timeout_is_not_a_reason_to_start_the_next_runner(self):
        res, _, calls = self.run_dispatch(('timeout', '', '', None), ('ok', 'DONE', '', 0))
        self.assertEqual((res[0], res[1]), ('claude', 'timeout'))
        self.assertEqual(calls[0], 'claude')
        self.assertNotIn('codex', calls[:1])

    def test_run_agent_returns_the_unavailable_text(self):
        limit = ('limit', LIMIT_JSON, '', 1)
        w = self.w
        self.cfg({'runners': ['claude']})
        with patch.dict(w.RUNNER_EXEC, {'claude': lambda *a: limit}):
            out = w.run_agent(w.agent_cmd('triage', ['A']), 'p', self.tmp / 'cwd')
        self.assertTrue(w.is_unavailable(out))
        self.assertFalse(w.followup_solved(out))

    # ---------------------------------------------------------------- Codex translation
    def test_codex_rules_and_writable_dirs_follow_the_claude_allowlist(self):
        w = self.w
        allowed = ['Bash(kubectl -n ns get pod x:*)', 'Bash(nrp-watchdog list)', 'Bash(nrp-task:*)', 'Read(//a/b/**)',
                   'Edit(//home/me/state/approved/**)', 'Write(//home/me/plans/p/work/**)', 'Edit(//home/me/plans/p/work/**/.git/**)', 'Bash(unbalanced "quote:*)']
        rules = w.codex_rules(allowed).splitlines()
        self.assertIn('prefix_rule(pattern=["kubectl", "-n", "ns", "get", "pod", "x"], decision="allow")', rules)
        self.assertIn('prefix_rule(pattern=["nrp-watchdog", "list"], decision="allow")', rules)
        self.assertIn('prefix_rule(pattern=["nrp-task"], decision="allow")', rules)
        self.assertEqual(len(rules), 3, 'Read/Edit entries and a malformed pattern make no command rule')
        self.assertEqual(w.codex_writable(allowed), ['/home/me/state/approved', '/home/me/plans/p/work'])   # .git never writable

    # ---------------------------------------------------------------- the follow-up ladder
    def ladder(self, ladder, responses):
        self.cfg({'followup_ladder': ladder})
        with patch.object(self.w, 'run_agent', side_effect=responses) as agent:
            res = self.w.tiered_job_followup('job', {}, 'notes', ['Edit', 'Bash(kubectl apply:*)'], ['Read'])
        return res, [c.args[0].spec['tier'] for c in agent.call_args_list]

    def test_ladder_is_configurable(self):
        res, tiers = self.ladder(['repair'], ['ESCALATE: x'])
        self.assertEqual(tiers, ['repair'])
        self.assertTrue(res.startswith('STOPPED after 1 repair attempt'))
        res, tiers = self.ladder(['triage', 'repair', 'repair', 'repair'], ['ESCALATE: a', 'ESCALATE: b', 'ESCALATE: c', 'RESUBMITTED: j'])
        self.assertEqual(tiers, ['triage', 'repair', 'repair', 'repair'])
        self.assertTrue(self.w.followup_solved(res))
        res, tiers = self.ladder(['triage'], ['ESCALATE: a'])
        self.assertTrue(res.startswith('STOPPED after triage: '))

    def test_unavailable_stops_the_ladder_at_once(self):
        res, tiers = self.ladder(['triage', 'repair', 'repair'], [self.w.UNAVAILABLE + ': claude out of usage until Tue 14:01'])
        self.assertEqual(tiers, ['triage'])
        self.assertTrue(self.w.is_unavailable(res))

    # ---------------------------------------------------------------- legacy job registrations
    def check_jobs(self, followup_result, available):
        w = self.w
        notes = self.tmp / 'notes.md'
        notes.write_text('notes')
        rec = {'status': 'watching', 'added': 1, 'resume': str(notes)}
        st = {'jobs': {'job': rec}}
        with patch.object(w, 'job_state', return_value='ok'), patch.object(w, 'save'), patch.object(w, 'job_prompt', return_value='p'), \
             patch.object(w, 'agents_available', return_value=available), patch.object(w, 'notify') as notify, \
             patch.object(w, 'tiered_job_followup', return_value=followup_result) as follow, \
             patch.object(w, 'load', return_value={'jobs': {'job': rec}}), patch.object(w, 'SLOCK', self.tmp / 'lock'):
            w.check_jobs(SimpleNamespace(fake_finished='', dry_run=False), st)
        return rec, follow.call_count, notify.call_count

    def test_finished_job_waits_while_no_runner_has_usage(self):
        rec, follow, notify = self.check_jobs('DONE: x', available=False)
        self.assertEqual((rec['status'], follow, notify), ('watching', 0, 0))

    def test_runner_running_out_mid_ladder_requeues_the_job(self):
        rec, follow, notify = self.check_jobs(self.w.UNAVAILABLE + ': both out', available=True)
        self.assertEqual((rec['status'], follow, notify), ('watching', 1, 0))
        self.assertNotIn('handled', rec)
        self.push.assert_not_called()


FAKE_CLAUDE_LIMIT = '#!/bin/sh\ncat >/dev/null\necho "x" >> "$(dirname "$0")/../fake/claude_calls.log"\necho \'' + LIMIT_JSON + '\'\nexit 1\n'
FAKE_CODEX = r'''#!/usr/bin/env python3
"""Fake `codex exec`: same plan format as the fake claude; writes its final message to the -o file."""
import json, os, subprocess, sys
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fake"); prompt = sys.stdin.read()
args = sys.argv[1:]
open(d + "/codex_calls.log", "a").write(json.dumps({"args": args, "home_rules": open(os.environ["CODEX_HOME"] + "/rules/watchdog.rules").read()}) + "\n")
plan = json.load(open(d + "/agent_plan.json")) if os.path.exists(d + "/agent_plan.json") else []
step = plan.pop(0) if plan else {"cmds": [], "result": "STOPPED: no plan"}
json.dump(plan, open(d + "/agent_plan.json", "w"))
for c in step.get("cmds", []):
    subprocess.run(c[1], shell=True, capture_output=True, text=True) if c[0] == "sh" else subprocess.run(c, capture_output=True, text=True)
open(args[args.index("-o") + 1], "w").write(step.get("result", "done"))
'''


class EndToEnd(unittest.TestCase):
    """The real script, fake kubectl/aws and fake claude/codex binaries (the test_tasks harness)."""
    def setUp(self):
        self.h = TT.T('test_add_warns_on_existing_output')
        self.h.setUp()
        h = self.h
        self.addCleanup(h.tearDown)
        (h.tmp / 'codex-auth.json').write_text('{}')
        h.env['NRP_WATCHDOG_CODEX_AUTH'] = str(h.tmp / 'codex-auth.json')
        (h.bin / 'codex').write_text(FAKE_CODEX)
        os.chmod(h.bin / 'codex', 0o755)
        (h.state / 'agents.json').write_text(json.dumps({'runners': ['claude', 'codex'], 'models': {'task': {'codex': 'gpt-6.1-sol'}}}))
        self.man = None

    def fail_oom(self):
        h = self.h
        h.add()
        self.man = h.task()['stages'][0]['manifest']
        h.run_pass()
        h.set_job('t1-a', state='FAILED', term={'reason': 'OOMKilled', 'exitCode': 137})
        h.plan({'cmds': [['sh', "sed -i '' 's/512Mi/1Gi/g' %s" % self.man], ['nrp-task', 'submit', 't1-a', '--reason', 'OOM -> 1Gi'],
                         ['nrp-task', 'report', 'RESUBMITTED', 'OOM -> 1Gi']], 'result': 'RESUBMITTED: OOM -> 1Gi'})

    def use_limited_claude(self):
        (self.h.bin / 'claude').write_text(FAKE_CLAUDE_LIMIT)
        os.chmod(self.h.bin / 'claude', 0o755)

    def test_fix_agent_runs_on_codex_when_claude_is_out_of_usage(self):
        h = self.h
        self.use_limited_claude()
        self.fail_oom()
        h.run_pass()
        t = h.task()
        self.assertEqual(t['status'], 'retrying', t.get('reason'))
        self.assertEqual(t['attempts'][0]['cls'], 'resources')
        self.assertEqual(t['agent_runs'][-1]['runner'], 'codex')
        self.assertIn('1Gi', (h.fake / 'applied.log').read_text().splitlines()[-1])
        call = json.loads((h.fake / 'codex_calls.log').read_text().splitlines()[0])
        a = call['args']
        self.assertEqual(a[0], 'exec')
        self.assertEqual(a[a.index('-s') + 1], 'workspace-write')
        self.assertIn('approval_policy="never"', a)
        self.assertEqual(a[a.index('-m') + 1], 'gpt-6.1-sol')
        self.assertIn('prefix_rule(pattern=["nrp-task"], decision="allow")', call['home_rules'])
        self.assertEqual(h.pushes(), [], 'a backup runner took over: no alert')
        state = json.loads((h.state / 'runners.json').read_text())
        self.assertGreater(state['claude']['until'], time.time())
        # the next failure does not touch the blocked Claude again
        h.set_job('t1-a', state='FAILED', term={'reason': 'Error', 'exitCode': 1}, log='Traceback\nKeyError: "x"')
        h.plan({'cmds': [['nrp-task', 'report', 'STOPPED', 'give up']], 'result': 'STOPPED: give up'})
        h.run_pass()
        self.assertEqual((h.fake / 'claude_calls.log').read_text().count('x'), 1, 'claude was asked once, then skipped until its reset')

    def test_all_runners_out_of_usage_wait_without_using_a_retry_or_alerting_wrongly(self):
        h = self.h
        self.use_limited_claude()
        (h.bin / 'codex').write_text('#!/bin/sh\ncat >/dev/null\necho "ERROR: You\'ve hit your usage limit." >&2\nexit 1\n')
        os.chmod(h.bin / 'codex', 0o755)
        self.fail_oom()
        h.run_pass()
        t = h.task()
        self.assertIn(t['status'], ('retrying', 'running'), 'not NEEDS_OWNER: it is waiting, not stuck')
        self.assertEqual(t['attempts'], [], 'no retry was used up')
        self.assertIsNotNone(t.get('failure'))
        pushes = h.pushes()
        self.assertEqual(len(pushes), 1, pushes)
        self.assertIn('agents unavailable', pushes[0])
        h.run_pass()                                                  # still out of usage: waits again, still one alert
        self.assertEqual(len(h.pushes()), 1)
        self.assertEqual(h.task()['attempts'], [])
        rc, out, _ = h.wd('status')
        self.assertIn('out of usage', out)
        # usage returns: unblock, Claude answers again, the same failure is repaired and nothing was lost
        self.assertEqual(h.wd('agents', 'unblock', 'claude')[0], 0)
        self.assertEqual(h.wd('agents', 'unblock', 'codex')[0], 0)
        (h.bin / 'claude').write_text(TT.FAKE_CLAUDE)
        os.chmod(h.bin / 'claude', 0o755)
        h.run_pass()
        t = h.task()
        self.assertEqual(t['status'], 'retrying', t.get('reason'))
        self.assertEqual(t['attempts'][0]['cls'], 'resources')
        self.assertEqual(t['agent_runs'][-1]['runner'], 'claude')

    def test_agents_command_shows_state_and_a_bad_file_is_reported_not_fatal(self):
        h = self.h
        rc, out, _ = h.wd('agents')
        self.assertEqual(rc, 0)
        self.assertIn('runner 1: claude', out)
        self.assertIn('runner 2: codex', out)
        self.assertIn('job follow-up ladder: triage -> repair -> repair -> a person', out)
        (h.state / 'agents.json').write_text('{"runners": ["nope"]}')
        rc, out, _ = h.wd('agents')
        self.assertIn('PROBLEM: agents.json ignored', out)
        self.assertIn('runner 1: claude', out)


class Owner(unittest.TestCase):
    """Who the installation works for comes from config.json (env overrides it); nothing is hard-coded to one person."""
    def load(self, cfg, **env):
        tmp = Path(tempfile.mkdtemp(prefix='wdowner_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        if cfg is not None:
            (tmp / 'config.json').write_text(json.dumps(cfg))
        saved = {k: os.environ.pop(k, None) for k in ('NRP_WATCHDOG_USER_ANNOTATION', 'NRP_WATCHDOG_SLACK_USER', 'NRP_WATCHDOG_OWNER_LABEL', 'NRP_WATCHDOG_OWNER_NAME')}
        os.environ.update(env)
        try:
            return load_module(tmp)
        finally:
            for k in saved:
                os.environ.pop(k, None)
                if saved[k] is not None:
                    os.environ[k] = saved[k]

    def test_config_file_supplies_the_identity(self):
        m = self.load({'nrp_user_annotation': 'http://cilogon.org/serverE/users/1', 'slack_user_id': 'UABC', 'owner_label': 'jdoe'})
        self.assertEqual((m.USER_ANN, m.SLACK_USER, m.OWNER_LABEL), ('http://cilogon.org/serverE/users/1', 'UABC', 'jdoe'))

    def test_owner_name_defaults_to_the_label_and_can_be_set(self):
        self.assertEqual(self.load({'owner_label': 'jdoe'}).OWNER_NAME, 'jdoe')
        self.assertEqual(self.load({'owner_label': 'jdoe', 'owner_name': 'Jane'}).OWNER_NAME, 'Jane')
        self.assertEqual(self.load({'owner_name': 'Jane'}, NRP_WATCHDOG_OWNER_NAME='Alex').OWNER_NAME, 'Alex')

    def test_old_status_name_is_read_as_needs_owner(self):
        m = self.load({})
        d = m.TASKS / 'old'
        d.mkdir(parents=True)
        (d / 'task.json').write_text(json.dumps({'name': 'old', 'status': 'NEEDS_HUNTER'}))
        self.assertEqual(m.task_load('old')['status'], 'NEEDS_OWNER')

    def test_environment_overrides_the_file(self):
        m = self.load({'nrp_user_annotation': 'a', 'slack_user_id': 'U1'}, NRP_WATCHDOG_USER_ANNOTATION='b', NRP_WATCHDOG_SLACK_USER='U2')
        self.assertEqual((m.USER_ANN, m.SLACK_USER), ('b', 'U2'))

    def test_without_config_nothing_is_assumed(self):
        import getpass
        m = self.load(None)
        self.assertEqual((m.USER_ANN, m.SLACK_USER, m.OWNER_LABEL), ('', '', getpass.getuser()))
        with patch.object(m, 'log'):
            self.assertFalse(m.slack_dm('x'), 'no Slack user: no request is made')
            with self.assertRaises(RuntimeError):
                m.my_pods()


class Continuation(unittest.TestCase):
    """A task that nothing will act on when it finishes is flagged at registration and again in the digest."""
    def setUp(self):
        self.h = TT.T('test_add_warns_on_existing_output')
        self.h.setUp()
        self.addCleanup(self.h.tearDown)

    def test_add_warns_without_a_continuation_and_digest_only_is_the_explicit_opt_out(self):
        h = self.h
        rc, _, err = h.add()
        self.assertEqual(rc, 0, err)
        self.assertIn('no continuation', err)
        rc, _, err = h.add(name='t2', digest_only='an input check, nothing is pending after it')
        self.assertEqual(rc, 0, err)
        self.assertNotIn('no continuation', err)
        self.assertEqual(h.task('t2')['digest_only'], 'an input check, nothing is pending after it')
        rc, _, err = h.add(name='t3', followup='report the row count')
        self.assertNotIn('no continuation', err)
        rc, _, err = h.add(name='t4', digest_only='x')
        self.assertNotEqual(rc, 0)
        self.assertIn('digest_only', err)

    def test_refused_when_the_lab_requires_a_continuation(self):
        h = self.h
        h.env['NRP_WATCHDOG_REQUIRE_CONTINUATION'] = '1'
        rc, _, err = h.add()
        self.assertNotEqual(rc, 0)
        self.assertIn('no continuation', err)
        self.assertEqual(h.add(name='t2', digest_only='nothing is pending after this one')[0], 0)

    def test_finishing_without_a_continuation_lands_in_the_digest_as_such(self):
        h = self.h
        h.add(stages=[{"id": "a", "job": "t1-a", "manifest": h.manifest("t1-a"), "done_s3": ["s3://braingeneersdev/t/a.txt"]}])
        h.run_pass()
        h.set_job('t1-a', state='ok')
        (h.fake / 's3.json').write_text(json.dumps(['s3://braingeneersdev/t/a.txt']))
        h.run_pass()
        self.assertEqual(h.task()['status'], 'done')
        rc, out, _ = h.wd('digest')
        self.assertIn('nothing was set to act on it', out)
        h2 = self.h
        h2.add(name='t5', digest_only='terminal step, results are read by hand',
               stages=[{"id": "a", "job": "t5-a", "manifest": h2.manifest("t5-a"), "done_s3": ["s3://braingeneersdev/t/e.txt"]}])
        h2.run_pass()
        h2.set_job('t5-a', state='ok')
        (h2.fake / 's3.json').write_text(json.dumps(['s3://braingeneersdev/t/a.txt', 's3://braingeneersdev/t/e.txt']))
        h2.run_pass()
        rc, out, _ = h2.wd('digest')
        self.assertEqual(out.count('nothing was set to act on it'), 1, 'only the task that declared nothing')


if __name__ == '__main__':
    unittest.main()

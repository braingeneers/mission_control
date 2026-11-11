#!/usr/bin/env python3
"""Tests for the util waiver: a util fix agent may answer `UTIL_OK: evidence`, and the SCRIPT accepts it only for a lab-floor-only flag on a
Job that still runs, within the per-task cap. Offline: the fake kubectl / aws / claude of test_tasks.py (the fake agent runs the real
`nrp-task`), a scratch state dir, pushes routed to a banner log. Run: python3 tests/test_util_waiver.py"""
import json
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_agent_runners as TA  # noqa: E402  (load_module: the script as a module, for the pure functions)
import test_handoff as TH  # noqa: E402
import test_tasks as TT  # noqa: E402

EVIDENCE = ("Job t1-a runs and progresses: snr_1.bin finished 13:37 and snr_1p5.bin 13:47, the log shows streaming to S3. The flag is "
            "utilization only (I/O bound); deleting it would lose 4 h of write-once outputs.")
LAB_LINE = "LOW t1-a-abc age 218m, 10m mean: cpu 0.08/1.00 (8%) [lab 40% rule; NRP-exempt size] rule=lab"
NRP_LINE = "LOW t1-a-abc age 218m, 10m mean: cpu 0.08/1.00 (8%) [NRP violation] rule=nrp"


class Base(unittest.TestCase):
    def setUp(self):
        self.h = TT.T('test_add_warns_on_existing_output')
        self.h.setUp()
        self.addCleanup(self.h.tearDown)

    def started(self, name='t1', **kw):
        """Register the task and let a pass submit its Job (running in the fake cluster)."""
        rc, _, err = self.h.add(name=name, digest_only='nothing else is pending after this', **kw)
        self.assertEqual(rc, 0, err)
        self.h.run_pass()
        self.assertIn(name + '-a', self.h.cl())

    def edit(self, fn, n='t1'):
        p = self.h.state / 'tasks' / n / 'task.json'
        t = json.loads(p.read_text())
        fn(t)
        p.write_text(json.dumps(t))

    def inject(self, n='t1', cls='util', rule='lab', **extra):
        """A util failure as the pod strike-2 path records it, on the stage whose Job runs."""
        def f(t):
            s = t['stages'][0]
            s['state'] = 'failed'
            t['failure'] = dict({'stage': s['id'], 'job': s['job'], 'cls': cls, 'sig': 'util:cpu@512Mi', 'detail': 'pod %s-abc low: ' % s['job'] + LAB_LINE,
                                 'logs': None, 'ts': time.time(), 'pod': s['job'] + '-abc'}, **({'rule': rule} if rule else {}), **extra)
        self.edit(f, n)

    def agent(self, result=None, report='UTIL_OK', extra_cmds=()):
        cmds = [['nrp-task', 'report', report, 'util only, job healthy']] if report else []
        self.h.plan({'cmds': cmds + list(extra_cmds), 'result': result if result is not None else 'UTIL_OK: ' + EVIDENCE})

    def waivers(self, n='t1'):
        return self.h.task(n).get('util_waivers') or []

    def digest(self):
        return self.h.wd('digest')[1]


class Accept(Base):
    def test_accepted_waiver_keeps_the_task_running_without_a_message(self):
        h = self.h
        self.started()
        self.inject()
        self.agent()
        h.run_pass()
        t = h.task()
        self.assertEqual(t['status'], 'running', 'not NEEDS_OWNER')
        self.assertIsNone(t['failure'])
        self.assertEqual(t['stages'][0]['state'], 'running', 'the stage is back to running and watched')
        self.assertEqual(t['attempts'], [], 'no retry used')
        self.assertEqual(h.pushes(), [], 'no DM, no push')
        self.assertIn('t1-a', h.cl(), 'the Job was not deleted or resubmitted')
        self.assertEqual(len(self.waivers()), 1)
        w = self.waivers()[0]
        self.assertEqual(w['job'], 't1-a')
        self.assertEqual(w['pod'], 't1-a-abc')
        self.assertIn('snr_1.bin', w['reason'])
        self.assertLessEqual(len(w['reason']), 400)
        self.assertAlmostEqual(w['until'] - w['at'], 6 * 3600, delta=2)
        self.assertTrue(any('util waiver 1 of 3' in e for e in t['events']))
        d = self.digest()
        self.assertRegex(d, r'util-waived\s+\[t1')
        self.assertIn('waiver 1 of 3', d)
        self.assertNotIn('needs you', d.lower().split('events:')[-1])
        rc, out, _ = h.wd('task', 'show', 't1')
        self.assertEqual(rc, 0, out)
        self.assertIn('util waivers: 1 of 3 used', out)
        self.assertIn('util waiver ACTIVE t1-a until', out)
        self.assertIn('snr_1.bin', out)

    def test_answer_text_alone_counts_without_an_nrp_task_report(self):
        h = self.h
        self.started()
        self.inject()
        self.agent(report=None)
        h.run_pass()
        self.assertEqual(h.task()['status'], 'running')
        self.assertEqual(len(self.waivers()), 1)
        self.assertEqual(h.pushes(), [])

    def test_report_status_alone_counts_with_its_line_as_the_evidence(self):
        h = self.h
        self.started()
        self.inject()
        self.agent(result='done, see report')
        h.run_pass()
        self.assertEqual(len(self.waivers()), 1)
        self.assertEqual(self.waivers()[0]['reason'], 'util only, job healthy')

    def test_stopped_report_stays_a_stop_even_with_a_util_ok_line(self):
        h = self.h
        self.started()
        self.inject()
        self.agent(report='STOPPED')
        h.run_pass()
        self.assertEqual(h.task()['status'], 'NEEDS_OWNER')
        self.assertEqual(self.waivers(), [])
        self.assertNotIn('waiver refused', h.task()['reason'])

    def test_waiver_is_a_fix_log_entry_when_a_handoff_exists(self):
        h = self.h
        f = h.tmp / 'handoff_src.md'
        f.write_text(TH.handoff_text())
        self.started(handoff=str(f))
        self.inject()
        self.agent(result='UTIL_OK: ' + EVIDENCE + '\nHANDOFF_ENTRY:\nChecked outputs; leave the Job alone.')
        h.run_pass()
        fl = TH.sections((h.state / 'tasks/t1/handoff.md').read_text())['Fix log']
        self.assertIn('Checked outputs; leave the Job alone.', fl)
        self.assertIn('Util flag waived until', fl)
        self.assertIn('| watchdog | util waiver 1 of 3', fl)
        self.assertNotIn('HANDOFF_ENTRY', self.waivers()[0]['reason'], 'the evidence stops at the handoff block')


class Suppression(Base):
    def module(self):
        m = TA.load_module(self.h.state)
        for name in ('log', 'digest', 'push'):
            p = patch.object(m, name)
            p.start()
            self.addCleanup(p.stop)
        return m

    def flag(self, m, line):
        st = {'strikes': {}, 'jobs': {}, 'pods': {}}
        m.task_pod_flag(st, 't1', 'a', 't1-a-abc', 'LOW', line)
        return st

    def notes(self):
        return self.h.task().get('util') or []

    def test_lab_flag_is_recorded_without_a_waiver_and_silent_with_one(self):
        h = self.h
        self.started()
        m = self.module()
        self.flag(m, LAB_LINE)
        self.assertEqual(len(self.notes()), 1)
        self.assertIn('[lab]', self.notes()[0])
        self.inject()
        self.agent()
        h.run_pass()
        self.assertEqual(len(self.waivers()), 1)
        self.flag(m, LAB_LINE)
        self.assertEqual(len(self.notes()), 1, 'suppressed while the waiver holds')

    def test_nrp_and_gpu_flags_are_never_suppressed(self):
        h = self.h
        self.started()
        self.inject()
        self.agent()
        h.run_pass()
        m = self.module()
        st = self.flag(m, NRP_LINE)
        self.assertEqual(len(self.notes()), 1, 'an NRP-band flag is still processed under a waiver')
        self.assertIn('[nrp]', self.notes()[0])
        self.assertIn('t1-a-abc', st['strikes'])
        self.flag(m, "LOW t1-a-abc age 218m, 10m mean: gpu 5% (gpu 0, A100) [NRP violation] rule=gpu")
        self.assertEqual(len(self.notes()), 2)

    def test_waiver_ends_with_its_time_or_with_the_job(self):
        h = self.h
        self.started()
        self.inject()
        self.agent()
        h.run_pass()
        m = self.module()
        t = h.task()
        self.assertTrue(m.active_waiver(t, 'a'))
        self.edit(lambda t: t['util_waivers'][0].update(until=time.time() - 1))
        self.assertIsNone(m.active_waiver(h.task(), 'a'), 'ran out')
        self.flag(m, LAB_LINE)
        self.assertEqual(len(self.notes()), 1, 'recorded again after it ran out')
        self.edit(lambda t: t['util_waivers'][0].update(until=time.time() + 3600))
        self.assertTrue(m.active_waiver(h.task(), 'a'))
        self.edit(lambda t: t['stages'][0].update(submitted=t['stages'][0]['submitted'] + 5))     # resubmitted: a different Job
        self.assertIsNone(m.active_waiver(h.task(), 'a'))
        self.edit(lambda t: t['stages'][0].update(submitted=t['util_waivers'][0]['submitted'], state='done'))
        self.assertIsNone(m.active_waiver(h.task(), 'a'), 'the Job ended')

    def test_strike_two_failure_records_the_rule_and_pod(self):
        h = self.h
        self.started()
        m = self.module()
        st = {'strikes': {'t1-a-abc': {'n': 1, 't': time.time() - 3600, 'owner': 't1'}}, 'jobs': {}, 'pods': {}}
        m.task_pod_flag(st, 't1', 'a', 't1-a-abc', 'LOW', NRP_LINE)
        f = h.task()['failure']
        self.assertEqual((f['cls'], f['rule'], f['pod']), ('util', 'nrp', 't1-a-abc'))
        self.edit(lambda t: t.update(failure=None))
        # an older nrp-util-check has no rule token: the tag says it
        self.assertEqual(m.flag_rule('LOW p age 1m, 10m mean: cpu 1/2 (5%) [NRP violation]'), 'nrp')
        self.assertEqual(m.flag_rule('LOW p age 1m, 10m mean: gpu 5% [lab 40% rule]'), 'gpu')
        self.assertEqual(m.flag_rule('LOW p age 1m, 10m mean: mem 1/2Gi (5%) [lab 40% rule]'), 'lab')
        self.assertEqual(m.flag_rule('LOW p age 1m, 10m mean: mem 1/2Gi (5%) [lab 40% rule; NRP-exempt size]'), 'lab')
        self.assertEqual(m.flag_rule('something else'), 'unknown')
        self.assertEqual(m.flag_rule(LAB_LINE), 'lab')


class ExpiryAndCap(Base):
    def test_expired_waiver_then_reflag_goes_through_the_ladder_until_the_cap_then_stops(self):
        h = self.h
        self.started()
        for k in (1, 2, 3):
            self.inject()
            self.agent()
            h.run_pass()
            self.assertEqual(h.task()['status'], 'running', 'waiver %d' % k)
            self.assertEqual(len(self.waivers()), k)
            self.edit(lambda t: [w.update(until=time.time() - 10) for w in t['util_waivers']])     # six hours pass
        self.assertEqual(h.pushes(), [])
        self.assertEqual(len(h.prompts()), 3, 'each re-flag started a fresh fix agent')
        self.assertIn('flag rule lab', h.prompts()[0].read_text())
        self.inject()
        self.agent()
        h.run_pass()
        t = h.task()
        self.assertEqual(t['status'], 'NEEDS_OWNER')
        self.assertEqual(len(self.waivers()), 3)
        self.assertIn('used its 3 util waiver', t['reason'])
        self.assertEqual(len(h.pushes()), 1, 'only the escalation messages the owner')
        self.assertEqual(self.digest().count('util-waived'), 3 + 1, 'three lines, plus the summary count in the Events header')

    def test_agent_prompt_says_the_cap_and_the_hours(self):
        h = self.h
        h.env['NRP_WATCHDOG_UTIL_WAIVER_MAX'] = '2'
        h.env['NRP_WATCHDOG_UTIL_WAIVER_HOURS'] = '1.5'
        self.started()
        self.inject()
        self.agent(report='STOPPED')
        h.run_pass()
        text = h.prompts()[0].read_text()
        self.assertIn('at most 2 times per task', text)
        self.assertIn('for 1.5 hours', text)
        self.assertIn('UTIL_OK', text)


class Refused(Base):
    def refused(self, why, **kw):
        h = self.h
        self.agent(**kw)
        h.run_pass()
        t = h.task()
        self.assertEqual(t['status'], 'NEEDS_OWNER', 'behaves exactly as today: a STOP to the owner')
        self.assertEqual(self.waivers(), [])
        self.assertEqual(len(h.pushes()), 1)
        self.assertIn('fix agent did not resubmit', t['reason'])
        self.assertIn('util waiver refused', t['reason'])
        self.assertIn(why, t['reason'])
        self.assertTrue(any('util waiver refused' in e and why in e for e in t['events']), t['events'])
        self.assertNotIn('util-waived', self.digest())
        return t

    def test_refused_when_the_pod_is_outside_an_nrp_band(self):
        self.started()
        self.inject(rule='nrp')
        t = self.refused('rule nrp')
        self.assertEqual(t['stages'][0]['state'], 'failed')

    def test_refused_for_a_gpu_flag(self):
        self.started()
        self.inject(rule='gpu')
        self.refused('rule gpu')

    def test_refused_for_a_gpu_stage_even_with_a_lab_flag(self):
        self.started()
        self.edit(lambda t: t['stages'][0].update(gpu_ok_until='2099-01-01'))
        self.inject()
        self.refused('GPU')

    def test_refused_when_another_pod_was_flagged_outside_the_bands_recently(self):
        self.started()
        self.edit(lambda t: t.update(util=['%s [nrp] LOW t1-a-xyz ... [NRP violation] rule=nrp -> resize' % time.strftime('%Y-%m-%dT%H:%M:%S')]))
        self.inject()
        self.refused('another flag on this task')

    def test_old_nrp_note_does_not_block(self):
        h = self.h
        self.started()
        self.edit(lambda t: t.update(util=['2020-01-01T00:00:00 [nrp] LOW ... -> resize']))
        self.inject()
        self.agent()
        h.run_pass()
        self.assertEqual(len(self.waivers()), 1)

    def test_refused_when_the_job_is_not_running(self):
        h = self.h
        self.started()
        self.inject()
        h.set_job('t1-a', state='pending')
        self.refused('is pending now')

    def test_refused_when_the_job_is_gone(self):
        h = self.h
        self.started()
        self.inject()
        c = json.loads((h.fake / 'cluster.json').read_text())
        c['jobs'].pop('t1-a')
        (h.fake / 'cluster.json').write_text(json.dumps(c))
        self.refused('is missing now')

    def test_refused_when_the_job_already_failed(self):
        h = self.h
        self.started()
        self.inject()
        h.set_job('t1-a', state='FAILED', term={'reason': 'Error', 'exitCode': 1})
        self.refused('is FAILED now')

    def test_refused_for_a_non_util_failure_class(self):
        self.started()
        self.inject(cls='code')
        self.refused('class is code, not util')

    def test_refused_without_evidence(self):
        self.started()
        self.inject()
        self.refused('no evidence', result='UTIL_OK:', report=None)

    def test_refused_for_a_failure_written_before_waivers_existed(self):
        self.started()
        self.inject(rule=None)
        t = self.refused('records no flag rule')
        self.assertNotIn('rule', t['failure'])

    def test_answer_without_util_ok_is_the_old_stop(self):
        h = self.h
        self.started()
        self.inject()
        self.agent(report='STOPPED', result='STOPPED: the Job looks healthy but I did not touch it.')
        h.run_pass()
        t = h.task()
        self.assertEqual(t['status'], 'NEEDS_OWNER')
        self.assertTrue(t['reason'].startswith('fix agent did not resubmit: util only, job healthy'), t['reason'])   # then the no-webhook fallback note
        self.assertNotIn('waiver', t['reason'])
        self.assertEqual(self.waivers(), [])
        self.assertEqual(len(h.pushes()), 1)

    def test_util_ok_in_an_ordinary_resubmit_changes_nothing(self):
        h = self.h
        self.started()
        self.inject()
        man = h.task()['stages'][0]['manifest']
        self.agent(report='RESUBMITTED', result='RESUBMITTED: resized',
                   extra_cmds=[['sh', "sed -i '' 's/512Mi/1Gi/g' %s" % man], ['nrp-task', 'submit', 't1-a', '--reason', 'oversized -> 1Gi']])
        h.run_pass()
        self.assertEqual(h.task()['attempts'][0]['cls'], 'util')
        self.assertEqual(self.waivers(), [])


class Settings(Base):
    def test_hours_and_cap_come_from_the_environment(self):
        h = self.h
        h.env['NRP_WATCHDOG_UTIL_WAIVER_HOURS'] = '2'
        self.started()
        self.inject()
        self.agent()
        h.run_pass()
        w = self.waivers()[0]
        self.assertAlmostEqual(w['until'] - w['at'], 2 * 3600, delta=2)

    def test_cap_zero_turns_waivers_off(self):
        h = self.h
        h.env['NRP_WATCHDOG_UTIL_WAIVER_MAX'] = '0'
        self.started()
        self.inject()
        self.agent()
        h.run_pass()
        self.assertEqual(h.task()['status'], 'NEEDS_OWNER')
        self.assertIn('used its 0 util waiver', h.task()['reason'])

    def test_defaults_config_file_environment_and_bad_values(self):
        tmp = self.h.tmp / 'cfgstate'
        tmp.mkdir()
        m = TA.load_module(tmp)
        self.assertEqual((m.util_waiver_max(), m.util_waiver_hours()), (3, 6.0))
        (tmp / 'config.json').write_text(json.dumps({'util_waiver_max': 5, 'util_waiver_hours': 12}))
        m = TA.load_module(tmp)
        self.assertEqual((m.util_waiver_max(), m.util_waiver_hours()), (5, 12.0))
        with patch.dict('os.environ', {'NRP_WATCHDOG_UTIL_WAIVER_MAX': '1', 'NRP_WATCHDOG_UTIL_WAIVER_HOURS': '0.5'}):
            self.assertEqual((m.util_waiver_max(), m.util_waiver_hours()), (1, 0.5), 'the environment beats the file')
        with patch.dict('os.environ', {'NRP_WATCHDOG_UTIL_WAIVER_MAX': 'many', 'NRP_WATCHDOG_UTIL_WAIVER_HOURS': '-4'}):
            self.assertEqual((m.util_waiver_max(), m.util_waiver_hours()), (3, 6.0), 'bad values fall back to the defaults')


class Pure(unittest.TestCase):
    def setUp(self):
        import shutil
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix='wdwaiver_'))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.m = TA.load_module(self.tmp)

    def test_util_ok_extract(self):
        x = self.m.util_ok_extract
        self.assertIsNone(x('STOPPED: nothing to see'))
        self.assertEqual(x('UTIL_OK: the Job runs.'), 'the Job runs.')
        self.assertEqual(x('RESUBMITTED: no\n\n**UTIL_OK:** Job runs\nand writes outputs.\n\nHANDOFF_ENTRY:\ntried x'), 'Job runs and writes outputs.')
        self.assertEqual(x('UTIL_OK: first\nUTIL_OK: second one'), 'second one', 'the last block wins')
        self.assertEqual(x('UTIL_OK: evidence\nHANDOFF_ENTRY:\nUTIL_OK is fine'), 'evidence')
        self.assertEqual(len(x('UTIL_OK: ' + 'a' * 900)), 400)
        self.assertEqual(x('UTIL_OK:'), '')


if __name__ == '__main__':
    unittest.main()

"""Account RED ALERT (NRP's dry-run admission verdict) and NRP-floor utilization reviews. Fake kubectl / nrp-util-check, scratch state."""
import argparse
import json
from types import SimpleNamespace
from unittest.mock import patch

from test_blocked_submit import LOW_CPU, REFUSAL, USER, pod
from test_escalation_costs import monitor, task  # noqa: F401  (fixture)

A = argparse.Namespace(dry_run=False)


class Nrp:
    """Fake kubectl (admission probe + get pods) and nrp-util-check; a clock; a switch for NRP's verdict."""
    def __init__(self, m):
        self.m, self.deny, self.clock, self.probes, self.applies = m, True, [10000.0], 0, 0
        self.pods = [pod('work-17-abc', USER, 'work-17'), pod('stray-xyz', None, 'stray-job', sa='someone-sa'), pod('fine-1', USER, 'other')]
        self.flags = {'work-17-abc': LOW_CPU, 'stray-xyz': LOW_CPU}
        m.USER_ANN = USER
        alpha, beta = task(m, 'alpha'), task(m, 'beta')
        m.task_txn('alpha', lambda t: t['stages'][0].update(state='running') or t.update(failure=None))
        m.task_txn('beta', lambda t: t['stages'][0].update(state='pending', job='beta-1', after=[]) or t.update(failure=None))
        self.stack = [patch.object(m, 'kubectl', self.kubectl), patch.object(m.subprocess, 'run', self.util),
                      patch.object(m, 'apply_manifest', self.apply), patch.object(m, 'job_state', return_value='missing'),
                      patch.object(m, 'manifest_check', return_value=[]), patch.object(m, 'gpu_expired', return_value=None),
                      patch.object(m, 'bad_nodes', return_value={}), patch.object(m, 'now', lambda: self.clock[0]),
                      patch.object(m, 'observe_task'), patch.object(m, 'report_long_pending'), patch.object(m, 'process_util_event'),
                      patch.object(m, 'push')]

    def kubectl(self, *args, **kw):
        if 'create' in args:
            assert '--dry-run=server' in args
            self.probes += 1
            body = json.loads(open(args[args.index('-f') + 1]).read())['spec']['template']['spec']['containers'][0]['resources']
            assert body['requests'] == body['limits']
            return SimpleNamespace(returncode=1, stdout='', stderr=REFUSAL) if self.deny else \
                SimpleNamespace(returncode=0, stdout='job.batch/x created (server dry run)', stderr='')
        assert args[2:4] == ('get', 'pods'), args
        return SimpleNamespace(returncode=0, stdout=json.dumps({'items': self.pods}), stderr='')

    def util(self, cmd, **kw):
        assert cmd[0] == 'nrp-util-check', cmd
        lines = [f.format(n) for n, f in self.flags.items() if n in cmd]
        return SimpleNamespace(returncode=4 if lines else 0, stdout='\n'.join(lines), stderr='')

    def apply(self, ns, path):
        self.applies += 1
        return 'ok'

    def __enter__(self):
        self.mocks = [p.start() for p in self.stack]
        self.push = self.mocks[-1]
        return self

    def __exit__(self, *exc):
        for p in reversed(self.stack):
            p.stop()

    def pass_(self, minutes=11):
        self.clock[0] += minutes * 60
        self.m.process_red_alert(A, {})
        self.m.advance_task('beta', {}, A)

    def wakes(self, n):
        return [e for e in self.m.task_load(n).get('webhook_outbox') or [] if e['event_type'] == 'red_alert']


def test_probe_denial_holds_every_submit_wakes_owner_once_reports_unknown(monitor):
    with Nrp(monitor) as x:
        x.pass_()
        cur = monitor.red_alert()
        assert cur and 'utilization is too low' in cur['refusal']
        assert x.applies == 0                                       # beta's ready stage was held, not applied
        beta = monitor.task_load('beta')
        assert beta['status'] == 'blocked' and beta['pending']['hold'] == 'red-alert'
        wakes = x.wakes('alpha')
        assert len(wakes) == 1                                      # work-17-abc belongs to alpha (its stage's Job)
        assert 'stray-xyz' in wakes[0]['summary'] and 'not mine' in wakes[0]['summary']
        assert 'working-set peak' in wakes[0]['summary'] and 'no exceptions' in wakes[0]['summary']
        assert x.wakes('beta') == []                                # beta owns no low pod
        assert x.push.call_count == 1
        msg, key = x.push.call_args[0]
        assert 'NRP RED ALERT' in msg and 'stray-xyz' in msg and 'alpha' in msg
        text = monitor.wake_text(monitor.task_load('alpha'), wakes[0], 't3-cli')
        assert text.startswith('[NRP monitor RED ALERT') and 't3 thread send' in text

        x.pass_()                                                   # still denied: no second wake, no second push, still held
        assert len(x.wakes('alpha')) == 1 and x.push.call_count == 1 and x.applies == 0

        x.deny = False
        x.pass_(minutes=3)                                          # probe not due yet: the alert stays
        assert monitor.red_alert() and x.applies == 0
        x.pass_()                                                   # NRP's dry-run accepts: cleared, the held submit goes
        assert monitor.red_alert() == {} and x.applies == 1
        assert monitor.task_load('beta')['status'] == 'running'


def test_real_submit_refusal_enters_red_alert(monitor):
    with Nrp(monitor) as x:
        x.deny = False
        x.stack[2].stop()                                           # real apply_manifest, kubectl refuses the dry-run apply
        with patch.object(monitor, 'kubectl', lambda *a, **k: SimpleNamespace(returncode=1, stdout='', stderr=REFUSAL)):
            assert monitor.apply_manifest('test', '/dev/null') == 'blocked'
        x.stack[2].start()
        assert monitor.red_alert()['source'] == 'submit refused'
        ok, msg = monitor.do_submit('beta', 'a', 'stage ready', 'monitor')
        assert ok and msg.startswith('HELD') and x.applies == 0


def util_task(m, mode, rule):
    t = task(m, 'watcher')
    line = 'LOW work-17-abc age 2h, 10m mean: mem 1.00/16.00 (6%%) %s rule=%s' % (
        '[NRP violation]' if rule == 'nrp' else '[lab 40% rule]', rule)

    def f(t):
        t.update(failure=None, mode=mode)
        t['stages'][0].update(state='running', submitted=500)
        t['util_event'] = {'stage': 'a', 'job': 'work-17', 'cls': 'util', 'sig': 'util:x', 'detail': line, 'ts': 600,
                           'evidence': {'peaks_gi': {'work-17-abc': 6.1}, 'true_peak_gi': 7.58}, 'rule': rule, 'pod': 'work-17-abc'}
    m.task_txn('watcher', f)
    return t


def review(m, agent):
    with patch.object(m, 'run_task_agent', agent), patch.object(m, 'task_prompt', return_value='FIX'), \
            patch.object(m, 'triage_prompt', return_value='JUDGE'):
        m.process_util_event('watcher', A)
    t = m.task_load('watcher')
    assert 'util_event' not in t
    return [e for e in t.get('webhook_outbox') or [] if e['event_type'] == 'util_nrp']


def test_nrp_floor_watch_only_wakes_chat_not_digest(monitor):
    util_task(monitor, 'watch', 'nrp')
    wakes = review(monitor, lambda *a, **k: (_ for _ in ()).throw(AssertionError('no agent for a watch-only NRP review')))
    assert len(wakes) == 1 and '"No change" is not an allowed answer' in wakes[0]['summary']


def test_nrp_floor_fixer_no_change_still_wakes_chat(monitor):
    util_task(monitor, 'auto', 'nrp')
    prompts = []
    wakes = review(monitor, lambda n, prompt, a, **k: (prompts.append(prompt), ('DONE: no change needed', None))[1])
    assert len(prompts) == 1 and 'working-set peak' in prompts[0] and 'memory.peak' in prompts[0]
    assert 'NOT an allowed outcome' in prompts[0]
    assert len(wakes) == 1


def test_nrp_floor_fixer_resubmit_needs_no_wake(monitor):
    util_task(monitor, 'auto', 'nrp')

    def fixer(n, prompt, a, **k):
        monitor.task_txn(n, lambda t: t['stages'][0].update(submitted=900))     # the fixer resized and resubmitted
        return 'DONE: resized to 10Gi and resubmitted', None
    assert review(monitor, fixer) == []


def test_lab_floor_watch_only_keeps_digest(monitor):
    util_task(monitor, 'watch', 'lab')
    assert review(monitor, lambda *a, **k: ('ESCALATE: low', None)) == []

"""Explicit shadow switch: isolated writes, no external actions, fail-closed IO.

The normal pass runs on a disposable copy (dry_run=False), so its decisions and
local transitions remain observable. Suppressed actions never claim real success.
"""
import contextlib
from datetime import datetime
import traceback
import fcntl
import importlib
import io
import json
import os
from pathlib import Path
import runpy
import re
import subprocess
import sys
import tempfile
import urllib.request
from urllib.parse import urlsplit

_ACTIVE = None
_TASK = None
_STAGE = None


def record(would_do, **details):
    if _ACTIVE is not None:
        with (_ACTIVE / 'shadow-actions.jsonl').open('a') as stream:
            stream.write(json.dumps({'would_do': would_do, 'task': _TASK, 'stage': _STAGE, 'time': datetime.now().isoformat(), **details}) + '\n')


def _audit(event, args):
    if _ACTIVE is None:
        return
    paths = []
    if event == 'open':
        path, mode, flags = args
        if isinstance(path, int):
            return
        if (mode and any(c in mode for c in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            paths = [path]
    elif event in ('os.remove', 'os.rmdir', 'os.mkdir', 'os.chmod', 'os.utime', 'os.truncate'):
        paths = [(args[0], args[2] if event == "os.chmod" else args[1] if event in ("os.remove", "os.rmdir") else args[2] if event == "os.mkdir" else -1)]
    elif event in ('os.rename', 'os.link', 'os.symlink'):
        paths = [(args[0], args[2] if len(args) > 2 else -1), (args[1], args[3] if len(args) > 3 else -1)]
    elif event in ('os.system', 'os.exec', 'os.posix_spawn'):
        record('blocked process primitive ' + event)
        raise PermissionError('shadow forbids process primitive')
    elif event == 'subprocess.Popen' and not _read_command(args[1]):
        record('blocked raw subprocess ' + Path(str(args[0])).name)
        raise PermissionError('shadow subprocess allowlist')
    for item in paths:
        path, dir_fd = item if isinstance(item, tuple) else (item, -1)
        path = Path(os.fsdecode(path))
        if not path.is_absolute() and dir_fd not in (None, -1):
            # shutil.rmtree uses relative unlink/rmdir with an open directory FD.
            # Resolve that FD, not cwd; otherwise legitimate isolated cleanup is blocked.
            if sys.platform == 'darwin':
                parent = os.fsdecode(fcntl.fcntl(dir_fd, 50, bytes(1024)).split(b'\0', 1)[0])
            else:
                parent = os.readlink('/proc/self/fd/%d' % dir_fd)
            path = Path(parent) / path
        if not path.resolve().is_relative_to(_ACTIVE):
            stack = traceback.extract_stack(limit=8)
            record('filesystem write outside isolated state', route=event,
                   path_kind='external ' + (path.suffix or 'directory'),
                   target=str(path), caller=[f'{Path(f.filename).name}:{f.lineno}:{f.name}' for f in stack[:-1]])
            raise PermissionError('shadow forbids write outside isolated state')


sys.addaudithook(_audit)


def _kubectl_verb(argv):
    args = list(argv[1:])
    if args[:1] == ["--context"]:
        args = args[2:]
    # Only the audited wrapper shape; unknown flags before the verb fail closed.
    if args[:1] in (['-n'], ['--namespace']):
        args = args[2:]
    return args[0] if args else ''


def _aws_op(argv):
    args = list(argv[1:])
    if args[:1] == ["--context"]:
        args = args[2:]
    # Only the monitor's own aws_cmd shape: global --endpoint-url/--profile, then the operation.
    while args[:1] in (['--endpoint-url'], ['--profile']):
        args = args[2:]
    return tuple(args[:2])


def _read_command(argv):
    if not isinstance(argv, (list, tuple)) or not argv:
        return False
    name = Path(str(argv[0])).name
    if name == 'kubectl':
        return _kubectl_verb(argv) in ('get', 'describe', 'logs', 'top')
    # S3 success markers drive most stage decisions; HEAD/list are read-only.
    return name == 'aws' and _aws_op(argv) in (('s3api', 'head-object'), ('s3', 'ls'))


# Semantic boundaries, before any agent scratch setup / outbound IO. Every row
# is exercised by tests. Values deliberately avoid pretending an action happened.
GATES = {
    'agents.dispatch_agent': lambda *a, **k: importlib.import_module('.agents', __package__).Result(None, 'unavailable', 'shadow: agent skipped', '', None),
    'agents.exec_backend': lambda *a, **k: ('unavailable', 'shadow: agent skipped', '', None),
    'agents.run_agent': lambda *a, **k: 'shadow: agent skipped',
    'notify.slack_dm': lambda *a, **k: False,
    'notify.claude_push': lambda *a, **k: False,
    'notify.banner': lambda *a, **k: None,
    'wake.handoff_write': lambda *a, **k: None,
    'notify.push': lambda *a, **k: False,
    'wake.wake_session': lambda *a, **k: None,
    'wake.wake_t3': lambda *a, **k: None,
    'wake.process_task_webhooks': lambda *a, **k: None,
    'red_alert.red_probe': lambda *a, **k: ('error', 'shadow: admission create skipped'),
    's3.incluster_job': lambda *a, **k: None,
    'task.pass_.run_postcheck': lambda *a, **k: {'ok': False, 'output': 'shadow: postcheck unknown'},
}


@contextlib.contextmanager
def isolated_pass():
    from . import state
    global _ACTIVE
    base = Path('/private/tmp/claude-501/nrp-shadow').resolve()
    dest = state.STATE.resolve()
    if not dest.is_relative_to(base) or dest == base or dest.is_symlink():
        raise ValueError('shadow requires an isolated NRP_MONITOR_STATE below ' + str(base))
    if _ACTIVE is not None:
        raise RuntimeError('nested shadow pass')
    dest.mkdir(parents=True, exist_ok=True)
    old_temp = tempfile.tempdir
    tempfile.tempdir = str(dest)
    patches = []
    original_run = subprocess.run
    original_open = urllib.request.OpenerDirector.open

    def patch(obj, name, value):
        patches.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def run(argv, *args, **kwargs):
        if _read_command(argv) and not kwargs.get('shell'):
            return original_run(argv, *args, **kwargs)
        label = Path(str(argv[0])).name if isinstance(argv, (tuple, list)) and argv else 'shell'
        if label == 'kubectl':
            # Record and report failure (never success) so the rest of the pass is still compared.
            record('kubectl ' + _kubectl_verb(argv))
            return subprocess.CompletedProcess(argv, 125, '', 'shadow: kubectl %s skipped' % _kubectl_verb(argv))
        if label == 'nrp-util-check':
            # Execute the reviewed source here, under these same IO gates; never
            # spawn the installed helper, whose GPU fallback uses kubectl exec.
            buf, err = io.StringIO(), io.StringIO()
            old_argv = sys.argv
            sys.argv = list(argv)
            try:
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
                    try:
                        runpy.run_path(str(Path(__file__).resolve().parent.parent / 'nrp-util-check'), run_name='__main__')
                        rc = 0
                    except SystemExit as e:
                        rc = e.code or 0
                    except Exception as e:
                        rc = 2
                        err.write(type(e).__name__ + ': ' + str(e))
            finally:
                sys.argv = old_argv
            return subprocess.CompletedProcess(argv, rc, buf.getvalue(), err.getvalue())
        record('subprocess ' + label)
        return subprocess.CompletedProcess(argv, 125, '', 'shadow: subprocess skipped')

    def http(opener, fullurl, data=None, timeout=None):
        url = fullurl.full_url if isinstance(fullurl, urllib.request.Request) else fullurl
        method = fullurl.get_method() if isinstance(fullurl, urllib.request.Request) else 'GET'
        allowed = urlsplit(state.THANOS_URL)
        target = urlsplit(url)
        if method != 'GET' or data is not None or (target.scheme, target.netloc, target.path) != (allowed.scheme, allowed.netloc, allowed.path):
            record('HTTP outside Thanos GET')
            raise PermissionError('shadow HTTP allowlist')
        return original_open(opener, fullurl, data, timeout)

    try:
        for route, result in GATES.items():
            mod, name = route.rsplit('.', 1)
            obj = importlib.import_module('.' + mod, __package__)
            def skip(*args, _route=route, _result=result, **kwargs):
                record(_route)
                return _result(*args, **kwargs)
            patch(obj, name, skip)
        # Stored executor aliases must follow their defining function's gate.
        # Ordered observations share the action journal so suppression boundaries are exact.
        original_log = state.log
        def log(message):
            match = re.match(r'task ([^:]+): ', message)
            record('observation', message=message, task=match[1] if match else _TASK)
            return original_log(message)
        patch(state, 'log', log)
        from . import stage_jobs, task_agents, agents, wake, cluster
        original_delete = cluster.delete_owned_job
        def delete_owned_job(*args, **kwargs):
            # Capture completion before the delete is suppressed by the I/O gate.
            caller = sys._getframe(1)
            if (caller.f_globals.get('__name__') == __package__ + '.ladder'
                    and caller.f_code.co_name == 'observe_task'):
                record('decision', category='mark_done', task=caller.f_locals['n'],
                       stage=caller.f_locals['s']['id'])
            return original_delete(*args, **kwargs)
        patch(cluster, 'delete_owned_job', delete_owned_job)

        def scoped(obj, method, stage_arg):
            original = getattr(obj, method)
            def wrapped(*args, **kwargs):
                global _STAGE, _TASK
                previous, previous_task = _STAGE, _TASK
                _TASK = args[0]['name'] if stage_arg == 'delete' else args[0]
                if stage_arg == 'delete':
                    _STAGE = args[1]['id']
                    record('decision', category='mark_done' if args[2] == 'Job succeeded' else 'safety_stop' if args[2] == 'NRP violation safety stop' else 'submit' if args[2] == 'before resubmit' else 'restart')
                elif stage_arg == 'agent':
                    task = state.task_load(args[0])
                    _STAGE = (task.get('failure') or task.get('util_event') or {}).get('stage')
                    record('decision', category='utilization_review' if task.get('util_event') and not task.get('failure') else 'fix_agent')
                else:
                    _STAGE = args[1] if len(args) > 1 else kwargs.get('sid')
                try:
                    return original(*args, **kwargs)
                finally:
                    _STAGE, _TASK = previous, previous_task
            patch(obj, method, wrapped)
        scoped(stage_jobs, 'do_submit', 'submit')
        scoped(stage_jobs, 'delete_stage_job', 'delete')
        scoped(task_agents, 'run_task_agent', 'agent')
        patch(agents, 'RUNNER_EXEC', {n: agents.exec_backend for n in agents.RUNNER_EXEC})
        for name in ('exec_claude', 'exec_codex', 'exec_agy'):
            patch(agents, name, agents.exec_backend)
        patch(wake, 'WAKE_EXEC', {n: wake.wake_session for n in wake.WAKE_EXEC})
        from .task import pass_ as task_pass
        original_task = task_pass.process_task
        def process_task(name, *args, **kwargs):
            global _TASK
            _TASK = name
            try:
                return original_task(name, *args, **kwargs)
            finally:
                _TASK = None
        patch(task_pass, 'process_task', process_task)
        patch(subprocess, 'run', run)
        patch(urllib.request.OpenerDirector, 'open', http)
        _ACTIVE = dest
        yield
    finally:
        _ACTIVE = None
        for obj, name, old in reversed(patches):
            setattr(obj, name, old)
        tempfile.tempdir = old_temp

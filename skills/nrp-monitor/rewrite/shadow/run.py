#!/usr/bin/env python3
"""One fresh, read-only shadow pass. No scheduler, install or background loop.

Use the miniconda Python from HANDOFF.md. Private evidence stays in /private/tmp;
only sanitized reports are placed in the gitignored runs/ directory. Run once per invocation.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta
import plistlib
from compare import installed_events, shadow_decisions, judge
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

LIVE = ('running', 'retrying', 'blocked', 'NEEDS_OWNER', 'WITH_COORDINATOR')


def tasks(root):
    return {p.parent.name: json.loads(p.read_text()) for p in (root / 'tasks').glob('*/task.json')}


def refresh(source, dest):
    # Never copy symlinks (including nested links), sockets, backups or agent homes.
    def ignore(directory, names):
        return [n for n in names if (Path(directory) / n).is_symlink() or n in ('work', 'backup', '.git', '__pycache__')]
    for name in ('tasks', 'plans', 'approved', 'resume', 'templates', 'webhooks'):
        if (source / name).is_dir() and not (source / name).is_symlink():
            shutil.copytree(source / name, dest / name, ignore=ignore)
    for p in source.iterdir():
        if p.is_file() and not p.is_symlink() and p.suffix in ('.json', '.jsonl', '.log', '.enabled'):
            shutil.copyfile(p, dest / p.name)
    # Relocate absolute state references; external code/origin paths remain read-only.
    for p in dest.rglob('*'):
        if p.is_file() and p.suffix in ('.json', '.jsonl', '.yaml', '.yml', '.src'):
            try:
                content = p.read_text()
                p.write_text(content.replace(str(source), str(dest)))
            except UnicodeError:
                pass


BASE = Path('/private/tmp/claude-501/nrp-shadow')
RUNS = Path(__file__).resolve().parent / 'runs'


def interval(source):
    config = json.loads((source / 'config.json').read_text())
    if config.get('pass_interval_seconds'):
        return int(config['pass_interval_seconds']), 'installed config pass_interval_seconds'
    plist = Path.home() / 'Library/LaunchAgents/edu.ucsc.hunterschweiger.nrp-monitor.plist'
    with plist.open('rb') as stream:
        return int(plistlib.load(stream)['StartInterval']), 'installed launchd StartInterval'


def save(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def resolve_pending(source):
    lines = (source / 'monitor.log').read_text().splitlines()
    pending = []
    # Re-judge persisted results rather than counting resolutions as new runs.
    for path in sorted(BASE.glob('result-*.json')):
        result = json.loads(path.read_text())
        events = installed_events(lines, result['tasks'])
        result['rows'] = [judge(row, events, datetime.now().isoformat(timespec='seconds'))
                          if row['verdict'] == 'pending' else row for row in result['rows']]
        save(path, result)
        Path(result['report']).write_text(render(result))
        pending.extend(dict(run=path.name, **row) for row in result['rows'] if row['verdict'] == 'pending')
    save(BASE / 'pending.json', pending)


def render(result):
    counts = Counter(r['verdict'] for r in result['rows'])
    lines = ['# R4 decision comparison', '', f"Started: {result['start']}; installed window through {result['deadline']}.",
             f"Interval: {result['interval']} seconds ({result['interval_source']}); no waiting or installed execution.",
             f"Private evidence: `{result['private']}`; exit {result['exit']}.", '',
             'First decisions only. Suppression ends reliable task coverage; later events are provisional. '
             'A missing installed event is pending until the deadline, then unknown; silence never proves wait. '
             'A match compares categories across different cluster observations, not identical inputs.', '',
             '| Task / stage | First shadow decision / evidence | Installed evidence | Verdict |', '|---|---|---|---|']
    for row in result['rows']:
        lines.append(f"| {row['task']} / {row['stage']} | {row['category']}; {row['evidence']} | {row['installed']} | {row['verdict']} |")
    lines += ['', 'Counts: ' + '; '.join(f'{k}={counts[k]}' for k in ('matched', 'unexplained', 'pending', 'unknown')), '',
              'Route counts: ' + json.dumps(result['routes'], sort_keys=True), '', 'Provisional events after first suppressed action:']
    lines += [f"- {e['task']} / {e['stage']}: {e['category'] or e['route']} (journal row {e['index'] + 1})" for e in result['provisional']]
    lines += ['', 'External filesystem blocks (private journal retains exact targets and callers):']
    lines += [f"- {e.get('route')}: {e.get('path_kind')}; {', '.join(e.get('caller', []))}" for e in result['filesystem']]
    lines += ['', 'Limits: sequential snapshot; unknown agents/postchecks/admission creates/S3 fallback Jobs; '
              'read-only S3 HEAD/list permitted. No GPU exec, writes outside isolation, wakes or notifications. '
              'Global errors: ' + str(result['errors'])]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--day-summary', metavar='SINCE', help='aggregate persisted runs since local ISO timestamp; resolve pending first')
    args = parser.parse_args()
    RUNS.mkdir(exist_ok=True)
    BASE.mkdir(parents=True, exist_ok=True, mode=0o700)
    source = Path.home() / '.local/state/nrp-monitor'
    resolve_pending(source)
    stamp = datetime.now().strftime('%Y-%m-%dT%H%M%S')
    report = args.report or RUNS / (('day-' if args.day_summary else '') + stamp + '.md')
    if not report.resolve().is_relative_to(RUNS):
        parser.error('--report must remain below rewrite/shadow/runs/')
    if args.day_summary:
        since = datetime.fromisoformat(args.day_summary).isoformat(timespec='seconds')
        results = [json.loads(p.read_text()) for p in sorted(BASE.glob('result-*.json'))]
        results = [r for r in results if r['start'] >= since]
        counts = Counter(row['verdict'] for r in results for row in r['rows'])
        routes = Counter()
        for r in results:
            routes.update(r['routes'])
        lines = ['# R4 day summary', '', f'Since {since}; {len(results)} runs. Pending rows re-judged against current installed log.',
                 '', 'Verdict counts: ' + json.dumps(counts, sort_keys=True), '', 'Route counts: ' + json.dumps(routes, sort_keys=True), '', 'Every unexplained row:']
        for r in results:
            for row in r['rows']:
                if row['verdict'] == 'unexplained':
                    lines.append(f"- {r['start']} {row['task']}/{row['stage']}: shadow {row['category']} ({row['evidence']}); installed {row.get('installed_category')} ({row['installed']}); private {r['private']}")
        report.write_text('\n'.join(lines) + '\n')
        print(f'report={report} counts={dict(counts)}')
        return 0
    dest = Path(tempfile.mkdtemp(prefix='pass-', dir=BASE))
    dest.chmod(0o700)
    started = datetime.now()
    seconds, interval_source = interval(source)
    refresh(source, dest)
    before = tasks(dest)
    (dest / 'snapshot-before.json').write_text(json.dumps(before))
    log_size = (dest / 'monitor.log').stat().st_size
    scripts = Path(__file__).resolve().parents[2] / 'scripts'
    env = dict(os.environ, NRP_MONITOR_STATE=str(dest), PYTHONDONTWRITEBYTECODE='1')
    with (dest / 'stdout.txt').open('w') as out:
        result = subprocess.run([sys.executable, str(scripts / 'nrp-monitor'), 'run', '--shadow'], env=env,
                                stdout=out, stderr=subprocess.STDOUT, cwd=scripts)
    actions_file = dest / 'shadow-actions.jsonl'
    actions = [json.loads(line) for line in actions_file.read_text().splitlines()] if actions_file.exists() else []
    live = {name: task for name, task in before.items() if task['status'] in LIVE}
    rows, provisional = shadow_decisions(actions, live)
    start = started.isoformat(timespec='seconds')
    deadline = (datetime.now() + timedelta(seconds=2 * seconds)).isoformat(timespec='seconds')
    events = installed_events((source / 'monitor.log').read_text().splitlines(), live)
    rows = [judge(dict(row, start=start, deadline=deadline), events, datetime.now().isoformat(timespec='seconds')) for row in rows]
    with (dest / 'monitor.log').open('rb') as stream:
        stream.seek(log_size)
        newlog = stream.read().decode(errors='replace').splitlines()
    data = dict(start=start, deadline=deadline, interval=seconds, interval_source=interval_source,
                private=str(dest), report=str(report.resolve()), exit=result.returncode, tasks=live, rows=rows,
                routes=dict(Counter(a['would_do'] for a in actions if a['would_do'] not in ('observation', 'decision'))),
                provisional=provisional, filesystem=[a for a in actions if a['would_do'].startswith('filesystem write')],
                errors=sum(' error:' in line for line in newlog))
    save(BASE / ('result-' + stamp + '.json'), data)
    report.write_text(render(data))
    resolve_pending(source)
    print(f'report={report} private={dest} counts={dict(Counter(r["verdict"] for r in rows))} exit={result.returncode}')
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())

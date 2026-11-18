#!/usr/bin/env python3
"""One fresh, read-only shadow pass. No scheduler, install or background loop.

Use the miniconda Python from HANDOFF.md. Private evidence stays in /private/tmp;
only the sanitized report is placed in this directory. Run once per invocation.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, help='report path beneath this shadow directory (default: timestamped)')
    args = parser.parse_args()
    args.report = args.report or Path(__file__).parent / (datetime.now().strftime('%Y-%m-%dT%H%M%S') + '.md')
    if not args.report.resolve().is_relative_to(Path(__file__).resolve().parent):
        parser.error('--report must remain below the repository shadow directory')
    base = Path('/private/tmp/claude-501/nrp-shadow')
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    dest = Path(tempfile.mkdtemp(prefix='pass-', dir=base))
    dest.chmod(0o700)
    source = Path.home() / '.local/state/nrp-monitor'
    started = datetime.now()
    refresh(source, dest)
    before = tasks(dest)
    (dest / 'snapshot-before.json').write_text(json.dumps(before))
    installed = (dest / 'monitor.log').read_text().splitlines()
    log_size = (dest / 'monitor.log').stat().st_size
    since = (started - timedelta(minutes=30)).isoformat(timespec='seconds')
    window = [line for line in installed if line[:19] >= since]
    scripts = Path(__file__).resolve().parents[2] / 'scripts'
    env = dict(os.environ, NRP_MONITOR_STATE=str(dest), PYTHONDONTWRITEBYTECODE='1')
    with (dest / 'stdout.txt').open('w') as out:
        result = subprocess.run([sys.executable, str(scripts / 'nrp-monitor'), 'run', '--shadow'], env=env,
                                stdout=out, stderr=subprocess.STDOUT, cwd=scripts)
    after = tasks(dest)
    actions_file = dest / 'shadow-actions.jsonl'
    actions = [json.loads(line) for line in actions_file.read_text().splitlines()] if actions_file.exists() else []
    with (dest / 'monitor.log').open('rb') as stream:
        stream.seek(log_size)
        newlog = stream.read().decode(errors='replace').splitlines()
    # No raw prompts, origins, URLs, request bodies, tokens or config in the report.
    report = ['# R4 single shadow comparison', '',
              f'Window: {since} to {datetime.now().isoformat(timespec="seconds")} (workstation local time).',
              f'Installed evidence: read-only monitor.log and copied task/event state. Snapshot start {started.isoformat(timespec="seconds")}.',
              f'Private evidence: `{dest}`; exit {result.returncode}.', '',
              'Checked: installed monitor was never executed. Snapshot is a sequential copy, not an atomic checkpoint. '
              'Installed decisions below are recent recorded observations, not a replay on the same cluster snapshot. '
              'No recent event means unknown, not an installed decision to do nothing. Task-scoped actions repeat across stage rows and do not imply an action on each stage.', '',
              '| Task / stage | Installed snapshot / recent event | Shadow outcome / task-scoped attempted action | Comparison |',
              '|---|---|---|---|']
    expected = unexplained = same = unknown = 0
    differences = []
    for name, task in sorted(before.items()):
        if task['status'] not in LIVE:
            continue
        recent = [l for l in window if f'task {name}:' in l]
        event_kind = 'no event in window'
        if recent:
            # Only the event prefix; details can contain user text and remote paths.
            event_kind = recent[-1].split(f'task {name}:', 1)[1].strip().split(':', 1)[0][:75]
        task_events = [e for e in task.get('events', []) if e[:19] >= since]
        own_actions = sorted({a['would_do'] for a in actions if a.get('task') == name})
        errors = [l for l in newlog if f'task {name} error:' in l]
        for stage in task['stages']:
            post = next(s for s in after[name]['stages'] if s['id'] == stage['id'])
            old = task['status'] + '/' + stage['state']
            new = after[name]['status'] + '/' + post['state']
            desc = ', '.join(own_actions) or 'no external action reached'
            if errors:
                verdict = 'unexplained: pass error'
                unexplained += 1
                differences.append(name + '/' + stage['id'] + ': pass error (see private log)')
            elif stage['state'] != post['state']:
                verdict = 'unexplained: stage changed on newer cluster observation; agent suppression explains only coordinator routing'
                unexplained += 1
                differences.append(name + '/' + stage['id'] + ': ' + old + ' -> ' + new)
            elif old != new or own_actions:
                if own_actions:
                    verdict = 'expected: shadow suppression (IO gates); downstream state is provisional'
                    expected += 1
                else:
                    verdict = 'unexplained: state changed without a suppressed action'
                    unexplained += 1
                    differences.append(name + '/' + stage['id'] + ': ' + old + ' -> ' + new)
            elif not recent:
                verdict = 'unknown: no recent installed event; snapshot unchanged'
                unknown += 1
            else:
                verdict = 'same snapshot state; recent event is historical'
                same += 1
            report.append(f'| {name} / {stage["id"]} | {old}; {event_kind} ({len(task_events)} task events in window) | {new}; {desc} | {verdict} |')
    report += ['', f'Counts (live task/stage rows): expected differences {expected}; unexplained differences {unexplained}; unchanged with recent evidence {same}; unknown recent decision {unknown}.', '',
               'Unexplained differences: ' + ('; '.join(differences) if differences else 'none'), '',
               'Suppressed route counts: ' + ', '.join(f'{k}={v}' for k, v in sorted(Counter(a['would_do'] for a in actions).items())), '',
               'Limits: agent results, postchecks, admission server-create probes and S3 fallback Jobs are unknown. '
               'AWS subprocesses are suppressed too, so external S3 observations are unknown. GPU exec fallback is forbidden. '
               'Webhooks/wakes and pushes are skipped at their semantic boundary; queued deliveries are not simulated. '
               'These are intentional shadow restrictions, not production behavior changes or Cut-register differences. '
               'C1–C4 remain the approved rewrite differences; no cut-driven difference is asserted without evidence. '
               'Local task changes after suppressed actions are provisional. A day of comparisons is still required.', '',
               f'Pass diagnostics: {len([l for l in newlog if " error:" in l or " error: " in l])} error log lines (private evidence).', '',
               'Global IO gate errors: ' + ', '.join(l.split(' ', 1)[1].split(':', 1)[0] for l in newlog if ' error:' in l),
               'A global gate error makes coverage incomplete even when every task row has no error.']
    args.report.write_text('\n'.join(report) + '\n')
    print(f'report={args.report}\nprivate={dest}\nexpected={expected} unexplained={unexplained} unchanged={same} unknown={unknown} exit={result.returncode}')
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())

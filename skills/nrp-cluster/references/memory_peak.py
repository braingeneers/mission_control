#!/usr/bin/env python3
"""Run a command, preserve its exit status, and report memory evidence at exit.

Usage: python memory_peak.py [--container NAME] [--done-json PATH] -- COMMAND ...
Only updates an existing success marker after a successful command. Upload it afterwards.
An OOM may kill this wrapper too; the watchdog must retain its sampled-peak backstop.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys


def measure():
    # Resolve non-root cgroups too (containers without a private cgroup namespace).
    roots = [(Path('/sys/fs/cgroup'), 'memory.peak', 'cgroup_v2'),
             (Path('/sys/fs/cgroup/memory'), 'memory.max_usage_in_bytes', 'cgroup_v1')]
    try:
        for line in Path('/proc/self/cgroup').read_text().splitlines():
            _, controllers, relative = line.split(':', 2)
            if not controllers:
                roots.insert(0, (Path('/sys/fs/cgroup') / relative.lstrip('/'), 'memory.peak', 'cgroup_v2'))
            elif 'memory' in controllers.split(','):
                roots.insert(1, (Path('/sys/fs/cgroup/memory') / relative.lstrip('/'), 'memory.max_usage_in_bytes', 'cgroup_v1'))
    except (OSError, ValueError):
        pass
    for root, filename, source in roots:
        try:
            value = int((root / filename).read_text().strip())
            if value > 0:
                return {'bytes': value, 'source': source}
        except (OSError, ValueError):
            pass
    rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return {'bytes': int(rss * (1 if sys.platform == 'darwin' else 1024)), 'source': 'ru_maxrss'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--container')
    parser.add_argument('--done-json', type=Path)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('a command is required')
    result = subprocess.run(command)
    row = measure()
    if args.container:
        row['container'] = args.container
    print('NRP_MEMORY_PEAK ' + json.dumps(row, sort_keys=True), flush=True)
    if result.returncode == 0 and args.done_json:
        try:
            marker = json.loads(args.done_json.read_text())
            marker['memory_peak'] = row
            temporary = args.done_json.with_name(args.done_json.name + '.tmp')
            temporary.write_text(json.dumps(marker) + '\n')
            os.replace(temporary, args.done_json)
        except (OSError, ValueError, TypeError) as exc:
            print('memory peak marker update failed: ' + str(exc), file=sys.stderr)
            return 1
    return result.returncode if result.returncode >= 0 else 128 - result.returncode


if __name__ == '__main__':
    sys.exit(main())

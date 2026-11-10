"""Resumable annotation orchestration; Python 3.10+ stdlib only."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import summaries as m

HERE = Path(__file__).resolve().parent


def run(script, *args, **kwargs):
    return subprocess.run([sys.executable, str(HERE / script), *map(str, args)], **kwargs)


def main():
    if sys.version_info < (3, 10):
        sys.exit('Python 3.10+ required')
    args = sys.argv[1:]
    root = m.repo_root(args[args.index('--root') + 1] if '--root' in args else None)
    work = Path(os.environ.get('WORK') or tempfile.mkdtemp(prefix='code-summaries-')).resolve()
    os.environ['WORK'] = str(work)
    for name in ('out', 'logs'):
        (work / name).mkdir(parents=True, exist_ok=True)
    state = work / 'request.json'
    request = {'root': str(root), 'args': args}
    if state.exists():
        saved = json.loads(state.read_text())
        if saved['root'] != str(root) or (args and args != saved['args']):
            sys.exit('WORK belongs to a different root or selection; choose a new WORK')
        args = saved['args']
    else:
        run('make_batches.py', work, *args, check=True, cwd=root)
        state.write_text(json.dumps(request))
    prompt = f'''# Annotate source batches for a code-navigation index

Repository root (read-only for you): {root}
Work dir: {work} (batch inputs in batches/, write outputs to out/)

You are given batch names. For EACH batch name N:
1. Read {work}/batches/N.json. It has tier (full|brief) and files (path, sha256, lines).
2. Read {HERE.parent}/references/annotation-format.md once and follow the tier's format and quality rules exactly (specific, never invent, record shapes/paths/CLI args).
3. Read EVERY listed file completely (chunked reads for long files; paths relative to repository root). Do not run or import them.
4. Write ONE JSON object keyed by those exact repo-relative paths (every path present) to {work}/out/N.json. Use the listed sha256 as source_sha256. Valid JSON only (no comments/trailing commas).
5. Check it: python3 "{HERE}/validate_batch.py" "{work}/batches/N.json" "{work}/out/N.json". Fix errors and re-check (max 3 tries).

Do not modify any other file, do not touch git, do not write inside {root}.
Final reply: one line per batch, "N ok" or "N FAILED <reason>".
'''
    (work / 'PROMPT.md').write_text(prompt)
    batches = sorted((work / 'batches').glob('*.json'))

    def valid(batch):
        return run('validate_batch.py', batch, work / 'out' / batch.name,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

    pending = [b for b in batches if not valid(b)]
    command = os.environ.get('ANNOTATOR_CMD')
    quota = threading.Event()
    if command and pending:
        timeout = float(os.environ.get('ANNOTATOR_TIMEOUT', '1200'))
        def annotate(batch):
            if quota.is_set():
                return
            with (work / 'logs' / (batch.stem + '.log')).open('w') as log:
                try:
                    result = subprocess.run(['bash', '-c', command, 'annotator', str(batch)],
                                            input=prompt, text=True, stdout=log, stderr=log,
                                            cwd=root, timeout=timeout)
                    if result.returncode == 10:
                        quota.set()
                        (work / 'QUOTA_OUT').write_text('exit 10; rerun to retry\n')
                except subprocess.TimeoutExpired:
                    log.write('TIMEOUT\n')
        with concurrent.futures.ThreadPoolExecutor(max_workers=int(os.environ.get('PARALLEL', '6'))) as pool:
            list(pool.map(annotate, pending))
        pending = [b for b in batches if not valid(b)]
    print(f'WORK={work}', flush=True)
    if pending:
        print(f'{len(batches) - len(pending)}/{len(batches)} batches validated.')
        print(f'Spawn subagents/children, each given {work}/PROMPT.md and these batch names:')
        print(' '.join(b.stem for b in pending))
        print(f'Each child writes {work}/out/<batch>.json. Then rerun with WORK="{work}" and the same repository root; selection arguments may be omitted.')
        if quota.is_set():
            print('Quota exhausted (exit 10); queued batches skipped. Rerun to retry remaining batches.')
        return 1
    outputs = [work / 'out' / b.name for b in batches]
    build = ['build', *args]
    if outputs:
        build += ['--annotations', *outputs]
    run('summaries.py', *build, cwd=root, check=True)
    with (work / 'check.txt').open('w') as check:
        rc = run('summaries.py', 'check', '--root', root,
                 *(['--include-tests'] if '--include-tests' in args else []), cwd=root, stdout=check).returncode
    print('Summaries current.' if rc == 0 else f'Still stale: see {work}/check.txt')
    return rc


if __name__ == '__main__':
    raise SystemExit(main())

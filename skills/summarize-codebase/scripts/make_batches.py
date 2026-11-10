"""Split a summaries.py plan into annotation batch manifests (stdlib only).

Usage: python make_batches.py WORK_DIR [plan args: --all | --since REF | 'path/or/glob' ...]
Writes WORK_DIR/batches/{full,brief}_NNN.json, each {"tier", "files": [{path, sha256, lines}]}.
Batches stay within one directory where possible so reviewers see related files together.
"""
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import summaries as m  # noqa: E402

LIMIT = {"full": (12, 3000), "brief": (40, 9000)}  # (max files, max source lines) per batch


def main():
    work = Path(sys.argv[1])
    (work / "batches").mkdir(parents=True, exist_ok=True)
    args = sys.argv[2:]
    root = m.repo_root(args[args.index("--root") + 1] if "--root" in args else None)
    m.configure(root)
    plan = json.loads(subprocess.check_output([sys.executable, str(HERE / "summaries.py"), "plan", "--json", *sys.argv[2:]]))
    files, _, _ = m.discover(root, "--include-tests" in args)
    bydir = defaultdict(list)
    for f in plan["files"]:
        bydir[(m.tier(f), str(Path(f).parent))].append(f)
    batches = []
    for t in ("full", "brief"):
        cur, lines = [], 0
        for (tt, _), fs in sorted(bydir.items()):
            if tt != t:
                continue
            for f in fs:
                n = sum(1 for _ in open(root / f, errors="replace"))
                if cur and (len(cur) >= LIMIT[t][0] or lines + n > LIMIT[t][1]):
                    batches.append((t, cur))
                    cur, lines = [], 0
                cur.append({"path": f, "sha256": files[f], "lines": n})
                lines += n
        if cur:
            batches.append((t, cur))
    for i, (t, fs) in enumerate(batches):
        (work / "batches" / f"{t}_{i:03d}.json").write_text(json.dumps({"tier": t, "files": fs}, indent=1))
    print(f"{plan['count']} files ({plan['tiers']['full']} full, {plan['tiers']['brief']} brief) -> "
          f"{len(batches)} batches in {work / 'batches'}; {len(plan['deleted'])} deleted")


if __name__ == "__main__":
    main()

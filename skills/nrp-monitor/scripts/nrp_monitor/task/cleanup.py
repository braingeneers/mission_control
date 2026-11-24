"""Prune finished tasks' code clones from TASK_CACHE; their commits stay in TASKS/<task>/code.bundle."""
import json
import os
import shutil
from pathlib import Path

PRUNE_EVERY_S = 3600


def _ended(t):
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    for k in ("terminal_at", "finished"):
        try:
            return float(t[k])
        except (KeyError, TypeError, ValueError):
            pass
    return (_m_state.task_dir(t["name"]) / "task.json").stat().st_mtime


def _cache_bytes(root):
    seen, total = set(), 0
    for d, _, files in os.walk(root):
        for f in files:
            try:
                s = os.lstat(os.path.join(d, f))
            except OSError:
                continue
            if (s.st_dev, s.st_ino) not in seen:                                  # local clones hardlink their packs
                seen.add((s.st_dev, s.st_ino))
                total += s.st_blocks * 512
    return total


def cache_report():
    from .. import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return _m_notify.read_json(_m_state.STATE / "clone-cache.json", None)


def prune_clone(t, now):
    """Bundle the task's commits past base, delete its clone dir, record it. Returns a reason it was kept, or None."""
    from .. import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    n, code = t["name"], t["code"]
    clone = Path(code["clone"])
    head = _m_task_registry.git("rev-parse", "HEAD", cwd=str(clone)).stdout.strip() if (clone / ".git").exists() else ""
    bundle = None
    if head and head != code.get("base"):
        bundle = _m_state.task_dir(n) / "code.bundle"
        r = _m_task_registry.git("bundle", "create", str(bundle), "%s..%s" % (code["base"], code["branch"]), cwd=str(clone))
        if r.returncode:
            return "bundle failed: " + r.stderr.strip()[:200]
    fixes = head and _m_task_registry.git("rev-list", "--count", "%s..HEAD" % (code.get("snapshot") or code["base"]),
                                          cwd=str(clone)).stdout.strip() not in ("", "0")

    def record(cur):
        cur["code"].update(pruned_at=now, final=head or cur["code"].get("final"), bundle=str(bundle) if bundle else None)
    _m_state.task_txn(n, record)                                     # record first: a stray clone is harmless, a lost record is not
    shutil.rmtree(clone.parent if clone.parent.parent == _m_state.TASK_CACHE else clone, ignore_errors=True)
    _m_state.log("task %s: clone pruned%s" % (n, " (commits in %s)" % bundle if bundle else ""))
    if fixes and code.get("snapshot"):
        _m_notify.digest("merge", "fixes on branch %s (clone pruned, kept as a bundle): git -C %s fetch %s %s"
                         % (code["branch"], code["repo"], bundle, code["branch"]), n)
    return None


def prune_clones(a, st=None, now=None):
    """Once an hour: delete clones of tasks finished CLONE_KEEP_DAYS ago (CLONE_KEEP_CONT_DAYS while an on_done continuation
    is unregistered) that no unfinished task uses as its repo; refresh the cache size for `status`."""
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import model as _m_model  # Local import breaks orchestration cycle; patches stay on the defining module.
    if getattr(a, "dry_run", False):
        return
    now = now or _m_state.now()
    stamp = _m_state.STATE / "clone-prune.stamp"
    if stamp.exists() and now - stamp.stat().st_mtime < PRUNE_EVERY_S:
        return
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.touch()
    tasks = [t for t in (_m_state.task_load(x) for x in _m_state.task_names()) if t and t.get("code")]
    cache = _m_state.TASK_CACHE.resolve() if _m_state.TASK_CACHE.exists() else _m_state.TASK_CACHE
    in_use = set()                                                    # clones an unfinished task reads (its own, or a parent's as repo)
    for t in tasks:
        if t.get("status") not in _m_model.TERMINAL:
            for k in ("clone", "repo"):
                p = Path(t["code"].get(k) or "/").expanduser()
                p = p.resolve() if p.exists() else p
                if p.is_relative_to(cache):
                    in_use.add(p.relative_to(cache).parts[0] if p != cache else "")
    for t in tasks:
        clone = Path(t["code"].get("clone") or "")
        if t.get("status") not in _m_model.TERMINAL or not clone.parts or not clone.exists() or t["name"] in in_use:
            continue
        if clone.resolve().parent.parent != cache:                   # only clones the monitor made under TASK_CACHE
            continue
        days = (now - _ended(t)) / 86400
        pending = t.get("on_done") and not (t.get("continuation") or {}).get("registered")
        if days < (_m_state.CLONE_KEEP_CONT_DAYS if pending else _m_state.CLONE_KEEP_DAYS):
            continue
        try:
            kept = prune_clone(t, now)
        except Exception as e:
            kept = "%s: %s" % (type(e).__name__, str(e)[:150])
        if kept:
            _m_state.log("task %s: clone kept (%s)" % (t["name"], kept))
    tmp = _m_state.STATE / "clone-cache.json.tmp"
    tmp.write_text(json.dumps({"bytes": _cache_bytes(_m_state.TASK_CACHE) if _m_state.TASK_CACHE.exists() else 0, "ts": now}))
    os.replace(tmp, _m_state.STATE / "clone-cache.json")

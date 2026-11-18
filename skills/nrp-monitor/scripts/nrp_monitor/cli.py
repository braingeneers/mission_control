"""nrp-monitor: agent-free NRP monitoring, approved tasks (no model runs unless something needs a decision)."""
import fcntl
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from . import agents as _m_agents
from . import cluster as _m_cluster
from . import legacy as _m_legacy
from . import notify as _m_notify
from . import plan_wakes as _m_plan_wakes
from . import red_alert as _m_red_alert
from . import s3 as _m_s3
from . import state as _m_state
from .task import pass_ as _m_task_pass_
from . import util as _m_util
from . import wake as _m_wake


def session_ids():
    """Ids naming the chat this command runs in: the T3 thread, else the Claude Code / Codex session. Empty when unknown."""
    import os
    return {v.strip() for v in (os.environ.get(k) for k in ("T3CODE_THREAD_ID", "CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID")) if v and v.strip()}


def origin_ids(origin):
    """Ids naming a task's origin chat: the last segment of its T3 link and its recorded session id."""
    o = origin or {}
    ids = {str(o["session"]).strip()} if o.get("session") else set()
    link = str(o.get("link") or "").rstrip("/")
    if link.startswith("t3-thread://"):
        ids.add(link.rsplit("/", 1)[-1])
    return ids


def cmd_status(a):
    for line in _m_cluster.bad_node_lines():
        print(line)
    hb = _m_state.heartbeat_age()
    watching = [j for j, r in _m_state.load()["jobs"].items() if r.get("status") == "watching"]
    tasks = [n for n in _m_state.task_names() if (_m_state.task_load(n) or {}).get("status") in _m_state.TASK_LIVE]
    active = len(watching) + len(tasks)
    age = None if hb is None else _m_state.now() - hb
    # counts are registrations, not Kubernetes Jobs: a task covers many Jobs (its stages), a legacy `add` covers one
    n_stage_jobs = sum(1 for n in tasks for s in (_m_state.task_load(n) or {}).get("stages", []) if s["state"] == "running")
    desc = "%d task(s) (%d running stage Job(s)) and %d legacy watched job(s) active" % (len(tasks), n_stage_jobs, len(watching))
    if active and (age is None or age > _m_state.HEART_WARN_S):
        print("WARNING: nrp-monitor %s but %s; nothing is being submitted, checked or notified. Start: "
              "sh -c 'while :; do nrp-monitor run; sleep 300; done'" %
              ("has never run" if age is None else "has not run for %d min" % (age // 60), desc))
        return 3
    nh = _m_notify.needs_owner()
    if nh:
        print("nrp-monitor: %d task(s) need the owner: %s  (`nrp-monitor digest`)" % (len(nh), "; ".join(
              "%s: %s" % (n, (t.get("reason") or "")[:100]) for n, t in nh[:3])))
    co = _m_notify.coordinating()
    if co:
        # Session-start notice, scoped to this chat (Hunter 2026-11-18): other chats' waiting tasks stay in their own chats and the
        # digest. Display only; routing and wakes are unchanged.
        here = session_ids()
        if here:
            mine = [(n, t) for n, t in co if origin_ids(t.get("origin")) & here]
            if mine:
                print("nrp-monitor: %d task(s) from this chat wait on you (the owner is told only if you say so): %s" % (
                      len(mine), "; ".join("%s: %s" % (n, (t.get("reason") or "")[:80]) for n, t in mine[:3])))
        else:
            print("nrp-monitor: %d task(s) wait on their coordinator chat; this session's chat is unknown, so they are not "
                  "listed (`nrp-monitor digest`)" % len(co))
    blocked = [r for r in _m_agents.agent_cfg()["runners"] if _m_agents.runner_blocked(r)]
    if blocked:
        print("nrp-monitor: agent runner(s) out of usage: %s%s  (`nrp-monitor agents`)" % (", ".join(blocked),
              "; NO runner left, agent work is waiting" if not _m_agents.agents_available() else "; work uses the next runner"))
    if not a.quiet:
        print("ok: heartbeat %s, %s" % ("none" if age is None else _m_state.ago(hb) + " ago", desc))
    return 0


def save_merged(st):
    """Save jobs.json, keeping registrations that `add` wrote while this (possibly long) pass ran."""
    with _m_state.state_lock():
        disk = _m_state.load()
        for k, v in disk["jobs"].items():
            st["jobs"].setdefault(k, v)
            if v.get("origin") and not st["jobs"][k].get("origin"):        # `origin job` ran while this pass held a stale copy
                st["jobs"][k]["origin"] = v["origin"]
        _m_state.save(st)


def cmd_run(a):
    try:
        if getattr(a, "shadow", False):
            from .shadow import isolated_pass
            with isolated_pass():
                return cmd_run_pass(a)
        return cmd_run_pass(a)
    finally:
        _m_state.S3_PASS = None


def cmd_run_pass(a):
    with _m_cluster.pass_snapshot():                                          # each namespace's Jobs and each Job's pods are read once per pass
        return run_pass(a)


def run_pass(a):
    _m_state.STATE.mkdir(parents=True, exist_ok=True)
    lock = open(_m_state.LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 0                                                              # another pass is running
    st = _m_state.load()
    _m_state.PASS.clear()
    t0 = _m_state.now()
    try:
        _m_s3.s3_prepass(a)                                                         # success markers/gates checked once; in-cluster fallback if S3 is unreachable from here
    except Exception as e:
        _m_state.log("s3_prepass error: %s: %s" % (type(e).__name__, str(e)[:150]))

    def beat(tag):
        if not a.dry_run:
            _m_state.write_heartbeat("%s %s" % (tag, " ".join("%s=%s" % kv for kv in sorted(_m_state.PASS.items())) or "idle"))
    try:
        _m_red_alert.process_red_alert(a, st)                                          # NRP's admission verdict first: it gates every submit below
    except Exception as e:
        _m_state.log("process_red_alert error: %s: %s" % (type(e).__name__, str(e)[:150]))
    rest = (_m_task_pass_.process_tasks, _m_plan_wakes.process_continuations, _m_wake.process_task_webhooks) if a.tasks_only else (_m_legacy.check_pods, _m_task_pass_.process_tasks, _m_plan_wakes.process_continuations, _m_wake.process_task_webhooks, _m_legacy.check_jobs,
                                                                         _m_util.check_orphans)
    for fn in rest:
        try:
            fn(a, st)
        except Exception as e:
            _m_state.log("%s error: %s" % (fn.__name__, str(e)[:150]))
        beat("after-" + fn.__name__)
    if not a.dry_run:
        save_merged(st)
        beat("pass-ok %ds" % (_m_state.now() - t0))
        try:
            _m_notify.daily_digest(a)
        except Exception as e:
            _m_state.log("digest error: %s" % str(e)[:150])
    return 0


def cmd_add(a):
    resume = None
    if a.resume:
        p = Path(a.resume).expanduser().resolve()
        if not p.is_file():
            sys.exit("resume file not found: %s" % p)
        size = p.stat().st_size
        if size > _m_state.RESUME_MAX:
            sys.exit("resume file %s is %d KB; the limit is %d KB. A fresh follow-up agent reads it whole, so register a "
                     "short notes file instead (output prefix, what to do with the result, next commands), not a LOG.md."
                     % (p, size // 1024, _m_state.RESUME_MAX // 1024))
        _m_state.RESUME_DIR.mkdir(parents=True, exist_ok=True)
        dst = _m_state.RESUME_DIR / ("%s.md" % re.sub(r"[^A-Za-z0-9_.-]", "_", a.job))
        shutil.copyfile(p, dst)                                               # run time never reads the Desktop
        resume = str(dst)
    with _m_state.state_lock():
        st = _m_state.load()
        rec = {"added": _m_state.now(), "ns": a.n, "label": a.label or "", "resume": resume, "status": "watching"}
        try:                                     # explicit origin, else the origin of the same Job / its predecessor (repair agents re-register)
            rec["origin"] = (_m_wake.norm_origin(_m_wake.origin_overlay(None, a)) or (st["jobs"].get(a.continue_from or "") or st["jobs"].get(a.job) or {}).get("origin"))
        except _m_state.ChainError as e:
            sys.exit("add refused: %s" % e)
        if not rec["origin"]:
            del rec["origin"]
            _m_wake.require_origin_note(None, "job", a.job)
        if a.continue_from:                                                    # a replacement Job for an authorized task
            old = st["jobs"].get(a.continue_from)
            au = old and old.get("authorize")
            if not au:
                sys.exit("%s is not an authorized task; register with --authorize instead" % a.continue_from)
            fail = " ".join((a.failure or "").lower().split())
            if not fail:
                sys.exit("--continue-from needs --failure 'one line: why the previous Job failed'")
            if au["attempt"] + 1 > au["max"]:
                sys.exit("ATTEMPT CAP REACHED (%d of %d used). Do not resubmit: report the diagnosis (cause, what was tried) as your final line."
                         % (au["attempt"], au["max"]))
            if fail in [f.lower() for f in au.get("failures", [])]:
                sys.exit("SAME FAILURE as an earlier attempt (%r). Do not resubmit: report it as your final line; a person must decide." % fail)
            rec["authorize"] = dict(au, attempt=au["attempt"] + 1, failures=au.get("failures", []) + [fail])
            if not resume:                                                     # keep the old notes, add a lineage line
                rec["resume"] = old.get("resume")
        elif a.authorize:
            adir = _m_state.APPROVED / re.sub(r"[^A-Za-z0-9_.-]", "_", a.job)
            adir.mkdir(parents=True, exist_ok=True)
            au = {"root": a.job, "max": a.max_attempts, "attempt": 1, "dir": str(adir), "failures": []}
            if a.manifest:
                src_m = Path(a.manifest).expanduser().resolve()
                if src_m != (adir / "manifest.yaml").resolve():                 # already in the task dir (an agent wrote it there)
                    shutil.copyfile(src_m, adir / "manifest.yaml")
                au["manifest"] = True
            if a.code_dir:
                au["code"] = snapshot_code(Path(a.code_dir).expanduser().resolve(), adir)
            rec["authorize"] = au
        st["jobs"][a.job] = rec
        _m_state.save(st)
    au = rec.get("authorize")
    _m_state.log("add %s resume=%s label=%s%s" % (a.job, rec["resume"], a.label,
        " authorized attempt %d/%d" % (au["attempt"], au["max"]) if au else ""))
    print("watching %s [%s]%s%s" % (a.job, _m_wake.origin_plain(rec.get("origin")), " (resume copy: %s)" % rec["resume"] if rec["resume"] else " (notify only)",
          "; AUTHORIZED attempt %d of %d, task dir %s" % (au["attempt"], au["max"], au["dir"]) if au else ""))
    return 0


def snapshot_code(src, adir):
    """Copy a code folder (no data/weights/git) to approved/<task>/code and code.orig, so a launchd agent (which cannot read
    Desktop) can fix and rebuild a ConfigMap; the diff is kept in PATCH.diff for a person to merge. Refuses > 30 MB."""
    total = 0
    files = []
    for f in src.rglob("*"):
        rel = f.relative_to(src)
        if f.is_dir() or any(part in _m_state.CODE_SKIP for part in rel.parts) or f.suffix in _m_state.CODE_SKIP_EXT:
            continue
        total += f.stat().st_size
        files.append(rel)
    if total > _m_state.CODE_SNAPSHOT_MAX:
        sys.exit("code dir snapshot is %d MB (limit 30 MB): point --code-dir at a smaller folder" % (total // 2**20))
    for name in ("code", "code.orig"):
        shutil.rmtree(adir / name, ignore_errors=True)
        for rel in files:
            (adir / name / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / rel, adir / name / rel)
    return True


def cmd_list(a):
    st = _m_state.load()
    if not st["jobs"]:
        print("no registered jobs")
    for j, r in sorted(st["jobs"].items()):
        print("%-8s %s  added %s%s%s" % (r.get("status"), j, datetime.fromtimestamp(r["added"]).strftime("%m-%d %H:%M"),
              "  resume=" + r["resume"] if r.get("resume") else "", "  [" + r["label"] + "]" if r.get("label") else ""))
    return 0


def cmd_log(a):
    if _m_state.LOG.exists():
        print("\n".join(_m_state.LOG.read_text().splitlines()[-a.n:]))
    return 0


def main():
    from . import cli_args
    a = cli_args.monitor_parser().parse_args()
    sys.exit(a.f(a))


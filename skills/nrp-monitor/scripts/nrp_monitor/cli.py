"""nrp-monitor: agent-free NRP monitoring, approved tasks (no model runs unless something needs a decision)."""
import argparse
import collections
import contextlib
import fcntl
import getpass
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import agents as _m_agents
from . import cluster as _m_cluster
from . import decisions as _m_decisions
from . import legacy as _m_legacy
from . import notify as _m_notify
from . import nrp_task as _m_nrp_task
from . import plan_commands as _m_plan_commands
from . import plan_wakes as _m_plan_wakes
from . import red_alert as _m_red_alert
from . import s3 as _m_s3
from . import setup as _m_setup
from . import state as _m_state
from .task import pass_ as _m_task_pass_
from .task import registry as _m_task_registry
from . import task_commands as _m_task_commands
from . import util as _m_util
from . import wake as _m_wake


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
        print("nrp-monitor: %d task(s) wait on their coordinator chat (the owner is told only if the chat says so): %s" % (
              len(co), "; ".join("%s: %s" % (n, (t.get("reason") or "")[:80]) for n, t in co[:3])))
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
        return cmd_run_pass(a)
    finally:
        _m_state.S3_PASS = None


def cmd_run_pass(a):
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
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="one pass")
    r.add_argument("--dry-run", action="store_true", help="print what would be launched; no claude, no notification, no state change")
    r.add_argument("--fake-util", metavar="FILE", help="use FILE as nrp-util-check output (test)")
    r.add_argument("--fake-finished", metavar="JOBS", help="comma-separated registered jobs to treat as finished (test)")
    r.add_argument("--tasks-only", action="store_true", help="only advance tasks (no pod checks, chains, legacy jobs; for a test state dir)")
    r.set_defaults(f=cmd_run)
    x = sub.add_parser("costs")
    x.add_argument("--days", type=float, default=7)
    x.add_argument("--task")
    x.set_defaults(f=_m_decisions.cmd_costs)
    x = sub.add_parser("wake-review")
    x.add_argument("name")
    x.add_argument("--by", choices=("rule", "agent", "coordinator"), required=True)
    x.add_argument("--why", required=True)
    x.set_defaults(f=_m_decisions.cmd_wake_review)
    x = sub.add_parser("decide")
    x.add_argument("name")
    x.add_argument("fingerprint")
    x.add_argument("--action", choices=_m_state.DECISION_ACTIONS, required=True)
    x.add_argument("--scope", choices=("stage", "task"), default="stage")
    x.add_argument("--max-uses", type=int)
    x.add_argument("--why", required=True)
    x.set_defaults(f=_m_decisions.cmd_decide)
    tk = sub.add_parser("task", help="owner-approved tasks: the monitor submits, retries (fresh agent) and escalates once").add_subparsers(dest="tcmd", required=True)
    x = tk.add_parser("add", help="validate TASK.json (or YAML), clone its code, copy its manifests; the next pass takes over")
    x.add_argument("file")
    _m_wake.add_origin_args(x)
    x.set_defaults(f=_m_task_registry.cmd_task_add)
    tk.add_parser("list").set_defaults(f=_m_task_commands.cmd_task_list)
    x = tk.add_parser("show")
    x.add_argument("name")
    x.set_defaults(f=_m_task_commands.cmd_task_show)
    x = tk.add_parser("watch", help="set one task to watch mode when no monitor pass is running")
    x.add_argument("name")
    x.set_defaults(f=_m_task_commands.cmd_task_watch)
    x = tk.add_parser("code", help="declare the code dirs `nrp-task reship` packs (pkg dir + extra package dirs, e.g. finetune/ from another repo)")
    x.add_argument("name")
    x.add_argument("--pkg-dir", metavar="DIR", help="the predictor_v3 package folder when it is not in the clone (absolute path)")
    x.add_argument("--extra-pkg-dir", action="append", metavar="DIR", help="an extra package folder to ship beside predictor_v3 (repeatable; relative = in the clone)")
    x.add_argument("--replace", action="store_true", help="replace the declared extra dirs instead of adding")
    x.set_defaults(f=_m_task_commands.cmd_task_code)
    x = tk.add_parser("stage", help="change a stage of a registered task: --resumable marks it as skipping finished items on re-run (Tier 0 then resubmits it once with 2x deadline after a timeout)")
    x.add_argument("name")
    x.add_argument("stage")
    x.add_argument("--resumable", action="store_true")
    x.add_argument("--exclude-node", action="append", help="persist an explicit node exclusion for this stage")
    x.set_defaults(f=_m_task_commands.cmd_task_stage)
    x = tk.add_parser("resume", help="after the owner (or the coordinator chat) decides: clear NEEDS_OWNER / WITH_COORDINATOR, resubmit the failed stage (edit tasks/<t>/manifests first), budgets restart")
    x.add_argument("name")
    x.add_argument("--skip", action="append", metavar="STAGE", help="treat STAGE as done instead")
    x.add_argument("--retries", type=int, help="new max_retries")
    x.add_argument("--gpu-ok-until", metavar="YYYY-MM-DD", help="the owner's new last day of GPU OK for the unfinished GPU stages")
    x.add_argument("--note", help="what was decided (kept in the task)")
    x.add_argument("--decide", choices=_m_state.DECISION_ACTIONS)
    x.set_defaults(f=_m_task_commands.cmd_task_resume)
    x = tk.add_parser("needs-owner", help="(the task's coordinator chat) the owner is truly needed: sets NEEDS_OWNER and sends the one DM")
    x.add_argument("name")
    x.add_argument("--reason", required=True, help="what the owner must decide")
    x.set_defaults(f=_m_task_commands.cmd_task_needs_owner)
    x.add_argument("--by", help="who requests the owner decision")
    x = tk.add_parser("handoff", help="attach a handoff (markdown from templates/handoff.md) to a task registered without one; copied into the task dir")
    x.add_argument("name")
    x.add_argument("file")
    x.set_defaults(f=_m_task_commands.cmd_task_handoff)
    x = tk.add_parser("cancel")
    x.add_argument("name")
    x.set_defaults(f=_m_task_commands.cmd_task_cancel)
    pk = sub.add_parser("plan", help="plan-run plans that tasks continue (on_done); auto-continue is on only when <state>/on_done.enabled exists").add_subparsers(dest="pcmd", required=True)
    x = pk.add_parser("sync", help="copy PATH#ID (the plan section and its run block) into the state dir after the owner answers or widens approval")
    x.add_argument("ref", metavar="PATH#ID")
    x.add_argument("--reopen", action="store_true", help="reopen a closed plan")
    x.set_defaults(f=_m_plan_commands.cmd_plan_sync)
    x = pk.add_parser("close", help="close a finished plan without cancelling its tasks")
    x.add_argument("id")
    x.add_argument("--why", required=True, help="reason for closing the plan")
    x.add_argument("--force", action="store_true", help="close even with live tasks or running continuations; list them without cancelling")
    x.set_defaults(f=_m_plan_commands.cmd_plan_close)
    x = pk.add_parser("needs-owner", help="hand a blocked plan to the owner and send one DM")
    x.add_argument("id")
    x.add_argument("--reason", required=True)
    x.add_argument("--by")
    x.set_defaults(f=_m_plan_commands.cmd_plan_needs_owner)
    x = pk.add_parser("resume", help="clear a plan's owner wait")
    x.add_argument("id")
    x.add_argument("--note")
    x.set_defaults(f=_m_plan_commands.cmd_plan_resume)
    pk.add_parser("list").set_defaults(f=_m_plan_commands.cmd_plan_list)
    x = pk.add_parser("show")
    x.add_argument("id")
    x.set_defaults(f=_m_plan_commands.cmd_plan_show)
    x = sub.add_parser("tool", help="(fix agents, via the nrp-task wrapper; NRP_TASK names the task)")
    x.add_argument("rest", nargs=argparse.REMAINDER)
    x.set_defaults(f=_m_nrp_task.cmd_tool)
    x = sub.add_parser("digest", help="what happened (silent events), what needs the owner")
    x.add_argument("--hours", type=int, default=24)
    x.set_defaults(f=_m_notify.cmd_digest)
    d = sub.add_parser("add", help="register a job")
    d.add_argument("job")
    d.add_argument("--resume", help="file with notes for the follow-up agent")
    d.add_argument("--label", help="short text for notifications")
    d.add_argument("-n", default=_m_state.NS)
    d.add_argument("--authorize", action="store_true",
                   help="TASK-LEVEL APPROVAL: the follow-up agent may debug and resubmit this task (apply, create configmap, delete its own finished Jobs, edit files in its task dir)")
    d.add_argument("--max-attempts", type=int, default=3, help="with --authorize: total Jobs the task may use, including this one (default 3)")
    d.add_argument("--manifest", help="with --authorize: the rendered Job yaml, copied to the task dir for the agent to adjust and re-apply")
    d.add_argument("--code-dir", help="with --authorize: code folder snapshotted for the agent (<=30 MB, no data/.pt/results); it may fix and rebuild the ConfigMap")
    d.add_argument("--continue-from", metavar="OLD", help="(follow-up agents) register a replacement Job for authorized task job OLD; enforces the cap and the same-failure rule")
    d.add_argument("--failure", help="with --continue-from: one line, why the previous Job failed")
    _m_wake.add_origin_args(d)
    d.set_defaults(f=cmd_add)
    sub.add_parser("list").set_defaults(f=cmd_list)
    o = tk.add_parser("origin", help="record/show which chat owns a task, chain or legacy job (metadata only; backfill for work registered without one)")
    o.add_argument("name")
    o.add_argument("--chat", help="T3 v2 link or session id (requires --harness)")
    o.add_argument("--by", help="who changed the origin (default: current session or cli)")
    o.add_argument("--title", help="chat title")
    o.add_argument("--link", help="exact chat link (t3-thread://v2/ENV/THREAD or https://...)")
    o.add_argument("--assistant", help="assistant and model, e.g. 'Codex gpt-6-astra'")
    o.add_argument("--collaborator", help="person the chat works with (default: the owner_name setting)")
    o.add_argument("--harness", choices=_m_state.ORIGIN_HARNESSES, help="where the chat runs, so the monitor wakes it: t3, claude or codex")
    o.add_argument("--session", help="claude/codex session id of the chat (default: read from CLAUDE_CODE_SESSION_ID / CODEX_THREAD_ID)")
    o.add_argument("--cwd", help="directory the claude/codex chat runs in (default: the current directory)")
    o.add_argument("--note", help="short free text")
    o.add_argument("--evidence", help="REQUIRED when recording: how the chat was verified (no guessing)")
    o.add_argument("--replace", action="store_true", help="replace an origin; a new chat clears old chat fields")
    o.set_defaults(f=_m_task_commands.cmd_origin, kind="task")
    o = sub.add_parser("origin", help="record/show which chat owns a task, chain or legacy job (metadata only; backfill for work registered without one)")
    o.add_argument("kind", choices=("task", "job"))
    o.add_argument("name")
    o.add_argument("--chat", help="T3 v2 link or session id (requires --harness)")
    o.add_argument("--by", help="who changed the origin (default: current session or cli)")
    o.add_argument("--title", help="chat title")
    o.add_argument("--link", help="exact chat link (t3-thread://v2/ENV/THREAD or https://...)")
    o.add_argument("--assistant", help="assistant and model, e.g. 'Codex gpt-6-astra'")
    o.add_argument("--collaborator", help="person the chat works with (default: the owner_name setting)")
    o.add_argument("--harness", choices=_m_state.ORIGIN_HARNESSES, help="where the chat runs, so the monitor wakes it: t3, claude or codex")
    o.add_argument("--session", help="claude/codex session id of the chat (default: read from CLAUDE_CODE_SESSION_ID / CODEX_THREAD_ID)")
    o.add_argument("--cwd", help="directory the claude/codex chat runs in (default: the current directory)")
    o.add_argument("--note", help="short free text")
    o.add_argument("--evidence", help="REQUIRED when recording: how the chat was verified (no guessing)")
    o.add_argument("--replace", action="store_true", help="replace an origin; a new chat clears old chat fields")
    o.set_defaults(f=_m_task_commands.cmd_origin)
    l = sub.add_parser("log")
    l.add_argument("-n", type=int, default=30)
    l.set_defaults(f=cmd_log)
    t = sub.add_parser("status", help="heartbeat age; warns (exit 3) when stale while chains or jobs are active")
    t.add_argument("--quiet", action="store_true", help="print only the warning (for a SessionStart hook)")
    t.set_defaults(f=cmd_status)
    x = sub.add_parser("setup", help="choose which assistant runs each tier (Claude Code / Codex / Gemini CLI) from the subscriptions you have; writes agents.json after showing a diff")
    x.add_argument("--non-interactive", action="store_true", help="no prompts: use the flags, else the suggestions for the installed CLIs, and write")
    x.add_argument("--subscriptions", help="comma list of what you have: claude,codex,agy,t3 (default: the installed CLIs)")
    x.add_argument("--triage", help="Tier 1 backends in order, RUNNER[:MODEL],...")
    x.add_argument("--deputy", help="Deputy backends, RUNNER[:MODEL],...; default Claude Sonnet; preserves existing choice when omitted")
    x.add_argument("--fixer", help="Tier 2 backends in order, RUNNER[:MODEL],... (claude or codex)")
    x.add_argument("--dry-run", action="store_true", help="show the diff, write nothing")
    x.set_defaults(f=_m_setup.cmd_setup)
    ag = sub.add_parser("agents", help="which CLI runs each tier's agents (Claude / Codex / Gemini CLI, in order; the next only when one is unavailable), models, follow-up ladder")
    ags = ag.add_subparsers(dest="acmd")
    ag.set_defaults(f=_m_setup.cmd_agents, acmd="show", runner=None)
    ags.add_parser("show").set_defaults(f=_m_setup.cmd_agents, runner=None)
    x = ags.add_parser("test", help="send one tiny prompt through each runner (or one) and say whether it answered")
    x.add_argument("runner", nargs="?")
    x.set_defaults(f=_m_setup.cmd_agents)
    x = ags.add_parser("unblock", help="clear a runner's usage-limit block")
    x.add_argument("runner")
    x.set_defaults(f=_m_setup.cmd_agents)
    a = ap.parse_args()
    sys.exit(a.f(a))


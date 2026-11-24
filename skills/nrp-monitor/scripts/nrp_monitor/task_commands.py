"""NRP monitor task_commands (mechanical extraction; R3a)."""
import argparse
import fcntl
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from . import config as _m_config
from . import decisions as _m_decisions
from . import ladder as _m_ladder
from . import main_chat as _m_main_chat
from . import plan_commands as _m_plan_commands
from . import state as _m_state
from .task import registry as _m_task_registry
from . import tier0 as _m_tier0
from . import util as _m_util
from . import wake as _m_wake

# ---- task commands (people / registering agents) -----------------------------------------------------------------
def cmd_task_list(a):
    names = _m_state.task_names()
    if not names:
        print("no tasks")
    for n in names:
        t = _m_state.task_load(n)
        print("%-12s %-28s %s  retries %d/%d  %s  <%s>" % (t["status"], n, ", ".join("%s=%s" % (s["id"], s["state"]) for s in t["stages"])[:70],
              len(t["attempts"]), t["max_retries"], (t.get("reason") or "")[:80],
              (t.get("origin") or {}).get("title") or _m_state.ORIGIN_MISSING))
    return 0


def cmd_task_watch(a):
    """Set one task to watch mode only when no monitor pass is running."""
    _m_state.STATE.mkdir(parents=True, exist_ok=True)
    with open(_m_state.LOCK, "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print("ERROR monitor pass in progress; try again after it finishes")
            return 1
        if not _m_state.task_txn(a.name, lambda t: (t.update(mode="watch"), _m_state.tev(t, "mode set to watch by operator"))):
            print("ERROR no task %s" % a.name)
            return 2
    print("task %s: mode watch" % a.name)
    return 0


def cmd_task_code(a):
    """`task code NAME [--pkg-dir D] [--extra-pkg-dir D ...] [--replace]`: declare the code dirs `nrp-task reship` packs for a task registered
    without them (for example finetune/ from another repo). Relative = inside the task's clone (added to its sparse checkout), absolute = another checkout."""
    from . import nrp_task as _m_nrp_task  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = _m_state.task_load(a.name)
    if not t or not t.get("code"):
        sys.exit("no task %s with a code clone" % a.name)
    code = dict(t["code"])
    if a.pkg_dir:
        code["pkg_dir"] = a.pkg_dir
    new = list(a.extra_pkg_dir or [])
    code["extra_pkg_dirs"] = new if a.replace else list(code.get("extra_pkg_dirs") or []) + [x for x in new if x not in (code.get("extra_pkg_dirs") or [])]
    bad = _m_task_registry.code_dirs_check(code)
    if bad:
        sys.exit("task code refused: " + "; ".join(bad))
    clone = Path(code["clone"])
    for x in code["extra_pkg_dirs"]:
        if not os.path.isabs(os.path.expanduser(x)) and not (clone / x).is_dir() and code.get("subdir"):
            _m_task_registry.git("sparse-checkout", "add", x, cwd=str(clone))
            _m_task_registry.git("checkout", "-q", cwd=str(clone))
        if not os.path.isabs(os.path.expanduser(x)) and not (clone / x).is_dir():
            sys.exit("task code refused: %s is not in the task's code clone %s (it must be committed in %s)" % (x, clone, code["repo"]))
    try:
        _m_nrp_task.reship_dirs(code)
    except _m_state.ChainError as e:
        sys.exit("task code refused: %s" % e)
    if not _m_state.task_txn(a.name, lambda t: (t["code"].update({k: code[k] for k in ("pkg_dir", "extra_pkg_dirs") if code.get(k)}),
                                      _m_state.tev(t, "code dirs declared by operator: pkg %s, extra %s" % (code.get("pkg_dir") or "default", ", ".join(code["extra_pkg_dirs"]) or "none")))):
        sys.exit("no task %s" % a.name)
    print("task %s: reship packs %s%s" % (a.name, code.get("pkg_dir") or "predictor_v3 (default)", " + " + ", ".join(code["extra_pkg_dirs"]) if code["extra_pkg_dirs"] else ""))
    return 0


def cmd_task_stage(a):
    """Update a registered stage's resumability, node exclusions or exact S3 done marker."""
    t = _m_state.task_load(a.name)
    if not t:
        sys.exit("no task %s" % a.name)
    if not any(s["id"] == a.stage for s in t["stages"]):
        sys.exit("task %s has no stage %s (stages: %s)" % (a.name, a.stage, ", ".join(s["id"] for s in t["stages"])))
    nodes = getattr(a, "exclude_node", None) or []
    done_s3 = getattr(a, "done_s3", None)
    if done_s3 is not None:
        from . import s3 as _m_s3
        if not _m_s3.s3_split(done_s3):
            sys.exit("done_s3 = full s3://bucket/key URI of a single object (no trailing slash)")
        if done_s3 in (_m_state.tstage(t, a.stage).get("after_s3") or []):
            sys.exit("done_s3 repeats one of the stage's after_s3 URIs (it would never be submitted)")
    if not a.resumable and not nodes and done_s3 is None:
        sys.exit("nothing to change: pass --resumable, --exclude-node NODE or --done-s3 URI")
    for node in nodes:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}", node):
            sys.exit("invalid node name")
    if nodes:
        doc = _m_task_registry.manifest_doc(_m_state.tstage(t, a.stage)["manifest"])
        for node in nodes:
            _m_tier0.exclude_node(doc, node)
        _m_task_registry.manifest_write(_m_state.tstage(t, a.stage)["manifest"], doc)
    if not a.resumable and done_s3 is None:
        print("stage %s: excluded %s" % (a.stage, ", ".join(nodes)))
        return 0

    def mark(t):
        stage = _m_state.tstage(t, a.stage)
        if a.resumable:
            stage["resumable"] = True
            _m_state.tev(t, "stage %s marked resumable by operator (Tier 0 may resubmit it once with 2x deadline after a timeout)" % a.stage)
        if done_s3 is not None:
            old = ", ".join(stage["done_s3"])
            stage["done_s3"] = [done_s3]
            _m_state.tev(t, "stage %s done marker changed from %s to %s by operator" % (a.stage, old, done_s3))
    if not _m_state.task_txn(a.name, mark):
        sys.exit("no task %s" % a.name)
    print("task %s: stage %s %s" % (a.name, a.stage, "is resumable" if a.resumable else "done marker updated"))
    return 0


def cmd_task_show(a):
    t = _m_state.task_load(a.name)
    if not t:
        sys.exit("no task %s" % a.name)
    print("%s [%s] mode=%s ns=%s created %s ago  retries %d/%d" % (t["name"], t["status"], t["mode"], t["namespace"], _m_state.ago(t["created"]),
          len(t["attempts"]), t["max_retries"]))
    print("goal: %s\napproved: %s\norigin: %s" % (t["goal"], t["approved"], _m_wake.origin_plain(t.get("origin"), "no chat recorded; goal and code repo above identify it")))
    for old in t.get("origin_history", []):
        print("previous origin (%s): %s" % (old.get("replaced_at", "?"), _m_wake.origin_plain(old)))
    if t.get("reason"):
        print("reason: " + t["reason"])
    if (t.get("code") or {}).get("extra_pkg_dirs") or (t.get("code") or {}).get("pkg_dir"):
        print("code dirs reship packs: pkg %s; extra %s" % (t["code"].get("pkg_dir") or "default", ", ".join(t["code"].get("extra_pkg_dirs") or []) or "none"))
    print("postcheck: " + json.dumps(t.get("postcheck_result")))
    print("stage outputs: " + json.dumps({s["id"]: s.get("outputs", {}) for s in t["stages"]}))
    print("decisions: " + json.dumps(_m_decisions.decisions(a.name)))
    if t.get("failure"):
        f = t["failure"]
        print("fingerprint: " + (f.get("fingerprint") or _m_decisions.fingerprint(t, f)))
        print("failure: stage %s [%s] %s\n  logs: %s" % (f["stage"], f["cls"], f["detail"], f.get("logs")))
    uw = t.get("util_waivers") or []
    if uw:
        print("util waivers: %d of %d used" % (len(uw), _m_config.util_waiver_max()))
        for w in uw[-5:]:
            print("  util waiver %s %s until %s (given %s): %s" % ("ACTIVE" if _m_util.waiver_active(t, w) else "ended", w.get("job", "?"), _m_state.iso(w["until"]) if w.get("until") else "?",
                  _m_state.iso(w["at"]) if w.get("at") else "?", (w.get("reason") or "")[:200]))
    for s in t["stages"]:
        print("  %-14s %-8s %s attempt %d  %s" % (s["id"], s["state"], s["job"], s.get("attempt", 1), s["manifest"]))
        if s["state"] == "pending" and s.get("after_s3"):                 # gate on another task's success marker
            for u in (s["waiting_on"] if "waiting_on" in s else s["after_s3"]):
                print("      waiting-on %s" % u)
    for x in t["attempts"]:
        print("  retry: %s [%s] %s -> %s" % (x["job"], x["cls"], x["detail"][:100], x["fix"][:120] + " fp=" + str(x.get("fingerprint"))))
    for r in t.get("agent_runs", [])[-3:]:
        print("  agent %s %s cost=%s denials=%s: %s" % (_m_state.iso(r["ts"])[5:16], r["kind"], r.get("cost"), r.get("denials"), r["result"][:200]))
    if t.get("code"):
        print("code: %s branch %s (base %s)%s" % (t["code"]["clone"], t["code"]["branch"], t["code"]["base"][:10],
              "" if Path(t["code"]["clone"]).exists() else " (pruned; bundle: %s)" % (t["code"].get("bundle") or "none, no commits past base")))
    h = t.get("handoff")
    if h:
        try:
            secs = _m_wake.handoff_split((_m_state.task_dir(t["name"]) / "handoff.md").read_text())
            ent = {k: len(re.findall(r"(?m)^### ", _m_wake.handoff_body(secs, k) or "")) for k in _m_state.HANDOFF_HEADS[1:]}
            ok = "Registrar intact" if _m_wake.handoff_sha(secs) == h["registrar_sha256"] else "REGISTRAR CHANGED (restored at the next append)"
            print("handoff: accepted%s, %s, %d characters in the Registrar; entries: fix log %d, continuation %d, for the owner %d  (%s)"
                  % (" (thin)" if h.get("thin") else "", ok, _m_wake.handoff_chars(_m_wake.handoff_body(secs, "Registrar")), ent["Fix log"], ent["Continuation"],
                     ent["For the owner"], _m_state.task_dir(t["name"]) / "handoff.md"))
        except OSError:
            print("handoff: recorded but %s is missing" % (_m_state.task_dir(t["name"]) / "handoff.md"))
    else:
        print("handoff: none (no file accepted at task add)")
    for e in t.get("events", [])[-6:]:
        print("  . " + e)
    return 0


def cmd_task_resume(a):
    """After the owner decides: clear NEEDS_OWNER; the failed stage is resubmitted next pass (or --skip it), budgets restart."""
    from .task import model as _m_task_model  # Local import breaks orchestration cycle; patches stay on the defining module.
    msgs, skipped, again, who = [], [], [], ["a person"]

    def f(t):
        del skipped[:], again[:]
        if t["status"] not in ("NEEDS_OWNER", "WITH_COORDINATOR", "blocked"):
            msgs.append("task %s is %s; only NEEDS_OWNER, WITH_COORDINATOR or blocked can be resumed" % (t["name"], t["status"]))
            return False
        who[0] = "the coordinator chat" if t["status"] == "WITH_COORDINATOR" else "a person"
        t.pop("queue_hold", None)
        for s in t["stages"]:
            if s.get("nrp_stopped") or s.get("nrp_woken") or s.get("util_deleted"):
                for key in ("nrp_flag_since", "nrp_stopped", "nrp_woken"):
                    s.pop(key, None)
                s["coordinator_sized"] = _m_state.now()
            q = s.get("queue_wait") or {}
            if q.get("fired") and q.get("attempt") == s.get("attempt", 1):
                q.update(fired=False, multiplier=q.get("multiplier", 1) * 2)
            if s["state"] == "failed":
                s["state"] = "done" if s["id"] in (a.skip or []) else "pending"
                s["attempt"] = s.get("attempt", 1) + (0 if s["state"] == "done" else 1)
                (skipped if s["state"] == "done" else again).append(s["id"])
        if getattr(a, "decide", None) and t.get("failure"):
            _m_decisions.record_decision(t, t["failure"].get("fingerprint") or _m_decisions.fingerprint(t, t["failure"]), a.decide, a.note or "resume decision")
        if t.get("failure"):
            _m_decisions.cost_event(t["name"], "coordinator_resolution", "coordinator", "resolved", stage=t["failure"]["stage"],
                       fingerprint=t["failure"].get("fingerprint") or _m_decisions.fingerprint(t, t["failure"]))
            t["attempts"].append(dict(stage=t["failure"]["stage"], job=t["failure"]["job"], cls=t["failure"]["cls"], sig=t["failure"]["sig"], fingerprint=t["failure"].get("fingerprint") or _m_decisions.fingerprint(t, t["failure"]),
                                      detail=t["failure"]["detail"][:200], fix="resumed by %s: %s" % (who[0], a.note or ""), by="person", ts=_m_state.now()))
        _m_task_model.transition(t, "release", failure=None, reason="")         # the question is answered
        t["budget_from"] = len(t["attempts"])
        if a.retries is not None:
            t["max_retries"] = a.retries
        if getattr(a, "gpu_ok_until", None):
            for s in t["stages"]:
                if s["state"] != "done" and s.get("manifest") and _m_task_registry.manifest_gpu(s["manifest"]):
                    s["gpu_ok_until"] = a.gpu_ok_until
        if a.note and a.note.strip():
            t.setdefault("resume_notes", []).append(dict(note=a.note, ts=_m_state.now(), skipped=list(skipped)))
            _m_wake.handoff_append(t, "%s | coordinator | resume note" % _m_state.iso(_m_state.now()),
                           [("Fix log", _m_wake.handoff_clean(a.note, _m_state.HANDOFF_ENTRY_MAX))])
        _m_state.tev(t, "resumed by %s%s" % (who[0], ": " + a.note if a.note else ""))
    if not _m_state.task_txn(a.name, f):
        sys.exit(msgs[0] if msgs else "no task %s" % a.name)
    said = (["skipped (marked done): %s" % ", ".join(skipped)] if skipped else []) + (
        ["the next pass resubmits %s from %s/manifests" % (", ".join(again), _m_state.task_dir(a.name))] if again else [])
    print("task %s resumed; %s" % (a.name, "; ".join(said) or "no failed stage; pending stages run as usual"))
    return 0


def cmd_task_needs_owner(a):
    """`task needs-owner NAME --reason TEXT`: what the task's coordinator chat runs when the owner is truly needed. Sets NEEDS_OWNER and sends
    the one DM (the same path as every other stop). Nothing else tells the owner about a task that is WITH_COORDINATOR."""
    t = _m_state.task_load(a.name)
    if not t:
        sys.exit("no task %s" % a.name)
    if t["status"] in ("done", "cancelled", "failed"):
        pid = (t.get("on_done") or {}).get("plan")
        if pid:
            return _m_plan_commands.cmd_plan_needs_owner(argparse.Namespace(id=pid, reason=a.reason, by=getattr(a, "by", None)))
        sys.exit("task %s is %s; nothing to hand to the owner; for a blocked plan use `nrp-monitor plan needs-owner PLAN --reason TEXT`" % (a.name, t["status"]))
    if t["status"] == "NEEDS_OWNER":
        sys.exit("task %s is already NEEDS_OWNER (reason: %s)" % (a.name, t.get("reason", "")[:200]))
    if len(a.reason.strip()) < 8:
        sys.exit("--reason: say what the owner must decide (at least a short sentence)")
    _m_ladder.escalate(a.name, "the coordinator chat needs you: " + a.reason.strip(), None)
    print("task %s is NEEDS_OWNER; the owner was sent one DM. They continue it with `nrp-monitor task resume %s`" % (a.name, a.name))
    return 0


def cmd_task_handoff(a):
    """`task handoff NAME FILE`: attach the handoff to a task registered without one (the registering agent writes it after the monitor is
    started). Same checks as the `handoff` field of `task add`; a missing or empty file is an error here. The Registrar is written once:
    a task that has a handoff keeps it."""
    t = _m_state.task_load(a.name)
    if not t:
        sys.exit("no task %s" % a.name)
    if t.get("handoff"):
        sys.exit("task %s already has a handoff: the Registrar is written once and agents only add to the other sections" % a.name)
    try:
        text, thin, why = _m_wake.handoff_load(a.file, str(Path.cwd() / "x"))
    except _m_state.ChainError as e:
        sys.exit("handoff refused: %s" % e)
    if text is None:
        sys.exit("handoff refused: %s" % why)
    if thin and os.environ.get("NRP_MONITOR_REQUIRE_HANDOFF"):
        sys.exit("handoff refused: %s" % why)
    if thin:
        print("warning: %s; fix agents will have little to go on" % why, file=sys.stderr)
    elif _m_wake.handoff_escalation_missing(text):
        print("warning: the handoff does not say how failures are handled. " + _m_state.HANDOFF_ESC_ASK, file=sys.stderr)
    src = _m_wake.handoff_path(a.file, str(Path.cwd() / "x"))

    def attach(t):
        if t.get("handoff"):
            return False
        _m_wake.handoff_attach(t, text, thin, src)
    if not _m_state.task_txn(a.name, attach):
        sys.exit("task %s changed while attaching; run `nrp-monitor task show %s`" % (a.name, a.name))
    print("handoff attached to %s (copy: %s)" % (a.name, _m_state.task_dir(a.name) / "handoff.md"))
    return 0


def cmd_task_cancel(a):
    from .task import model as _m_task_model  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not _m_state.task_txn(a.name, lambda t: _m_task_model.transition(t, "cancel", "cancelled by a person")):
        sys.exit("no task %s" % a.name)
    print("task %s cancelled; nothing deleted" % a.name)
    return 0


def cmd_origin(a):
    """Metadata-only: record (or show) which chat owns a task/chain/legacy job. Same locks as the runner; no state, approval,
    submission or ownership changes. Refuses to overwrite an existing origin without --replace; --evidence is required."""
    chat = getattr(a, "chat", None)
    if chat:
        chat = chat.strip().strip("<>")
        if re.fullmatch(r"t3-thread://v2/[^/]+/[^/]+", chat):
            a.harness, a.link = "t3", chat
        elif a.harness in ("claude", "codex"):
            a.session = chat
        else:
            sys.exit("--chat needs a T3 v2 link or --harness claude|codex for a session id")
    flags = {k: getattr(a, k) for k in ("title", "link", "assistant", "collaborator", "note", "harness", "session", "cwd") if getattr(a, k)}
    if flags.get("harness") in ("claude", "codex"):                     # same defaults as `task add --origin-harness`
        flags.setdefault("session", _m_wake.detect_session(flags["harness"]))
        flags.setdefault("cwd", os.getcwd())
    kind, name = a.kind, a.name
    if not flags:
        cur = {"task": lambda: (_m_state.task_load(name) or {}).get("origin"),
               "job": lambda: (_m_state.load()["jobs"].get(name) or {}).get("origin")}[kind]()
        print("%s %s origin: %s" % (kind, name, _m_wake.origin_plain(cur)))
        return 0
    if not a.evidence:
        sys.exit("--evidence is required: say how the owning chat was verified (e.g. 'T3 thread_read 2026-11-05 title+link; task code repo is its worktree'). Never guess.")
    try:
        new = _m_wake.norm_origin(dict(flags, evidence=a.evidence), source="backfilled %s" % datetime.now().date().isoformat())
    except _m_state.ChainError as e:
        sys.exit("origin refused: %s" % e)
    msgs, replaced = [], []

    def apply(rec, log_fn):
        old = rec.get("origin")
        if old and not a.replace:
            msgs.append("%s %s already has origin %s; use --replace to change it" % (kind, name, _m_wake.origin_plain(old)))
            return False
        if old:
            new["collaborator"] = flags.get("collaborator") or old.get("collaborator", _m_state.OWNER_NAME)
            changed_chat = any(k in flags and flags[k] != old.get(k) for k in ("link", "session"))
            if not changed_chat:
                for k in ("assistant", "title", "link", "harness", "session", "cwd"):
                    if k not in flags and old.get(k):
                        new[k] = old[k]
            rec.setdefault("origin_history", []).append(dict(old, replaced_at=_m_state.iso(), replacement_evidence=a.evidence,
                                                             by=getattr(a, "by", None) or os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CODEX_THREAD_ID") or "cli"))
        rec["origin"] = new
        if old:
            replaced.append(dict(old))
        by = getattr(a, "by", None) or os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CODEX_THREAD_ID") or "cli"
        log_fn("origin %s -> %s by %s (evidence: %s)" % (_m_wake.origin_plain(old), _m_wake.origin_plain(new), by, a.evidence))
    if kind == "task":
        ok = _m_state.task_txn(name, lambda t: apply(t, lambda m: _m_state.tev(t, m)))
    else:
        with _m_state.state_lock():
            st = _m_state.load()
            rec = st["jobs"].get(name)
            ok = False
            if rec is not None:
                ok = apply(rec, lambda m: _m_state.log("job %s: %s" % (name, m))) is not False
                if ok:
                    _m_state.save(st)
    if not ok:
        sys.exit(msgs[0] if msgs else "no %s named %s" % (kind, name))
    print("%s %s origin recorded: %s" % (kind, name, _m_wake.origin_plain(new)))
    if replaced:                                                         # the main chat follows its work to the new chat
        moved = _m_main_chat.transfer(replaced[0], new, by=_m_main_chat.acting_by(a))
        if moved:
            print(moved)
    return 0


def cmd_util_restart(a):
    from . import stage_jobs as _m_stage_jobs
    from . import state as _m_state
    _m_state.STATE.mkdir(parents=True, exist_ok=True)
    with open(_m_state.LOCK, "a") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print("monitor pass in progress; retry after it finishes")
            return 1
        ok, message = _m_stage_jobs.utilization_restart(a.name, a.stage, getattr(a, "cpu", None), getattr(a, "mem", None), coordinator_sized=getattr(a, "coordinator_sized", False))
    print(message)
    return 0 if ok else 1

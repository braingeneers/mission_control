"""NRP monitor ladder (mechanical extraction; R3a)."""
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


def deputy_prompt(t, reason):
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import task_agents as _m_task_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    plan = "(none)"
    if (t.get("on_done") or {}).get("plan"):
        path = _m_plans.plan_dir(t["on_done"]["plan"]) / "plan.md"
        if path.exists():
            plan = path.read_text()
    return (_m_task_agents.task_prompt(t) + "\nYou are the fresh deputy before the coordinator. "
            "Work only inside this task's goal and approval. Edit manifests structurally (load YAML, change, dump), never by text substitution; every edit is validated. You may edit unfinished manifests using measured resources, "
            "make routine environment fixes allowed to the fixer, resubmit within budgets, and record task-scoped decisions "
            "with nrp-task decide FINGERPRINT --action ACTION --why TEXT; apply with nrp-task apply-decision. "
            "nrp-task retry-cap N may raise the cap up to %d. "
            "Never change thresholds, checks, data selection or method, touch other tasks, cancel the task or contact the owner. "
            "skip_reuse fixes a failed stage whose success markers exist, never a failing postcheck; a broken postcheck/acceptance script is the coordinator's problem. "
            "End with RESOLVED: what you did, or ESCALATE: a brief of at most 120 words stating what failed, "
            "what was tried and the exact decision needed.\nEscalation reason: %s\nPlan copy:\n%s" %
            (_m_decisions.scaled_retry_cap(t["stages"]), reason, plan))


def terminal_task(n, detail=None):
    """Late failures of done/cancelled tasks are audit-only, including queued work."""
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = _m_state.task_load(n) or {}
    if t.get("status") not in ("done", "cancelled"):
        return False
    f = t.get("failure") or {}
    detail = detail or ("stage %s [%s] %s" % (f.get("stage"), f.get("cls"), f.get("detail")) if f else None)
    if detail:
        def record(cur):
            if cur.get("status") not in ("done", "cancelled"):
                return False
            key = "%s: %s" % (cur["status"], detail)
            if key in cur.get("ignored_failures", []):
                return False
            cur.setdefault("ignored_failures", []).append(key)
            _m_state.tev(cur, "ignored late failure for %s task: %s" % (cur["status"], detail))
        if _m_state.task_txn(n, record):
            _m_notify.digest("failure-ignored", "late failure for %s task: %s" % (t["status"], detail), n)
    return True


def settled_outcome(n, line, a, kind):
    """Accept DONE/RESOLVED only when recovery passes the existing script checks."""
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if terminal_task(n):
        return True
    t = _m_state.task_load(n)
    report = t.get("report") or {}
    match = re.match(r"^(RESOLVED|DONE)\b", line or "")
    answer = report.get("status") or (match.group(1) if match else None)
    if answer not in ("RESOLVED", "DONE"):
        return False
    if a and a.dry_run:
        return False
    _m_decisions.apply_decision(n, a or argparse.Namespace(dry_run=False))
    t = _m_state.task_load(n)
    if terminal_task(n):
        return True
    if t.get("failure"):
        ok, why = close_failure(n, t["failure"], line, kind=kind)
        if not ok:
            return False
    _m_notify.digest("resolved", "%s settled the event: %s" % (kind, line[:240]), n)
    return True


def task_fail(n, sid, cls, sig, detail, logs=None, extra=None):
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import sizing as _m_sizing  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    if terminal_task(n, "stage %s [%s] %s" % (sid, cls, detail[:200])):
        return False
    def f(t):
        if t.get("failure"):
            return False
        s = _m_state.tstage(t, sid)
        s["state"] = "failed"
        if cls == "resources":
            try:
                extra_resources = _m_sizing.resource_values(_m_task_registry.manifest_doc(s["manifest"]))
            except (OSError, ValueError, KeyError, TypeError):
                extra_resources = None
        else:
            extra_resources = None
        t["failure"] = dict({"stage": sid, "job": s["job"], "cls": cls, "sig": sig, "detail": detail[:400], "logs": logs, "ts": _m_state.now(), "resource_values": extra_resources}, **(extra or {}))
        t["failure"]["fingerprint"] = _m_decisions.fingerprint(t, t["failure"])
        _m_state.tev(t, "stage %s FAILED [%s] %s" % (sid, cls, detail[:200]))     # no wake here: a failure goes up the ladder first (Tier 0/1/2 handle it)
    return _m_state.task_txn(n, f)


def class_retries(t, f):
    """Every class budget belongs to its stage (a failure on one shard says nothing about the others). The task is guarded by
    max_retries and by `systemic_failure` (the same code/unknown signature on several stages)."""
    return sum(1 for x in t.get("attempts", [])[t.get("budget_from", 0):]
               if x.get("cls") == f.get("cls") and x.get("stage") == f.get("stage"))


def systemic_failure(t, f):
    """A reason string when the current code/unknown/outputs failure has the same signature as failures on other stages (one bug
    hitting the fan-out), else None. Environment failures (infra, resources, queue) never count: dead nodes are not a bug."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if f.get("cls") not in _m_state.SYSTEMIC_CLASSES:
        return None
    stages = {x.get("stage") for x in t.get("attempts", [])[t.get("budget_from", 0):]
              if x.get("cls") == f.get("cls") and x.get("sig") == f.get("sig")} | {f.get("stage")}
    need = max(_m_state.SYSTEMIC_STAGES, -(-len(t.get("stages") or []) // 10))
    if len(stages) >= need:
        return "the same [%s] failure on %d stages (%s): one systemic cause, not bad shards; last: %s" % (
            f["cls"], len(stages), ", ".join(sorted(map(str, stages)))[:80], f.get("detail", "")[:200])
    return None


def escalate(n, reason, a=None):
    from .task import model as _m_task_model  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    out = {}

    def f(t):
        if not _m_task_model.can(t, "escalate"):
            return False
        _m_task_model.transition(t, "escalate", "NEEDS_OWNER: " + reason, reason=" ".join(reason.split())[:400],
                                 needs_since=_m_state.now(), escalations=t.get("escalations", 0) + 1)
        out["k"], out["label"] = "task:%s:%d" % (n, t["escalations"]), t["label"]
    if _m_state.task_txn(n, f):
        _m_state.PASS["escalated"] = _m_state.PASS.get("escalated", 0) + 1
        _m_notify.push("NRP task %s needs you: %s  (nrp-monitor task show %s)" % (out["label"], reason[:200], n), out["k"],
             a.dry_run if a else False, refs=["task:" + n])


def coordinator_summary(t, reason):
    """The short text a Tier 3 wake carries: what happened, and where to look. No logs, no secrets."""
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    n, f = t["name"], t.get("failure") or {}
    bits = ["NRP task %s needs its coordinator chat (the owner is NOT notified unless you say so): %s" % (n, reason)]
    if f:
        bits.append("Event: stage %s [%s] %s." % (f.get("stage"), f.get("cls"), (f.get("detail") or "")[:200]))
    if f:
        bits.append("Fingerprint: " + (f.get("fingerprint") or _m_decisions.fingerprint(t, f)))
    bits.append("After handling: `nrp-monitor wake-review %s --by rule|agent|coordinator --why TEXT`." % n)
    bits.append("Look: `nrp-monitor task show %s`; saved logs %s; fix log (handoff) %s." % (n, f.get("logs") or "(none)", _m_state.task_dir(n) / "handoff.md"))
    bits.append("Then: fix it and `nrp-monitor task resume %s --note TEXT` (resubmits the failed stage, budgets restart), or `nrp-monitor task cancel %s`, "
                "or only if the owner is truly needed `nrp-monitor task needs-owner %s --reason TEXT` (sends the one DM); for a plan blocked on the owner: `nrp-monitor plan needs-owner PLAN --reason TEXT`." % (n, n, n))
    if reason.startswith("Deputy:"):
        bits.insert(0, reason.split(" | ", 1)[0])
    return " ".join(bits)[:2400]


def to_coordinator(n, reason, a=None, deputy=True):
    """Tier 3: wake the task's coordinator chat (its webhook; same machinery as the done/failure wakes) with a short summary and pointers.
    The task goes to WITH_COORDINATOR, not NEEDS_OWNER: the owner is told only if the chat runs `task needs-owner`. With no webhook
    configured for the task there is nobody to wake, so the owner is told instead (NEEDS_OWNER) and nothing is lost. A wake that cannot
    be delivered (wake_failed) or an answer that never comes (check_coordinator_waits) falls back the same way."""
    from .task import model as _m_task_model  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import task_agents as _m_task_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = _m_state.task_load(n)
    if terminal_task(n) or t["status"] in _m_state.TASK_HELD:
        return
    failure = t.get("failure")
    if deputy and failure and not (a and a.dry_run) and _m_state.OWNER.get("deputy_enabled", True):
        fp = failure.get("fingerprint") or _m_decisions.fingerprint(t, failure)
        key = "%s:%d" % (fp, len(t["attempts"]))
        if key not in t.get("deputy_runs", []):
            _m_state.task_txn(n, lambda task: task.setdefault("deputy_runs", []).append(key))
            try:
                line, den = _m_task_agents.run_task_agent(n, deputy_prompt(t, reason), a, kind="deputy")
            except Exception as error:
                line = "ESCALATE: deputy failed (%s)" % type(error).__name__
            if settled_outcome(n, line, a, "deputy"):
                return
            current = _m_state.task_load(n)
            if not current.get("failure") or current["status"] == "blocked":
                return
            reason = "Deputy: " + " ".join(line.split()[:120]) + " | " + reason
    reason = " ".join(reason.split())
    if not _m_wake.wake_target(_m_state.task_load(n) or {"name": n}):
        escalate(n, "%s [no coordinator webhook or harness session is configured for this task, so the owner is told]" % reason[:290], a)
        return
    out = {}

    def f(t):
        if not _m_task_model.can(t, "coordinate"):
            return False
        _m_task_model.transition(t, "coordinate", reason=reason[:400], coordinator_since=_m_state.now(),
                                 coordinator_wakes=t.get("coordinator_wakes", 0) + 1)
        out["event"] = _m_wake.queue_task_webhook(t, "escalation", summary=coordinator_summary(t, reason))
        _m_state.tev(t, "WITH_COORDINATOR (Tier 3, wake queued): " + reason)
    if _m_state.task_txn(n, f):
        _m_notify.digest("coordinator", "woke the coordinator chat: %s" % reason[:260], n)
        _m_state.PASS["coordinator"] = _m_state.PASS.get("coordinator", 0) + 1


def check_coordinator_waits(a):
    """A WITH_COORDINATOR task whose wake was delivered but never answered for COORD_STALE_S goes to the owner."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if a.dry_run:
        return
    for n in _m_state.task_names():
        t = _m_state.task_load(n) or {}
        if t.get("status") == "WITH_COORDINATOR" and _m_state.now() - t.get("coordinator_since", _m_state.now()) > _m_state.COORD_STALE_S:
            escalate(n, "the coordinator chat did not answer for %s. %s" % (_m_state.ago(t["coordinator_since"]), t.get("reason", "")), a)


def triage_verdict(text):
    """(verdict, text) from the LAST verdict line of the judge's answer. Anything else fails closed to ESCALATE."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    ms = list(_m_state.TRIAGE_VERDICT_RE.finditer((text or "").strip().splitlines()[-1] if (text or "").strip() else ""))
    if not ms or not ms[-1].group(2).strip():
        return "ESCALATE", "no verdict line in the triage answer"
    return ms[-1].group(1), " ".join(ms[-1].group(2).replace("*", "").replace("`", "").split())[:300]


def triage_wanted(t, f):
    """Tier 1 looks at an event when a benign answer is possible: the Job is still alive or finished, or the class is one the script cannot
    pin down (unknown, slow). A plain terminal failure the rules already classified (OOM, traceback, image pull) goes straight to Tier 2.
    Util observations always receive a judge before a fixer."""
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if f.get("cls") == "util":
        return True
    return f.get("cls") in _m_state.TRIAGE_CLASSES_ALWAYS or _m_cluster.job_state(f["job"], t["namespace"]) in ("running", "pending", "ok")


def triage_prompt(t):
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    f = t["failure"] or {}
    tpl = (_m_state.TPL / "task_triage.md").read_text()
    rep = {"name": t["name"], "goal": t["goal"], "origin": _m_wake.origin_plain(t.get("origin")), "ns": t["namespace"], "notes": t["notes"] or "(none)",
           "cls": f.get("cls", "?"), "stage": f.get("stage", "?"), "job": f.get("job", "?"), "sig": f.get("sig", "?"), "detail": f.get("detail", ""),
           "logs": f.get("logs") or "(none saved)", "dir": str(_m_state.task_dir(t["name"])),
           "stages": "\n".join("  - %s job=%s state=%s" % (s["id"], s["job"], s["state"]) for s in t["stages"]),
           "attempts": "\n".join("  - %s [%s] %s -> %s" % (x["job"], x["cls"], x["detail"][:120], x["fix"][:120]) for x in t["attempts"][-5:]) or "  (none)"}
    for k, v in rep.items():
        tpl = tpl.replace("{%s}" % k, v)
    return tpl.replace("{handoff}", _m_wake.handoff_prompt(t)) + _m_decisions.failure_context(t)


def close_failure(n, f, why, kind="Tier 1 triage"):
    """Close a triaged event as benign. The script decides, not the verdict: the Job must be alive or done, or the stage's outputs present.
    Returns (ok, refusal)."""
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import s3 as _m_s3  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if terminal_task(n):
        return False, "task is terminal"
    t = _m_state.task_load(n)
    s = _m_state.tstage(t, f["stage"])
    st_ = _m_cluster.job_state(f["job"], t["namespace"])
    present = all(_m_s3.s3_exists(u, {}) is True for u in s["done_s3"])
    if st_ not in ("running", "pending", "ok") and not present:
        return False, "Job %s is %s and the stage's outputs are missing" % (f["job"], st_)

    def c(t):
        cur = t.get("failure")
        if t.get("status") in ("done", "cancelled") or not cur or cur.get("ts") != f.get("ts"):
            return False
        s2 = _m_state.tstage(t, f["stage"])
        if present and st_ not in ("running", "pending"):
            s2.update(state="done", done_ts=_m_state.now())
        else:
            s2["state"] = "running"
        s2.pop("util_deleted", None)
        t["failure"] = None
        _m_state.tev(t, "event closed by %s, no fix needed: %s" % (kind, why[:200]))
    if not _m_state.task_txn(n, c):
        return False, "the failure changed while it was closed"
    _m_decisions.cost_event(n, "triage_resolution" if kind == "Tier 1 triage" else kind + "_resolution",
               "1" if kind == "Tier 1 triage" else "2" if kind == "fixer" else kind, "resolved", stage=f["stage"],
               fingerprint=f.get("fingerprint") or _m_decisions.fingerprint(t, f))
    _m_notify.digest("triage-closed" if kind == "Tier 1 triage" else "resolved", "stage %s [%s]: no fix needed (%s)" % (f["stage"], f["cls"], why[:240]), n)
    return True, ""


def observe_task(n, jobs):
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import s3 as _m_s3  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import sizing as _m_sizing  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import timeouts as _m_timeouts  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import pass_ as _m_task_pass_  # Local import breaks orchestration cycle; patches stay on the defining module.
    if terminal_task(n):
        return
    t = _m_state.task_load(n)
    ns = t["namespace"]
    for s in t["stages"]:
        if s["state"] != "running":
            continue
        sid, info = s["id"], jobs.get(s["job"])
        if info and info["state"] in ("running", "pending"):
            if not s.get("pod_started"):
                ps0 = _m_task_pass_.pod_started(ns, s["job"])
                if ps0:
                    _m_state.task_txn(n, lambda t: _m_state.tstage(t, sid).update(pod_started=ps0))
                    s = _m_state.tstage(_m_state.task_load(n), sid)
            try:
                _m_timeouts.deadline_watch(n, s, info)                      # Tier 0: credit queue time, keep a progressing Job alive
            except Exception as e:                              # a Tier 0 helper must never stop the pass
                _m_state.log("task %s: deadline watch error: %s: %s" % (n, type(e).__name__, str(e)[:150]))
            continue
        if info is None:
            if _m_state.now() - s.get("submitted", 0) < _m_state.MISSING_GRACE_S:
                continue
            if all(_m_s3.s3_exists(u, {}) is True for u in s["done_s3"]):
                _m_state.task_txn(n, lambda t: (_m_state.tstage(t, sid).update(state="done", done_ts=_m_state.now()), _m_sizing.propagate_resources(t, _m_state.tstage(t, sid)), _m_state.tev(t, "stage %s done (Job gone, outputs present)" % sid)))
                _m_notify.digest("done", "stage %s done (Job gone before logs were saved; outputs present)" % sid, n)
                continue
            if s.get("util_deleted"):
                task_fail(n, sid, "util", "util:" + _m_state.norm_sig(s["util_deleted"]), "deleted for NRP utilization: " + s["util_deleted"])
            else:
                task_fail(n, sid, "infra", "vanished", "Job %s disappeared before it finished and its outputs are missing" % s["job"])
        elif info["state"] == "ok":
            p, _ = _m_task_pass_.save_task_logs(t, s, "Job succeeded")
            res = [_m_s3.s3_exists(u, {}) for u in s["done_s3"]]
            if None in res:
                n_err = s.get("s3_errors", 0) + 1
                _m_state.task_txn(n, lambda t: _m_state.tstage(t, sid).update(s3_errors=n_err))
                if n_err >= 5:
                    task_fail(n, sid, "infra", "s3-check", "cannot check S3 outputs (aws s3api head-object failed 5 passes)", p)
                continue
            if False in res:
                miss = s["done_s3"][res.index(False)]
                task_fail(n, sid, "outputs", "outputs-missing:" + miss, "Job succeeded but %s does not exist" % miss, p)
                continue
            _m_cluster.kubectl("-n", ns, "delete", "job", s["job"], "--wait=false")
            _m_state.task_txn(n, lambda t: (_m_state.tstage(t, sid).update(state="done", done_ts=_m_state.now()), _m_sizing.propagate_resources(t, _m_state.tstage(t, sid)), _m_state.tev(t, "stage %s done, Job deleted" % sid)))
            _m_notify.digest("done", "stage %s (%s) succeeded; outputs %s" % (sid, s["job"], ", ".join(s["done_s3"])[:200]), n)
            _m_state.PASS["stage_done"] = _m_state.PASS.get("stage_done", 0) + 1
        elif info["state"] == "FAILED":
            p, logtxt = _m_task_pass_.save_task_logs(t, s, "Job failed")
            cls, sig, detail = _m_task_pass_.classify(t, s, logtxt)
            task_fail(n, sid, cls, sig, detail, p)


def handle_failure(n, a):
    """The task escalation ladder. Tier 0: script rules (classification in observe_task, deadline rules, `tier0_timeout`). Tier 1: read-only
    triage, where a benign answer is possible; 'no fix needed' CLOSES the event. Tier 2: the fixer. Tier 3: the task's
    coordinator chat (`to_coordinator`). The owner is told (NEEDS_OWNER + one DM) only by the chat (`task needs-owner`), or when a person's
    decision is the only way on (watch-only task, GPU approval), or when the chat cannot be woken."""
    from . import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import task_agents as _m_task_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import timeouts as _m_timeouts  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import util as _m_util  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    if terminal_task(n):
        return
    t = _m_state.task_load(n)
    f = t["failure"]
    if not f.get("fingerprint"):
        f["fingerprint"] = _m_decisions.fingerprint(t, f)
        _m_state.task_txn(n, lambda task: task["failure"].update(fingerprint=f["fingerprint"]))
    if _m_decisions.postcheck_failure(f):
        to_coordinator(n, "postcheck failed: the coordinator must fix the acceptance script; skip_reuse cannot resolve it. " + f["detail"], a, deputy=False)
        return
    if _m_decisions.apply_decision(n, a):
        return
    since = t.get("budget_from", 0)
    prior = [x["sig"] for x in t["attempts"] if x["stage"] == f["stage"]]
    used = len(t["attempts"][since:])
    cls_used = class_retries(t, f)
    if t["mode"] == "watch":
        # a watch-only task has no ladder: the failure is final, so this is the one `failure` wake (the chat hears it, and so does the owner)
        if not a.dry_run:
            _m_state.task_txn(n, lambda t: _m_wake.queue_task_webhook(t, "failure", summary="NRP task %s (watch-only): stage %s failed [%s] %s. Look: "
                     "`nrp-monitor task show %s`. The owner is notified too: a watch-only task has no automatic fixes."
                     % (n, f["stage"], f["cls"], f["detail"][:200], n)))
        escalate(n, "watch-only task, stage %s failed [%s]: %s" % (f["stage"], f["cls"], f["detail"]), a)
        return
    if f["cls"] == "slow" and not a.dry_run and _m_timeouts.tier0_timeout(n, f):
        return
    why = None
    if f["sig"] in prior and f["sig"] != _m_state.LOST_SIG:
        why = "stage %s failed the same way again after a retry [%s]: %s" % (f["stage"], f["cls"], f["detail"])
    elif used >= t["max_retries"]:
        why = "retry cap %d reached; last failure [%s]: %s" % (t["max_retries"], f["cls"], f["detail"])
    elif cls_used >= _m_state.CLASS_BUDGET.get(f["cls"], 1):
        why = "%s retries used (%d) on stage %s; last failure: %s" % (f["cls"], cls_used, f["stage"], f["detail"])
    else:
        why = systemic_failure(t, f)
    if why:
        to_coordinator(n, why, a)
        return
    gx = _m_task_registry.gpu_expired(_m_state.tstage(t, f["stage"]))
    if gx and not a.dry_run:
        escalate(n, "stage %s failed [%s] %s | %s" % (f["stage"], f["cls"], f["detail"][:150], gx.split(" (`nrp-monitor")[0]), a)
        return
    if a.dry_run:
        print("[dry-run] task %s: would run Tier 1 triage / start a fix agent for [%s] %s" % (n, f["cls"], f["detail"][:120]))
        return
    if not _m_agents.agents_available():
        _m_state.log("task %s: fix agent waits: %s" % (n, _m_agents.unavailable_text()))
        return
    if _m_state.OWNER.get("ladder", {}).get("triage_judge", False) and not f.get("triaged") and triage_wanted(t, f):                       # Tier 1: once per failure
        _m_state.PASS["agents"] = _m_state.PASS.get("agents", 0) + 1
        line, _ = _m_task_agents.run_task_agent(n, triage_prompt(t), a, kind="triage")
        if _m_agents.is_unavailable(line):
            return
        run = (_m_state.task_load(n).get("agent_runs") or [{}])[-1]
        verdict, vtext = run.get("verdict") or "ESCALATE", run.get("verdict_text") or line

        def mark(t):
            cur = t.get("failure")
            if not cur or cur.get("ts") != f.get("ts"):
                return False
            cur["triaged"], cur["triage_text"] = _m_state.now(), "%s: %s" % (verdict, vtext)
            _m_state.tev(t, "Tier 1 triage: %s: %s" % (verdict, vtext[:200]))
        _m_state.task_txn(n, mark)
        if verdict in _m_state.TRIAGE_CLOSE:
            ok, refused = close_failure(n, f, vtext)
            if ok:
                return
            _m_state.task_txn(n, lambda t: _m_state.tev(t, "Tier 1 said no fix needed but the script refused to close it: " + refused))
        t = _m_state.task_load(n)
        if terminal_task(n) or not t.get("failure"):
            return
        f = t["failure"]
    _m_state.PASS["agents"] = _m_state.PASS.get("agents", 0) + 1
    line, den = _m_task_agents.run_task_agent(n, _m_task_agents.task_prompt(t), a)                       # Tier 2
    if _m_agents.is_unavailable(line) or settled_outcome(n, line, a, "fixer"):
        return
    t = _m_state.task_load(n)
    rep = (t.get("report") or {})
    if t["status"] == "blocked":
        return
    if t.get("failure") is None:
        _m_notify.digest("retry", "%s [%s] -> %s" % (f["job"], f["cls"], (t["attempts"][-1]["fix"] if t["attempts"] else line)[:250]), n)
        return
    if den and not rep:
        line = "the fix agent was denied %d tool call(s) (monitor fault): %s" % (len(den), line)
    claim = t.get("util_ok_claim")
    if claim is None and rep.get("status") == "UTIL_OK":
        claim = rep.get("line") or ""
    if claim is not None and rep.get("status") in (None, "UTIL_OK"):          # a STOPPED report stays a stop
        ok, why = _m_util.util_waive(n, f, claim, a)
        if ok:
            return
        _m_state.log("task %s: util waiver refused: %s" % (n, why))
        _m_state.task_txn(n, lambda t: (t.pop("util_ok_claim", None), _m_state.tev(t, "util waiver refused: " + why)))
        to_coordinator(n, "fix agent did not resubmit: %s [util waiver refused: %s]" % (((rep.get("line") or line)[:200]), why[:110]), a)
        return
    to_coordinator(n, "fix agent did not resubmit: %s" % ((rep.get("line") or line)[:300]), a)                    # Tier 3


"""NRP monitor plan_wakes (mechanical extraction; R3a)."""
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


def step_mates(t):
    """Other tasks of task `t`'s plan step (empty without on_done or when the plan state is unreadable)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not t.get("on_done"):
        return []
    try:
        return step_siblings(t)
    except Exception as e:
        _m_state.log("task %s: step siblings unreadable: %s: %s" % (t["name"], type(e).__name__, str(e)[:120]))
        return []


def task_group(t, h):
    return t.get("group") or next((g for g, steps in h.get("groups", {}).items()
                                   if t.get("on_done", {}).get("from_step") in steps), None)


def completion_policy(t):
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    h = _m_plans.plan_header((t.get("on_done") or {}).get("plan")) or {}
    group = task_group(t, h)
    policy = h.get("wake_overrides", {}).get(group, h.get("wake", "task"))
    return "task" if policy == "group" and group is None else policy


def group_members(pid, group, h):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return [t for n in _m_state.task_names() for t in [_m_state.task_load(n)] if t
            and (t.get("on_done") or {}).get("plan") == pid and task_group(t, h) == group]


def group_ready(h, group, members):
    # Every declared step must be represented; cancellations and failed checks remain open.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    ledger = _m_plans.plan_state(h["plan"])["ledger"]
    names = {t["name"] for t in members}
    missing = [e["task"] for step in h["groups"][group] for e in ledger.get(step, [])
               if e["task"] not in names and not _m_state.task_load(e["task"])]
    return (not missing and all(any(t["on_done"]["from_step"] == step for t in members) for step in h["groups"][group])
            and all(t["status"] == "done" and (t.get("continuation") or {}).get("state") == "closed"
                    and t["continuation"].get("status") in ("CONTINUED", "WAITING", "COVERED") for t in members))


def process_group_wakes(a):
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plan_commands as _m_plan_commands  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    if a.dry_run:
        return
    for pid in _m_plan_commands.plan_names():
        if _m_plans.plan_state(pid)["status"] == "closed":
            continue
        h = _m_plans.plan_header(pid) or {}
        for group in h.get("groups", {}):
            with _m_state.state_lock():
                members = group_members(pid, group, h)
                if not members or completion_policy(members[0]) != "group" or not group_ready(h, group, members):
                    continue
                st = _m_plans.plan_state(pid)
                summary = "Plan %s group %s complete. " % (pid, group)
                summary += "; ".join("%s: %d/%d stages done; results %s; postcheck %s; outputs %s; %s" % (
                    t["name"], sum(s["state"] == "done" for s in t["stages"]), len(t["stages"]),
                    _m_plans.plan_dir(pid) / "results.md", json.dumps(t.get("postcheck_result")),
                    json.dumps({s["id"]: s.get("outputs", {}) for s in t["stages"]}),
                    t["continuation"].get("line", "")) for t in members)
                summary += "; planned stops reached: " + ", ".join(sorted({step for t in members
                    for step, _ in _m_plans.next_steps(h, t["on_done"]["from_step"]) [1] if step in h.get("stops", [])}))
                summary += "; resolved failures: " + json.dumps([r for r in _m_decisions.cost_rows()
                    if r.get("task") in {t["name"] for t in members} and r.get("outcome") == "resolved"])
                key = pid + ":" + group
                announced = set(st.get("group_wake_members", {}).get(group, []))
                for member in members:
                    announced.update(member.get("group_wake_members", {}).get(key, []))
                prior = next((t.get("group_wakes", {}).get(key) for t in members if t.get("group_wakes", {}).get(key)), None)
                # Reconstruct pre-snapshot claims from their ledger time, without covering later registrations.
                if not announced and (prior or group in st.get("group_wakes", {})):
                    claim = prior or st["group_wakes"][group]
                    claimed_at = next((r["ts"] for r in _m_decisions.cost_rows() if r.get("event_id") == claim), 0)
                    announced = {t["name"] for t in members if t.get("created", 0) <= claimed_at
                                 or t.get("group_wakes", {}).get(key)}
                if {t["name"] for t in members} <= announced:
                    st.setdefault("group_wakes", {})[group] = prior
                    _m_notify.write_json(_m_plans.plan_dir(pid) / "state.json", st)
                    continue
                t = next((t for t in reversed(members) if _m_wake.wake_target(t)), members[-1])
                event = _m_wake.queue_task_webhook(t, "done", summary=summary)
                if event:
                    t.setdefault("group_wakes", {})[key] = event
                    names = sorted(t["name"] for t in members)
                    t.setdefault("group_wake_members", {})[key] = names
                    st.setdefault("group_wake_members", {})[group] = names
                    _m_state.task_write(t)
                    st.setdefault("group_wakes", {})[group] = event
                    _m_notify.write_json(_m_plans.plan_dir(pid) / "state.json", st)
                    _m_decisions.cost_event(t["name"], "group_wake", "coordinator", "done", plan=pid, group=group, event_id=event)


def terminal_wake(t):
    """Under state_lock: check every terminal transition, including internal cancellations."""
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not t.get("on_done"):
        if t["status"] == "done" and t.get("digest_only"):
            _m_notify.digest("done", "%s finished; digest only, no coordinator wake (%s)" % (t["name"], t["digest_only"]), task=t["name"])
            return
        if t["status"] == "done":
            event = _m_wake.queue_task_webhook(t, "done")
            if event:
                t["done_event_id"] = event
        return
    if _m_plans.plan_state(t["on_done"]["plan"])["status"] == "closed":
        _m_state.tev(t, "plan closed; terminal completion recorded without a wake")
        return
    policy = completion_policy(t)
    if policy in ("group", "digest"):
        if t["status"] == "done":
            _m_decisions.cost_event(t["name"], "wake_avoided", "coordinator", "done", policy=policy)
        return
    sib = step_siblings(t, include_cancelled=True)
    waiting = [x["name"] for x in sib if x["status"] not in ("done", "failed", "cancelled")]
    if waiting:
        _m_state.tev(t, "step %s: done wake held until task(s) %s finish" % (t["on_done"]["from_step"], ", ".join(waiting)))
        return
    wake_times = {r.get("event_id"): r["ts"] for r in _m_decisions.cost_rows() if r["kind"] == "coordinator_wake"}
    if any(x.get("done_event_id") and x.get("done_wake_started", wake_times.get(x["done_event_id"], 0)) >= t.get("created", 0)
           for x in [t] + sib):
        return
    event = _m_wake.queue_task_webhook(t, "done", summary=step_done_summary(t, sib))
    if event:
        t["done_event_id"] = event
        t["done_wake_started"] = _m_state.now()


def step_done_summary(t, sib):
    tasks = sorted([t] + sib, key=lambda x: x["name"])
    names = ", ".join(x["name"] for x in tasks)
    outcomes = "; ".join("%s: %s" % (status, ", ".join(x["name"] for x in tasks if x["status"] == status) or "none")
                         for status in ("done", "failed", "cancelled"))
    return ("NRP plan step %s (plan %s) finished: tasks %s. %s. Check results and the plan's done-when before continuing. Look: %s" %
            (t["on_done"]["from_step"], t["on_done"]["plan"], names, outcomes,
             "; ".join("`nrp-monitor task show %s`" % x["name"] for x in tasks)))[:1600]


def step_siblings(t, include_cancelled=False):
    """The other tasks bound to the same plan step as task `t` (from the plan's ledger), as loaded task dicts; cancelled ones do not count."""
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    od = t["on_done"]
    out = []
    for e in _m_plans.plan_state(od["plan"])["ledger"].get(od["from_step"]) or []:
        o = _m_state.task_load(e["task"]) if e["task"] != t["name"] else None
        if o and (include_cancelled or o.get("status") != "cancelled") and o.get("on_done") and o["on_done"].get("from_step") == od["from_step"]:
            out.append(o)
    return out


def continuation_covers(c, t):
    return (c.get("state") == "running" or
            (c.get("state") == "closed" and c.get("status") in ("CONTINUED", "WAITING")
             and c.get("started", -1) >= t.get("created", 0)))

# Plans idle since before the fallback shipped are not woken (no burst into old chats); new activity re-arms them.
FALLBACK_SINCE = 1794674429  # 2026-11-14 install


def process_plan_fallbacks(a):
    """One backup coordinator check-in per idle period; external activity resets it."""
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plan_commands as _m_plan_commands  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    if a.dry_run:
        return
    rows = _m_decisions.cost_rows()
    for pid in _m_plan_commands.plan_names():
        with _m_state.state_lock():
            st, h = _m_plans.plan_state(pid), _m_plans.plan_header(pid) or {}
            if st.get("owner_wait") or st["status"] not in ("running", "waiting") or h.get("fallback") == "off":
                continue
            tasks = [t for n in _m_state.task_names() for t in [_m_state.task_load(n)]
                     if t and (t.get("on_done") or {}).get("plan") == pid]
            if not tasks or any(t["status"] not in ("done", "failed", "cancelled") or
                    (t.get("continuation") or {}).get("state") == "running" for t in tasks):
                continue
            targets = [t for t in tasks if _m_wake.wake_target(t)]
            if not targets:
                continue
            names = {t["name"] for t in tasks}
            relevant = [r for r in rows if r.get("task") in names]
            latest_registration = max(t.get("created", 0) for t in tasks)
            delivered = {r.get("event_id") for r in relevant if r["kind"] == "coordinator_result"
                         and r["ts"] >= latest_registration}
            # Both explicit stop wakes and group summaries can deliver a current planned stop.
            stop_delivered = any(any(eid and eid in delivered for eid in
                [t.get("stop_event_id")] + list(t.get("group_wakes", {}).values())) and any(
                step in h.get("stops", []) for step, _ in _m_plans.next_steps(h, t["on_done"]["from_step"])[1])
                for t in tasks)
            if st["status"] == "waiting" and stop_delivered:
                continue  # existing plan-wait digest retains these owner waits
            terminal = max(t.get("terminal_at", t.get("finished", t.get("created", 0))) for t in tasks)
            activity = max([terminal, st.get("activity_at", 0), _m_state.parse_ts(h.get("synced")) or 0] + [t.get("created", 0) for t in tasks] +
                           [e.get("t", 0) for entries in st["ledger"].values() for e in entries] +
                           [r["ts"] for r in relevant if r["kind"] == "wake_review" or
                            (r["kind"] == "coordinator_result" and r.get("wake_kind") != "plan-fallback")])
            if activity < FALLBACK_SINCE:
                continue
            idle = _m_state.now() - activity
            if idle < h.get("fallback_hours", 3) * 3600:
                continue
            period = st.get("fallback_period", {})
            if period.get("activity") != activity:
                period = {"activity": activity, "count": 0}
            if period["count"]:
                continue
            t = max(targets, key=lambda t: t.get("terminal_at", t.get("finished", t.get("created", 0))))
            summary = ("Plan %s idle %.1f h: all tasks finished (%s); approved through %s, stops %s; started steps %s. "
                       "Check results and continue the approved plan, or record why it waits (nrp-monitor wake-review %s ...). "
                       "If blocked on the owner: nrp-monitor plan needs-owner %s --reason TEXT." %
                       (pid, idle / 3600, "; ".join("%s: %s/%s" % (x["name"], x["status"],
                        (x.get("continuation") or {}).get("status", "unchecked")) for x in tasks),
                        h.get("approved_through"), ",".join(h.get("stops", [])) or "none", ",".join(st["ledger"]), t["name"], pid))
            event = _m_wake.queue_task_webhook(t, "plan-fallback", summary=summary)
            if event:
                _m_state.task_write(t)
                period.update(count=period["count"] + 1, last=_m_state.now())
                st["fallback_period"] = period
                _m_plans.pev(st, "plan-fallback " + summary)
                _m_notify.write_json(_m_plans.plan_dir(pid) / "state.json", st)
                _m_decisions.cost_event(t["name"], "plan-fallback", "coordinator", "done", plan=pid, event_id=event)
                _m_notify.digest("plan-fallback", summary, t["name"])


def skip_closed_continuation(n):
    """Record a late completion once without launching another plan step."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    def record(t):
        if t.get("continuation"):
            return
        t["continuation"] = {"state": "closed", "status": "PLAN-CLOSED", "closed": _m_state.now()}
        _m_state.tev(t, "plan closed; continuation skipped")
    _m_state.task_txn(n, record)


def process_continuations(a, st=None):
    from . import continuation as _m_continuation  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    for n in _m_state.task_names():
        t = _m_state.task_load(n)
        if not t or t.get("status") != "done" or not t.get("on_done"):
            continue
        if _m_plans.plan_state(t["on_done"]["plan"])["status"] == "closed":
            if not a.dry_run:
                skip_closed_continuation(n)
            continue
        c = t.get("continuation")
        if c and c.get("state") == "running" and _m_state.now() - c.get("started", _m_state.now()) > _m_state.CONT_STALE_S and not a.dry_run:
            _m_continuation.close_continuation(n, "FAILED", "the continue agent never returned (pass crashed or timed out)")
            continue
        if c:
            continue
        sib = step_siblings(t)
        waiting = [x for x in sib if x["status"] in _m_state.TASK_LIVE + _m_state.TASK_HELD]
        if waiting and completion_policy(t) == "task" and not a.dry_run:  # legacy: one continuation per step
            names = ", ".join(x["name"] for x in waiting)
            if t.get("step_waits_for") != names:
                _m_state.task_txn(n, lambda t: (t.update(step_waits_for=names), _m_state.tev(t, "step %s is not done: waiting for task(s) %s" % (t["on_done"]["from_step"], names))))
            continue
        covered = [x["name"] for x in sib if continuation_covers(x.get("continuation") or {}, t)]
        if covered and completion_policy(t) == "task" and not a.dry_run:  # group/digest: each task gets its result check
            _m_state.task_txn(n, lambda t: (t.update(continuation={"state": "closed", "status": "COVERED", "line": "step %s continued by task %s" % (t["on_done"]["from_step"], covered[0]), "closed": _m_state.now()}),
                                   _m_state.tev(t, "step %s continued by task %s" % (t["on_done"]["from_step"], covered[0]))))
            continue
        try:
            _m_continuation.continue_task(n, a)
        except Exception as e:
            _m_state.log("plan continuation %s error: %s: %s" % (n, type(e).__name__, str(e)[:200]))

    process_group_wakes(a)
    process_plan_fallbacks(a)


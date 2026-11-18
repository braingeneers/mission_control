"""NRP monitor plan_commands (mechanical extraction; R3a)."""
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


def cmd_plan_needs_owner(a):
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not _m_plans.plan_header(a.id):
        sys.exit("no plan %s" % a.id)
    reason = a.reason.strip()
    if len(reason) < 8:
        sys.exit("--reason: say what the owner must decide (at least a short sentence)")
    by = getattr(a, "by", None) or os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CODEX_THREAD_ID") or "cli"
    count = []
    def wait(st):
        if st["status"] == "closed":
            sys.exit("plan %s is closed" % a.id)
        if st.get("owner_wait"):
            sys.exit("plan %s already waits on the owner: %s" % (a.id, st["owner_wait"]["reason"]))
        st.update(status="waiting", since=_m_state.now(), reason=reason,
                  owner_wait={"reason": reason, "since": _m_state.now(), "by": by},
                  owner_wait_count=st.get("owner_wait_count", 0) + 1)
        count.append(st["owner_wait_count"])
        _m_plans.pev(st, "needs the owner (by %s): %s" % (by, reason))
    _m_plans.plan_txn(a.id, wait)
    _m_notify.digest("plan-wait", "plan %s needs the owner: %s" % (a.id, reason))
    # Keep the continuation command ahead of the reason: push bounds its text.
    _m_notify.push("Plan %s needs the owner; continue with `nrp-monitor plan resume %s`. Reason: %s" %
         (a.id, a.id, reason), "plan-owner:%s:%d" % (a.id, count[0]))
    print("plan %s now waits on the owner; sent one DM. Reason: %s. Continue with `nrp-monitor plan resume %s`" % (a.id, reason, a.id))
    return 0


def cmd_plan_resume(a):
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not _m_plans.plan_header(a.id):
        sys.exit("no plan %s" % a.id)
    def resume(st):
        if not st.get("owner_wait"):
            sys.exit("plan %s has no owner wait" % a.id)
        if st["status"] == "closed":
            sys.exit("plan %s is closed" % a.id)
        st.pop("owner_wait")
        st.update(status="running", since=_m_state.now(), reason="", activity_at=_m_state.now())
        _m_plans.pev(st, "owner wait cleared by plan resume" + (": " + a.note if a.note else ""))
    _m_plans.plan_txn(a.id, resume)
    _m_notify.digest("plan-resume", "plan %s resumed%s" % (a.id, ": " + a.note if a.note else ""))
    print("plan %s resumed; idle check-in re-armed from now" % a.id)
    return 0


def cmd_plan_sync(a):
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    path, _, pid = a.ref.partition("#")
    try:
        h = _m_plans.plan_sync(path, pid, reopen=a.reopen)
    except _m_state.ChainError as e:
        sys.exit("plan refused: %s" % e)
    print("plan %s synced: steps %s; approved through %s; stops for the owner %s; auto-continue is %s"
          % (pid, ", ".join(h["steps"]), h["approved_through"], ", ".join(h["stops"]) or "none", "on" if _m_plans.on_done_enabled() else "OFF"))
    return 0


def cmd_plan_close(a):
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not a.why.strip():
        sys.exit("plan close requires a non-empty --why")
    if not _m_plans.plan_header(a.id):
        sys.exit("no plan %s" % a.id)
    with _m_state.state_lock():
        live = [t["name"] for n in _m_state.task_names() for t in [_m_state.task_load(n)]
                if t and (t.get("on_done") or {}).get("plan") == a.id and
                (t["status"] not in ("done", "failed", "cancelled") or
                 (t.get("continuation") or {}).get("state") == "running")]
        if live and not a.force:
            sys.exit("plan close refused: live tasks or running continuations: %s; use --force to close without cancelling them" % ", ".join(live))
        st = _m_plans.plan_state(a.id)
        st.update(status="closed", since=_m_state.now(), reason=a.why.strip(), closed_at=_m_state.now())
        _m_plans.pev(st, "closed: %s%s" % (a.why.strip(), "; forced with live tasks: " + ", ".join(live) if live else ""))
        _m_notify.write_json(_m_plans.plan_dir(a.id) / "state.json", st)
    print("plan %s [closed]: %s" % (a.id, a.why.strip()))
    if live:
        print("Live tasks left unchanged: " + ", ".join(live))
    return 0


def plan_names():
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return sorted(p.parent.name for p in _m_state.PLANS.glob("*/header.json")) if _m_state.PLANS.is_dir() else []


def plan_line(pid):
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    h, st = _m_plans.plan_header(pid) or {}, _m_plans.plan_state(pid)
    owner = st.get("owner_wait")
    return ("owner wait since %s (by %s): %s; " % (_m_state.iso(owner["since"]), owner["by"], owner["reason"]) if owner else "") + "%s [%s] approved through %s; stops %s; %s%s" % (pid, st["status"], h.get("approved_through", "?"),
           ", ".join(h.get("stops") or []) or "none", "started: " + ", ".join(
           "%s=%s" % (s, e[-1]["task"]) for s, e in st["ledger"].items()) if st["ledger"] else "nothing started",
           ("; %s: " % ("closed" if st["status"] == "closed" else "waiting") + st["reason"]) if st.get("reason") else "") + (
           "; night code to review: " + ", ".join("%s@%s (%s)" % (c["branch"], c["commit"][:8], c["clone"]) for c in st["code"]) if st.get("code") else "")


def cmd_plan_list(a):
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    names = plan_names()
    print("auto-continue is %s (%s)" % ("on" if _m_plans.on_done_enabled() else "OFF", _m_state.ON_DONE_FLAG))
    for pid in names:
        print("- " + plan_line(pid))
    if not names:
        print("no plans")
    return 0


def cmd_plan_show(a):
    from . import plan_wakes as _m_plan_wakes  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not _m_plans.plan_header(a.id):
        sys.exit("no plan %s" % a.id)
    print(plan_line(a.id))
    h = _m_plans.plan_header(a.id)
    print("wake policy: " + h.get("wake", "task"))
    for group, steps in h.get("groups", {}).items():
        members = _m_plan_wakes.group_members(a.id, group, h)
        print("group %s steps=%s wake=%s ready=%s members=%s" % (group, ",".join(steps),
              h.get("wake_overrides", {}).get(group, h.get("wake", "task")), _m_plan_wakes.group_ready(h, group, members),
              ", ".join(t["name"] + ":" + t["status"] for t in members) or "unregistered"))
    d = _m_plans.plan_dir(a.id)
    print("plan text: %s\nresults: %s" % (d / "plan.md", d / "results.md"))
    for e in _m_plans.plan_state(a.id)["events"][-12:]:
        print("  . " + e)
    return 0


"""NRP monitor task_agents (mechanical extraction; R3a)."""
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


def task_prompt(t):
    from . import config as _m_config  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    f = t["failure"] or {}
    tpl = (_m_state.TPL / "task_agent.md").read_text()
    att = t["attempts"]
    cls_used = _m_ladder.class_retries(t, f)
    code = t.get("code") or {}
    rep = {"name": t["name"], "goal": t["goal"], "approved": t["approved"], "origin": _m_wake.origin_plain(t.get("origin")), "ns": t["namespace"], "notes": t["notes"] or "(none)",
           "used": str(len(att[t.get("budget_from", 0):])), "max": str(t["max_retries"]), "cls": f.get("cls", "?"),
           "cls_used": str(cls_used), "cls_max": str(_m_state.failure_class(f.get("cls"))["budget"]), "stage": f.get("stage", "?"),
           "job": f.get("job", "?"), "sig": f.get("sig", "?"), "rule": f.get("rule") or "not recorded", "waiver_max": str(_m_config.util_waiver_max()), "waiver_hours": "%g" % _m_config.util_waiver_hours(), "detail": f.get("detail", ""), "logs": f.get("logs") or "(none saved)",
           "dir": str(_m_state.task_dir(t["name"])),
           "stages": "\n".join("  - %s job=%s state=%s attempt=%d manifest=%s done_s3=%s" % (s["id"], s["job"], s["state"], s.get("attempt", 1),
                                s["manifest"], ", ".join(s["done_s3"])) for s in t["stages"]),
           "attempts": "\n".join("  - %s attempt failed [%s] %s -> fix: %s" % (x["job"], x["cls"], x["detail"][:150], x["fix"][:150]) for x in att) or "  (none)",
           "util": "\n".join("  - " + u for u in t.get("util", [])[-5:]) or "  (none)",
           "clone": code.get("clone", "(no code clone registered: fix only the manifest)"), "branch": code.get("branch", "-"),
           "subdir": code.get("subdir") or ".", "skip_limit": _m_config.skip_limit_text(),
           "triage": f.get("triage_text") or "(Tier 1 did not run for this failure)"}
    for k, v in rep.items():
        tpl = tpl.replace("{%s}" % k, v)
    return tpl.replace("{handoff}", _m_wake.handoff_prompt(t)) + _m_decisions.failure_context(t)                 # last: the handoff text is not itself a template


def run_task_agent(n, prompt_text, a, kind="fix"):
    from . import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import util as _m_util  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    if kind in ("fix", "deputy", "triage") and _m_ladder.terminal_task(n):
        return "DONE: task is terminal", []
    t = _m_state.task_load(n)
    ctx = dict(t.get("failure") or t.get("util_event") or {}) if kind in ("fix", "deputy") else {}            # what the fix agent was started for (a resubmit clears the failure)
    d = str(_m_state.task_dir(n)).rstrip("/")
    allowed = ["Bash(nrp-task:*)", "Read(/%s/**)" % d, "Edit(/%s/**)" % d]
    if t.get("code"):
        c = t["code"]["clone"].rstrip("/")
        allowed += ["Read(/%s/**)" % c, "Edit(/%s/**)" % c]
    if kind == "continue":                                         # reads outputs and the plan, writes the next TASK file
        pd = str(_m_plans.plan_dir(t["on_done"]["plan"])).rstrip("/")
        allowed = ["Bash(nrp-task:*)", "Read(/%s/**)" % d, "Read(/%s/**)" % pd, "Write(/%s/work/**)" % pd, "Edit(/%s/work/**)" % pd]
    elif kind == "deputy" and (t.get("on_done") or {}).get("plan"):
        allowed += ["Read(/%s/**)" % str(_m_plans.plan_dir(t["on_done"]["plan"])).rstrip("/")]
    elif kind == "triage":                                         # Tier 1: judge, read-only; its verdict is the last line of its answer
        allowed = ["Bash(nrp-task %s:*)" % c for c in ("show", "logs", "describe", "util", "s3")] + ["Read(/%s/**)" % d]
    elif kind not in ("fix", "deputy"):
        allowed = ["Bash(nrp-task:*)", "Read(/%s/**)" % d]
    deny = []
    if kind == "continue":                                         # night code lives in work/code-<step>/: its .git is not the agent's to edit
        deny = ["Write(/%s/work/**/.git/**)" % pd, "Edit(/%s/work/**/.git/**)" % pd]
    cmd = _m_agents.agent_cmd("triage" if kind == "triage" else "deputy" if kind == "deputy" else "task", allowed, json_out=True, deny=deny)
    if kind != "deputy" and not _m_agents.agents_available():                 # deputy has its own configured backends
        return _m_agents.unavailable_text(), []
    env = _m_agents.clean_env()
    env["NRP_TASK"] = n
    env["NRP_MONITOR_AGENT_ROLE"] = kind
    cwd = _m_state.WORK / "task"
    _m_state.task_txn(n, lambda t: (t.update(agent_started=_m_state.now()), t.pop("report", None), t.pop("util_ok_claim", None)))
    _m_state.log("task %s: %s agent start" % (n, kind))
    originals = _m_task_registry.agent_manifest_checkpoint(n) if kind in ("fix", "deputy", "continue") else None
    rejection_count = len(t.get("manifest_rejections", []))
    try:
        runner, status, out, _, _ = _m_agents.dispatch_agent(cmd.spec, prompt_text, cwd, None, env,
                                                   on_failover=lambda m: _m_state.task_txn(n, lambda t: _m_state.tev(t, m)))
    finally:
        if originals is not None:
            _m_task_registry.validate_agent_manifests(n, originals)
    rejected = (_m_state.task_load(n).get("manifest_rejections") or [])[rejection_count:]
    if originals is not None and not rejected:
        _m_task_registry.agent_manifest_checkpoint(n)
    if rejected:
        status = "error"
        out = json.dumps({"is_error": True, "result": "ESCALATE: manifest edit rejected: " + "; ".join(rejected)})
        _m_ladder.to_coordinator(n, "agent manifest fix failed: " + "; ".join(rejected), a, deputy=False)
    if status == "unavailable":                                    # the last runner ran out mid-call
        _m_state.task_txn(n, lambda t: t.pop("agent_started", None))
        return out, []
    if status == "timeout":
        out = ""
    try:
        res = json.loads(out)
        full = str(res.get("result") or "")
    except ValueError:
        res = {"result": (out.strip().splitlines() or ["AGENT EMPTY or TIMEOUT"])[-1], "is_error": True}
        full = out
    den = res.get("permission_denials") or []
    line = " ".join(str(res.get("result") or "").split())[:400]
    if kind in ("fix", "deputy") and not res.get("is_error") and status == "ok":
        # Explanatory prose and HANDOFF_ENTRY blocks are not the outcome.
        answer = full.split("HANDOFF_ENTRY:", 1)[0]
        verdicts = re.findall(r"(?m)^\s*(?:\*\*)?((?:RESOLVED|DONE|ESCALATE|STOPPED|NOT-DONE|RESUBMITTED|UTIL_OK)\b[^\n]*)", answer)
        if verdicts:
            line = " ".join(verdicts[-1].split())[:400]
    claim = _m_util.util_ok_extract(full) if kind == "fix" else None
    if claim is not None:
        _m_state.task_txn(n, lambda t: t.update(util_ok_claim=claim))                  # the script decides on it in handle_failure
    rec = {"ts": _m_state.now(), "kind": kind, "runner": runner, "model": res.get("model"), "usage": res.get("usage"), "cost": res.get("total_cost_usd"), "turns": res.get("num_turns"), "result": line, "denials": len(den)}
    failure = t.get("failure") or t.get("util_event") or {}
    current = _m_state.task_load(n)
    tier = "1" if kind == "triage" else "deputy" if kind == "deputy" else "2"
    _m_decisions.cost_event(n, {"fix": "fixer", "continue": "continue_agent"}.get(kind, kind), tier,
               "resolved" if failure and kind != "triage" and not current.get("failure") and not current.get("util_event") else "stopped" if status != "ok" else "escalated" if failure else "done",
               stage=failure.get("stage"), runner=runner, model=(res.get("model") or _m_agents.tier_settings(cmd.spec["tier"], runner)["model"]) if runner else None,
               result=res, fingerprint=failure.get("fingerprint") or (_m_decisions.fingerprint(t, failure) if failure else None))
    if kind == "triage":
        rec["verdict"], rec["verdict_text"] = _m_ladder.triage_verdict(full)
    _m_state.task_txn(n, lambda t: (t.setdefault("agent_runs", []).append(rec), t.pop("agent_started", None)))
    _m_state.log("task %s: agent done cost=%s denials=%d: %s" % (n, rec["cost"], len(den), line[:250]))
    try:
        _m_wake.handoff_record(n, kind, full, rec, ctx)                         # no-op without a handoff; only fix / continue agents add to it
    except Exception as e:
        _m_state.log("task %s: handoff entry not written: %s: %s" % (n, type(e).__name__, str(e)[:200]))
    for x in den[:5]:
        _m_notify.digest("fault", "agent permission denied (monitor fault, not a job failure): %s %s"
               % (x.get("tool_name"), json.dumps(x.get("tool_input"))[:200]), n)
    return line, den


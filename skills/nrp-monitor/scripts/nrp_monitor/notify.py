"""NRP monitor notify (mechanical extraction; R3a)."""
import collections
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

# ---- notifications -------------------------------------------------------------------------------------------
def notify(msg, state=None, key=None, dry=False, ref="-"):
    """v2 (owner decision 2026-11-05): routine events are SILENT and go to the digest; push() is the one interruption.
    With key, repeats within NOTIFY_DEDUPE_S are dropped. `ref` names the owning registration for the digest."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    msg = " ".join(msg.split())[:400]
    if dry:
        print("[dry-run] would notify: " + msg)
        return
    if state is not None and key:
        if _m_state.now() - state["notified"].get(key, 0) < _m_state.NOTIFY_DEDUPE_S:
            return
        state["notified"][key] = _m_state.now()
    _m_state.log("notify: " + msg)
    digest("event", msg, ref)


def read_json(p, default):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


def write_json(p, d):
    tmp = Path(str(p) + ".tmp")
    tmp.write_text(json.dumps(d, indent=1, sort_keys=True))
    os.replace(tmp, p)


def digest(kind, msg, task="-"):
    """Silent record for the digest (`nrp-monitor digest`, daily file, SessionStart line)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    msg = " ".join(str(msg).split())[:500]
    _m_state.STATE.mkdir(parents=True, exist_ok=True)
    with open(_m_state.DIGEST, "a") as f:
        f.write(json.dumps({"t": _m_state.iso(), "kind": kind, "task": task, "msg": msg}) + "\n")
    _m_state.log("digest %s %s: %s" % (kind, task, msg))


def slack_dm(text):
    """Send `text` (already composed and escaped by slack_text) as the owner's DM."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not _m_state.SLACK_USER:
        _m_state.log("slack dm: slack_user_id is not set in %s/config.json; falling back to the other channels" % _m_state.STATE)
        return False
    try:
        import urllib.request
        tok = json.loads(_m_state.JWT_FILE.read_text())["access_token"]
        req = urllib.request.Request(_m_state.SLACK_URL, data=json.dumps({"user_id": _m_state.SLACK_USER, "text": text}).encode(),
                                     headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            ok = json.loads(r.read().decode()).get("status") == "delivered"
        _m_state.log("slack dm: %s" % ("delivered" if ok else "not delivered"))
        return ok
    except Exception as e:
        _m_state.log("slack dm failed: %s" % str(e)[:120])            # never log the token
        return False


def claude_push(msg):
    """PushNotification from a headless agent: reaches the owner's phone when a Remote Control session is open."""
    from . import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    prompt = ("Call the PushNotification tool exactly once with status \"proactive\" and this message, verbatim: %s\n"
              "Then reply with only the tool result text." % json.dumps(msg))
    try:
        r = subprocess.run(["claude", "-p", "--model", "haiku", "--max-turns", "3", "--max-budget-usd", "0.20",
                            "--permission-mode", "dontAsk", "--no-session-persistence", "--allowedTools", "PushNotification"],
                           input=prompt, capture_output=True, text=True, cwd=str(_m_state.WORK), env=_m_agents.clean_env(), timeout=180)
        out = r.stdout.strip()
    except Exception as e:
        out = "error %s" % e
    _m_state.log("claude push: %s" % out[:150])
    return bool(out) and "not sent" not in out.lower() and "error" not in out.lower()


def banner(msg, title="NRP: needs you"):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    try:
        subprocess.run(["osascript", "-e", "on run argv", "-e", "display notification (item 1 of argv) with title (item 2 of argv)",
                        "-e", "end run", msg, title], capture_output=True, timeout=20)
    except Exception as e:
        _m_state.log("osascript failed: %s" % str(e)[:80])


def push(msg, key, dry=False, refs=None):
    """The ONE interruption: Slack DM to the owner + Claude push; a macOS banner only when both fail. Once per key.
    `refs` = the registrations the alert is about ('task:NAME', 'chain:NAME', 'job:NAME'); their origin chat is named first in
    every channel. No refs = a shared/system alert that no single chat owns."""
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    msg = " ".join(msg.split())[:300]
    refs = list(refs or [])
    tag = _m_wake.short_tag(refs)
    if dry:
        print("[dry-run] would PUSH: " + tag + msg)
        print("[dry-run] Slack text:\n" + _m_wake.slack_text(msg, refs))
        return False
    def claim(sent):
        if key in sent:
            return False
        sent[key] = {"t": _m_state.iso(), "msg": tag + msg, "origin": [_m_wake.origin_plain(*_m_wake.lookup_origin(r)) for r in refs] or ["shared"]}
    if not _m_state.json_txn(lambda: read_json(_m_state.PUSHED, {}), claim,
                             lambda sent: write_json(_m_state.PUSHED, sent)):
        return False
    ledger_task = refs[0].split(":", 1)[-1] if len(refs) == 1 else "shared"
    task_failure = ((_m_state.task_load(ledger_task) or {}).get("failure") or {}) if len(refs) == 1 and refs[0].startswith("task:") else {}
    _m_decisions.cost_event(ledger_task, "owner_dm", "owner", "escalated", notification_key=key,
               stage=task_failure.get("stage"), fingerprint=task_failure.get("fingerprint"))
    _m_state.log("PUSH [%s] %s%s" % (key, tag, msg))
    digest("push", tag + msg, refs[0] if len(refs) == 1 else "-")
    if os.environ.get("NRP_MONITOR_NO_PUSH"):                 # tests: no Slack, no Claude; the (fake) banner records it
        banner(tag + msg, "NRP test push")
        return True
    ok_s, ok_c = slack_dm(_m_wake.slack_text(msg, refs)), claude_push((tag + msg)[:190])
    if not (ok_s or ok_c):
        banner(tag + msg)
    return True


def push_clear(key):
    """Re-arm a push key once its condition has cleared (account alarm, kubectl failing)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    def clear(sent):
        if sent.pop(key, None) is None:
            return False
    _m_state.json_txn(lambda: read_json(_m_state.PUSHED, {}), clear,
                      lambda sent: write_json(_m_state.PUSHED, sent))


def jwt_days_left():
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    try:
        import base64
        tok = json.loads(_m_state.JWT_FILE.read_text())["access_token"]
        p = json.loads(base64.urlsafe_b64decode(tok.split(".")[1] + "=="))
        return (p["exp"] - _m_state.now()) / 86400
    except Exception:
        return None

# ---- digest ------------------------------------------------------------------------------------------------------
def needs_owner():
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    out = []
    for n in _m_state.task_names():
        t = _m_state.task_load(n)
        if t and t["status"] == "NEEDS_OWNER":
            out.append((n, t))
    return out


def coordinating():
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return [(n, t) for n in _m_state.task_names() for t in [_m_state.task_load(n)] if t and t["status"] == "WITH_COORDINATOR"]


def ref_label(ref):
    """'task-name · origin title' for digest lines (looked up now, so a backfilled origin also labels old events)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not ref or ref == "-":
        return ""
    o, _ = _m_wake.lookup_origin(ref)
    return "[%s \u00b7 %s]" % (ref, (o or {}).get("title") or (o or {}).get("link") or _m_state.ORIGIN_MISSING)


def render_digest(hours):
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plan_commands as _m_plan_commands  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    cut = _m_state.now() - hours * 3600
    rows = []
    if _m_state.DIGEST.exists():
        for l in _m_state.DIGEST.read_text().splitlines():
            try:
                r = json.loads(l)
                if datetime.fromisoformat(r["t"]).timestamp() >= cut:
                    rows.append(r)
            except Exception:
                pass
    lines = ["# nrp-monitor digest, last %dh (%s)" % (hours, _m_state.iso()),
             "Sent by the monitor script, not by one chat: each task/chain below names the chat that owns it (origin) when recorded."]
    lines.extend(_m_cluster.bad_node_lines())
    from . import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    blocked = _m_agents.blocked_text()
    if blocked:                                # session-start status shows this only in the main chat; the digest keeps it for all
        lines.append("Agent runners blocked: %s%s  (`nrp-monitor agents`)" % (blocked, "" if _m_agents.agents_available() else "; NO runner left, agent work is waiting"))
    nh = needs_owner()
    owner_plans = [(p, _m_plans.plan_state(p)["owner_wait"]) for p in _m_plan_commands.plan_names() if _m_plans.plan_state(p).get("owner_wait")]
    lines.append("\n## Needs the owner (%d)" % (len(nh) + len(owner_plans)))
    lines += ["- %s (%s): %s  -> `nrp-monitor task show %s`" % (n, _m_wake.origin_plain(t.get("origin"), "goal: " + t.get("goal", "")[:60]),
                                                               t.get("reason", "")[:300], n) for n, t in nh]
    lines += ["- plan %s (since %s): %s -> `nrp-monitor plan show %s`" % (p, _m_state.iso(w["since"]), w["reason"], p) for p, w in owner_plans]
    if not nh and not owner_plans:
        lines.append("- nothing")
    co = coordinating()
    lines.append("\n## With the coordinator chat, owner not notified (%d)" % len(co))
    lines += ["- %s (%s) for %s: %s  -> `nrp-monitor task show %s`" % (n, _m_wake.origin_plain(t.get("origin"), "goal: " + t.get("goal", "")[:60]),
                                                                        _m_state.ago(t.get("coordinator_since", _m_state.now())), t.get("reason", "")[:300], n) for n, t in co] or ["- nothing"]
    live = [(n, _m_state.task_load(n)) for n in _m_state.task_names()]
    live = [(n, t) for n, t in live if t and t["status"] in _m_state.TASK_LIVE]
    lines.append("\n## Running tasks (%d)" % len(live))
    lines += ["- %s [%s] %s  (%s)" % (n, t["status"], ", ".join("%s=%s" % (s["id"], s["state"]) for s in t["stages"]),
                                  _m_wake.origin_plain(t.get("origin"))) for n, t in live] or ["- none"]
    pl = _m_plan_commands.plan_names()
    if pl:
        wait = [p for p in pl if _m_plans.plan_state(p)["status"] == "waiting"]
        lines.append("\n## Plans (auto-continue %s): %d waiting on the owner" % ("on" if _m_plans.on_done_enabled() else "OFF", len(wait)))
        lines += ["- " + _m_plan_commands.plan_line(p) for p in wait + [p for p in pl if p not in wait]]
        night = [r for r in rows if r["kind"].startswith("plan-") or r["kind"] in ("task-done", "result")]
        if night:
            lines.append("Finished, started and stopped in this window:")
            lines += ["- %s %s" % (r["t"][5:16], r["msg"][:260]) for r in night[-20:]]
    # Pending history stays on disk; show each stage's current wait once.
    for n in _m_state.task_names():
        t = _m_state.task_load(n)
        if not t or t["status"] not in _m_state.TASK_LIVE + _m_state.TASK_HELD:
            continue
        for stage in t["stages"]:
            report = stage.get("pending_report")
            if report and stage["state"] == "running" and not stage.get("pod_started"):
                since = (stage.get("queue_wait") or {}).get("since", stage.get("submitted", _m_state.now()))
                lines.append("- %s stage %s Pending %s: %s" % (n, stage["id"], _m_state.ago(since), report["reason"]))
    rows = [r for r in rows if r["kind"] != "pending"]
    cnt = collections.Counter(r["kind"] for r in rows)
    lines.append("\n## Events: " + (", ".join("%s %d" % kv for kv in sorted(cnt.items())) or "none"))
    for r in rows[-60:]:
        lines.append("- %s %-12s %s %s" % (r["t"][5:16], r["kind"], ref_label(r["task"]), r["msg"][:260]))
    days = jwt_days_left()
    if days is not None and days < 7:
        lines.append("\nSlack token expires in %.1f days: renew ~/.ssh/braingeneers_jwt_token.json (mission-control skill)." % days)
    return "\n".join(lines) + "\n"


def cmd_digest(a):
    print(render_digest(a.hours), end="")
    return 0


def daily_digest(a):
    from . import plan_commands as _m_plan_commands  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if a.dry_run or datetime.now().hour < 8:
        return
    p = _m_state.STATE / "digests" / ("%s.md" % datetime.now().strftime("%Y-%m-%d"))
    if p.exists():
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_digest(24))
    _m_state.log("daily digest written: %s" % p)
    wait = [x for x in _m_plan_commands.plan_names() if _m_plans.plan_state(x)["status"] == "waiting"] if _m_plans.on_done_enabled() else []
    if wait:
        push("Morning: %d plan(s) wait on you: %s  (nrp-monitor digest)" % (len(wait), "; ".join(
             "%s: %s" % (x, _m_plans.plan_state(x).get("reason", "")[:90]) for x in wait)), "morning:" + datetime.now().strftime("%Y-%m-%d"))


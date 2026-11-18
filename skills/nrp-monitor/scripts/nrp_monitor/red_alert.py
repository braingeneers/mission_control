"""NRP monitor red_alert (mechanical extraction; R3a)."""
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


def red_alert():
    """The active RED ALERT record, or {} when NRP accepts new pods."""
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return _m_notify.read_json(_m_state.RED_ALERT, {}).get("active") or {}


def red_alert_enter(ns, msg, source):
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    with _m_state.state_lock():
        st = _m_notify.read_json(_m_state.RED_ALERT, {})
        if st.get("active"):
            return False
        last = st.get("last") or {}
        keep = last if _m_state.now() - last.get("cleared", 0) < _m_state.RED_REUSE_S else {}
        st["active"] = {"id": keep.get("id") or "%s-%d" % (ns, _m_state.now()), "since": _m_state.now(), "ns": ns, "source": source,
                        "refusal": " ".join(msg.split())[:300], "woken": keep.get("woken", []), "notified": keep.get("notified", False)}
        _m_notify.write_json(_m_state.RED_ALERT, st)
    _m_state.log("NRP RED ALERT (%s, namespace %s): %s. ALL submits are held until NRP's dry-run accepts again." % (source, ns, msg[:200]))
    _m_notify.digest("red-alert", "NRP is refusing new pods (%s): %s. All submits held." % (source, msg[:200]))
    return True


def red_probe(ns):
    """('ok'|'denied'|'error', text) from a server-side dry-run create: NRP's admission webhooks judge it, nothing is created."""
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    with tempfile.TemporaryDirectory(prefix="nrp-probe-") as td:
        p = Path(td) / "probe.json"
        p.write_text(json.dumps(_m_state.RED_PROBE_JOB))
        r = _m_cluster.kubectl("-n", ns, "create", "--dry-run=server", "-f", str(p), timeout=60)
    msg = (r.stderr.strip() or r.stdout.strip())[:400]
    return ("ok", "") if not r.returncode else ("denied" if _m_state.BLOCK_RE.search(msg) else "error", msg)


def red_alert_text(cur, n, mine, unknown):
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return ("NRP RED ALERT: NRP is refusing new pods on the account (namespace %s, since %s): %s. This needs action now, no exceptions. "
            "Pods listed as task %s's: %s. Resize or delete your low pods now: request = ceil(NRP Thanos whole-life working-set peak x 1.5), "
            "limit within 20%% of request (never size from a cgroup memory.peak / profile peak: it counts page cache); delete a pod that "
            "cannot be resized (resubmits wait until NRP accepts again, then the monitor sends them). If a pod listed as yours is not yours, "
            "find the real owner (Job spec S3 paths, `nrp-monitor task list` and the task registries, the registering T3 thread) and hand it "
            "off with `t3 thread send`; \"not mine\" alone is not an acceptable answer. Pods with no known owning task: %s. Every task's "
            "submits are held; the alert clears only when NRP's dry-run accepts again, \"no change\" cannot close it."
            % (cur["ns"], _m_state.iso(cur["since"]), cur["refusal"][:200], n, "; ".join(_m_cluster.offender_text(o) for o in mine) or "none",
               "; ".join(_m_cluster.offender_text(o) for o in unknown) or "none"))


def red_alert_notify(cur):
    """Once per alert: offenders -> owning task (by Job name), wake each owner's coordinator, push Hunter (unknown owners named)."""
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    try:
        offenders = _m_cluster.namespace_offenders(cur["ns"])
    except Exception as e:                                                   # retried next pass; Hunter hears once now
        _m_notify.push("NRP RED ALERT: NRP refuses new pods (%s); all submits held; the offender check failed: %s" % (cur["refusal"][:120], str(e)[:80]),
             "red-alert:%s:check" % cur["id"])
        return
    owner = {s["job"]: n for n in _m_state.task_names() for s in (_m_state.task_load(n) or {}).get("stages", [])}
    mine, unknown = {}, []
    for o in offenders:
        n = owner.get(o["owner"][4:]) if o["owner"].startswith("Job/") else None
        mine.setdefault(n, []).append(o) if n else unknown.append(o)
    woken, unreached = set(cur.get("woken", [])), []
    for n, pods in sorted(mine.items()):
        text = red_alert_text(cur, n, pods, unknown)
        ok = n in woken or (not _m_ladder.terminal_task(n) and _m_state.task_txn(n, lambda t: bool(_m_wake.queue_task_webhook(t, "red_alert", summary=text)) and
                                                                     not _m_state.tev(t, "NRP RED ALERT: coordinator woken for %d low pod(s)" % len(pods))))
        (woken.add(n) if ok else unreached.append(n))
    short = lambda os_: ", ".join("%s [%s]" % (o["pod"], o["owner"] or o["username"] or o["service_account"] or "?") for o in os_)
    text = ("NRP RED ALERT: NRP refuses new pods on the account; all submits held until its dry-run accepts. NO KNOWN OWNER: %s. "
            "Owners woken: %s.%s" % (short(unknown) or "none" if offenders else "no pod outside NRP's bands (quota?)",
                                     ", ".join(sorted(woken)) or "none", (" No chat to wake: %s." % ", ".join(unreached)) if unreached else ""))
    _m_notify.digest("red-alert", text)
    _m_notify.push(text, "red-alert:%s" % cur["id"])
    with _m_state.state_lock():
        st = _m_notify.read_json(_m_state.RED_ALERT, {})
        if (st.get("active") or {}).get("id") == cur["id"]:
            st["active"].update(notified=True, woken=sorted(woken), offenders=[o["pod"] for o in offenders])
            _m_notify.write_json(_m_state.RED_ALERT, st)


def process_red_alert(a, st):
    """Probe NRP's admission (rate-limited), enter or clear the RED ALERT, and notify once per alert. Logs every pass while held."""
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if a.dry_run:
        print("[dry-run] RED ALERT %s" % ("ACTIVE: submits held" if red_alert() else "clear"))
        return
    cur = red_alert()
    names = [n for n in _m_state.task_names() if (_m_state.task_load(n) or {}).get("status") in _m_state.TASK_LIVE + _m_state.TASK_HELD]
    nss = {cur["ns"]} if cur else {_m_state.NS} | {_m_state.task_load(n)["namespace"] for n in names}
    probed = _m_notify.read_json(_m_state.RED_ALERT, {}).get("probed", {})
    for ns in sorted(nss):
        if _m_state.now() - probed.get(ns, 0) < _m_state.RED_PROBE_S:
            continue
        verdict, msg = red_probe(ns)
        with _m_state.state_lock():
            s = _m_notify.read_json(_m_state.RED_ALERT, {})
            s.setdefault("probed", {})[ns] = _m_state.now()
            if verdict == "ok" and (s.get("active") or {}).get("ns") == ns:
                s["last"] = dict(s.pop("active"), cleared=_m_state.now())
                _m_state.log("NRP RED ALERT CLEARED: NRP's dry-run in %s accepts again; held submits resume" % ns)
                _m_notify.digest("red-alert", "cleared: NRP's dry-run accepts new pods again; held submits resume")
            _m_notify.write_json(_m_state.RED_ALERT, s)
        if verdict == "denied":
            red_alert_enter(ns, msg, "admission dry-run probe")
        elif verdict == "error":
            _m_state.log("admission probe in %s inconclusive: %s" % (ns, msg[:150]))
    cur = red_alert()
    if cur:
        _m_state.PASS["red_alert"] = 1
        _m_state.log("NRP RED ALERT active since %s (%s): all submits held" % (_m_state.iso(cur["since"]), cur["refusal"][:120]))
        if not cur.get("notified"):
            red_alert_notify(cur)


"""NRP monitor timeouts (mechanical extraction; R3a)."""
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

# ---- Tier 0 timeouts (no model): extend a progressing Job in place, credit queue time, resubmit a resume-capable stage once at 2x ----
def patch_deadline(ns, job, secs):
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    r = _m_cluster.kubectl("-n", ns, "patch", "job", job, "--type=merge", "-p", json.dumps({"spec": {"activeDeadlineSeconds": int(secs)}}))
    return r.returncode == 0, (r.stderr or r.stdout).strip()[:150]


def log_signature(ns, job):
    """Hash of the Job's last log lines: it changes between two passes only when the pod is still writing."""
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    r = _m_cluster.kubectl("-n", ns, "logs", "job/" + job, "--all-containers", "--tail=20", timeout=60)
    lines = [l for l in (r.stdout or "").splitlines() if l.strip()][-20:] if r.returncode == 0 else []
    return hashlib.sha1("\n".join(lines).encode()).hexdigest()[:16] if lines else None


def pod_waiting_error(ns, job):
    """A pod stuck on an error (image pull, bad config) is not queueing: its deadline is not extended."""
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    r = _m_cluster.kubectl("-n", ns, "get", "pods", "-l", "job-name=" + job, "-o", "json")
    for p in json.loads(r.stdout or "{}").get("items", []) if r.returncode == 0 else []:
        for cs in p.get("status", {}).get("containerStatuses", []) or []:
            w = (cs.get("state") or {}).get("waiting") or {}
            if w.get("reason") in ("ImagePullBackOff", "ErrImagePull", "InvalidImageName", "CreateContainerConfigError", "CreateContainerError"):
                return w["reason"]
    return None


def deadline_watch(n, s, info):
    """Tier 0 for one running stage whose Job is Running or Pending. activeDeadlineSeconds counts from the Job's start, Pending time
    included, so: (1) once the pod has started after a long queue, credit the queue time (deadline = original + queue wait); (2) a pod that
    is still Pending near its deadline is kept alive (deadline = elapsed + original), a limited number of times, unless it is stuck on an
    error; (3) a pod that is still progressing near its deadline (its log tail changed between two passes) gets one more original
    deadline in place, at most DEADLINE_EXT_MAX times. A Job that is not progressing is left to expire and enters the ladder."""
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    dl, js = info.get("deadline"), info.get("start")
    if not dl or not js:
        return
    ns, sid, job, t_now = _m_state.task_load(n)["namespace"], s["id"], s["job"], _m_state.now()
    d = dict(s.get("dl") or {})
    before = json.dumps(d, sort_keys=True)
    orig = d.setdefault("orig", dl)
    remaining = js + dl - t_now
    margin = min(max(0.2 * orig, 900), 3600)
    started = s.get("pod_started")
    new, why, bump, notes = None, "", None, []
    if started:
        credit = max(0, started - js)
        if "credit" not in d:
            d["credit"] = credit if credit >= _m_state.DEADLINE_CREDIT_MIN_S else 0
        want = orig + d["credit"] + d.get("exts", 0) * orig
        if want > dl:
            new, why = want, "credited %d min the pod waited Pending (it counts toward activeDeadlineSeconds)" % (d["credit"] // 60)
        elif remaining < 2 * margin:
            sig = log_signature(ns, job)
            prev, d["sig"] = d.get("sig"), sig
            moving = bool(sig and prev and sig != prev)
            if remaining < margin and moving and d.get("exts", 0) < _m_state.DEADLINE_EXT_MAX:
                new, bump = dl + orig, "exts"
                why = "still progressing (log advanced between passes): extension %d of %d" % (d.get("exts", 0) + 1, _m_state.DEADLINE_EXT_MAX)
            elif remaining < margin and moving and not d.get("capped"):
                d["capped"] = True
                notes.append("deadline in %d min and the Job still progresses, but all %d extensions were used" % (remaining // 60, _m_state.DEADLINE_EXT_MAX))
            elif remaining < margin and sig and sig == prev and not d.get("stalled"):
                d["stalled"] = True
                notes.append("deadline in %d min and the Job's log did not advance between passes: no extension" % (remaining // 60))
    elif remaining < margin and d.get("pend", 0) < _m_state.DEADLINE_PEND_EXT_MAX and (t_now - js) + orig > dl and not pod_waiting_error(ns, job):
        new, bump = (t_now - js) + orig, "pend"
        why = "pod still Pending near the deadline: kept alive (extension %d of %d)" % (d.get("pend", 0) + 1, _m_state.DEADLINE_PEND_EXT_MAX)
    if new:
        ok, err = patch_deadline(ns, job, new) if d.get("patch_fail", 0) < 3 else (False, "gave up after 3 failed patches")
        if ok:
            if bump:
                d[bump] = d.get(bump, 0) + 1
            notes.append("%s: activeDeadlineSeconds %d -> %d s, %s" % (job, dl, new, why))
            _m_notify.digest("deadline-extended", notes[-1], n)
        else:
            d["patch_fail"] = d.get("patch_fail", 0) + 1
            notes.append("%s: could not extend activeDeadlineSeconds (%s)" % (job, err))
    if notes or json.dumps(d, sort_keys=True) != before:
        def save_dl(t):
            _m_state.tstage(t, sid)["dl"] = d
            for m in notes:
                _m_state.tev(t, m)
        _m_state.task_txn(n, save_dl)


def stage_resumable(s):
    """True only when the stage says so (`resumable: true` in TASK.json) or its manifest passes an explicit skip-existing/resume flag.
    Nothing is inferred beyond that: a stage that restarts from scratch must not be resubmitted blindly."""
    if s.get("resumable") is True:
        return True
    try:
        return bool(re.search(r"--(skip-existing|resume)\b", Path(s["manifest"]).read_text()))
    except (OSError, TypeError, KeyError):
        return False


def tier0_timeout(n, f):
    """A stage died of DeadlineExceeded while running. If it resumes by skipping finished items, resubmit it once with 2x deadline
    (the task's manifest copy is edited); otherwise (or when that was already done) False: the failure enters the ladder at Tier 1."""
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import pass_ as _m_task_pass_  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = _m_state.task_load(n)
    s = _m_state.tstage(t, f["stage"])
    done = (s.get("dl") or {}).get("resubmits", 0)
    if done >= _m_state.DEADLINE_RESUBMITS_MAX or not stage_resumable(s):
        return False
    try:
        text = Path(s["manifest"]).read_text()
        doc = _m_task_registry.manifest_doc(s["manifest"])
        old = int(doc["spec"]["activeDeadlineSeconds"])
    except (OSError, KeyError, TypeError, ValueError):
        return False
    doc["spec"]["activeDeadlineSeconds"] = old * 2
    _m_task_registry.manifest_write(s["manifest"], doc)
    ok, msg = _m_task_pass_.do_submit(n, f["stage"], "Tier 0: deadline %ds passed while running and the stage resumes by skipping finished items; resubmitted with 2x deadline (%d s)" % (old, old * 2), "monitor")
    if not ok:
        Path(s["manifest"]).write_text(text)
        _m_state.log("task %s: Tier 0 resubmit refused: %s" % (n, msg[:200]))
        return False
    _m_state.task_txn(n, lambda t: _m_state.tstage(t, f["stage"]).update(dl={"resubmits": done + 1}))
    _m_decisions.cost_event(n, "rule", "0", "resolved", stage=f["stage"], fingerprint=f.get("fingerprint") or _m_decisions.fingerprint(t, f))
    _m_notify.digest("deadline-resubmit", "%s ran into its %d s deadline; resumable stage resubmitted once with %d s" % (f["job"], old, old * 2), n)
    _m_state.PASS["retries"] = _m_state.PASS.get("retries", 0) + 1
    return True


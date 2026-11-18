"""NRP monitor task/pass_ (mechanical extraction; R3a)."""
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

# ---- task pass ---------------------------------------------------------------------------------------------------
def save_task_logs(t, s, reason):
    from .. import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    ns, job = t["namespace"], s["job"]
    p = _m_state.task_dir(t["name"]) / "logs" / ("%s-a%d.txt" % (job, s.get("attempt", 1)))
    if reason != "Job succeeded" and p.exists() and p.stat().st_size > 200:
        return str(p), p.read_text()
    parts, logtxt = ["# task %s stage %s job %s attempt %d  saved %s\n# reason: %s\n" % (t["name"], s["id"], job, s.get("attempt", 1), _m_state.iso(), reason)], ""
    for title, args in (("logs (last 300 lines)", ["logs", "job/" + job, "--all-containers", "--tail=300"]),
                        ("describe job", ["describe", "job", job]),
                        ("describe pods", ["describe", "pods", "-l", "job-name=" + job])):
        try:
            r = _m_cluster.kubectl("-n", ns, *args, timeout=120)
            body = r.stdout if r.returncode == 0 else "(kubectl failed rc=%d: %s)\n%s" % (r.returncode, r.stderr.strip()[:200], r.stdout)
        except Exception as e:
            body = "(kubectl error: %s)" % str(e)[:150]
        if title.startswith("logs"):
            logtxt = body
        parts.append("\n## %s\n%s" % (title, body[-40000:]))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(parts)[-120000:])
    if reason == "Job succeeded":
        outputs = dict(re.findall(r"^([A-Z][A-Z0-9_]{2,40})=(\S+)$", logtxt, re.M))
        (p.parent / s["id"]).mkdir(exist_ok=True)
        _m_notify.write_json(p.parent / s["id"] / "outputs.json", outputs)
        _m_state.task_txn(t["name"], lambda cur: _m_state.tstage(cur, s["id"]).update(outputs=outputs))
    return str(p), logtxt


def run_postcheck(t):
    from .. import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    check = t.get("postcheck")
    if not check:
        return {"ok": True, "output": "no postcheck declared"}
    try:
        r = subprocess.run(check["cmd"], cwd=(t.get("code") or {}).get("clone") or _m_state.task_dir(t["name"]),
                           env=_m_agents.clean_env(), capture_output=True, text=True, timeout=120)
        output = (r.stdout + "\n" + r.stderr)[-16000:]
        return {"ok": r.returncode == 0 and check["expect"] in r.stdout, "rc": r.returncode, "output": output}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "output": str(e)[-2000:]}


def pod_started(ns, job):
    """Earliest container start of the Job's pods (None if no container ever ran)."""
    from .. import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    r = _m_cluster.kubectl("-n", ns, "get", "pods", "-l", "job-name=" + job, "-o", "json")
    if r.returncode:
        return None
    ts = []
    for p in json.loads(r.stdout or "{}").get("items", []):
        for cs in p.get("status", {}).get("containerStatuses", []) or []:
            for k in ("running", "terminated"):
                v = (cs.get("state") or {}).get(k) or (cs.get("lastState") or {}).get(k)
                if v and v.get("startedAt"):
                    ts.append(_m_state.parse_ts(v["startedAt"]))
    ts = [x for x in ts if x]
    return min(ts) if ts else None


def classify(t, s, logtxt):
    """(class, signature, detail) from Job conditions, pod status, exit code and the log tail. No model."""
    from .. import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from ..task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    ns, job, mem = t["namespace"], s["job"], _m_task_registry.manifest_mem(t, s)
    j = json.loads(_m_cluster.kubectl("-n", ns, "get", "job", job, "-o", "json").stdout or "{}")
    pods = json.loads(_m_cluster.kubectl("-n", ns, "get", "pods", "-l", "job-name=" + job, "-o", "json").stdout or "{}").get("items", [])
    conds = {c.get("type"): c for c in j.get("status", {}).get("conditions", []) or []}
    freason = (conds.get("Failed") or {}).get("reason", "")
    code = None
    for p in pods:
        ps = p.get("status", {})
        if ps.get("reason") == "Evicted":
            return "resources", "evicted@" + mem, "pod evicted: %s" % (ps.get("message") or "")[:200]
        for cs in (ps.get("initContainerStatuses") or []) + (ps.get("containerStatuses") or []):
            term = (cs.get("state") or {}).get("terminated") or (cs.get("lastState") or {}).get("terminated")
            wait = (cs.get("state") or {}).get("waiting") or {}
            if term and term.get("reason") == "OOMKilled":
                return "resources", "oom@" + mem, "OOMKilled at memory limit %s" % mem
            if wait.get("reason") in ("ImagePullBackOff", "ErrImagePull", "InvalidImageName", "CreateContainerConfigError",
                                      "CreateContainerError"):
                return "infra", "waiting:%s" % wait["reason"], "%s: %s" % (wait["reason"], (wait.get("message") or "")[:200])
            if term and term.get("exitCode") is not None and (code is None or code == 0):
                code = term.get("exitCode")                   # a non-zero exit (init or main container) wins over a zero one
    if freason == "DeadlineExceeded":
        dl = (j.get("spec") or {}).get("activeDeadlineSeconds") or 0
        js, ps0 = _m_state.parse_ts(j.get("status", {}).get("startTime")), s.get("pod_started")
        if not ps0 or (js and dl and ps0 - js > dl / 2):
            return "queue", "deadline-queue", "deadline %ds passed while the pod waited in the queue" % dl
        return "slow", "deadline-run", "ran %d min of its %d min deadline and did not finish (needs profiling or a design change)" % (
            ((js or ps0) + dl - ps0) // 60, dl // 60)
    lines = [l for l in (logtxt or "").splitlines() if l.strip()]
    err = next((l.strip() for l in reversed(lines[-80:]) if _m_state.EXC_RE.match(l)), "")
    last = lines[-1].strip() if lines else ""
    if code is None and not err and "Traceback" not in (logtxt or ""):
        # General rule, no list of Kubernetes reasons: our container never reported an exit and printed no traceback, so our code
        # did not fail. Node loss, NotReady/taint evictions, preemption, drains and deleted pods all land here. Retry the stage.
        return "infra", _m_state.LOST_SIG, "pod ended without an exit code or traceback from our container (node loss, eviction, " \
            "preemption or deletion)%s" % ("; Job condition %s" % freason if freason else "")
    if code == 137:
        return "resources", "137@" + mem, "exit 137 (OOM or eviction) at memory %s" % mem
    if (err or last) and _m_state.TRANSIENT_RE.search(err or last):
        return "infra", "transient:" + _m_state.norm_sig(err or last), "transient error: %s" % (err or last)[:200]
    if err or "Traceback" in (logtxt or ""):
        return "code", "code:" + _m_state.norm_sig(err or last), "%s (exit %s)" % ((err or last)[:250], code)
    return "unknown", "exit%s:%s" % (code, _m_state.norm_sig(last)), "exit %s, last log line: %s%s" % (
        code, last[:200], "; Job condition %s" % freason if freason else "")


def do_submit(n, sid, reason, by):
    """Submit a stage's manifest. A failed stage = a retry (budgets enforced here, whoever asks). Returns (ok, message)."""
    from . import model as _m_model  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import red_alert as _m_red_alert  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import sizing as _m_sizing  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import tier0 as _m_tier0  # Local import breaks orchestration cycle; patches stay on the defining module.
    from ..task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    if _m_ladder.terminal_task(n):
        return False, "task is terminal"
    t = _m_state.task_load(n)
    s, ns, f = _m_state.tstage(t, sid), t["namespace"], t.get("failure")
    retry = s["state"] == "failed"
    if s["state"] not in ("pending", "failed"):
        return False, "stage %s is %s, nothing to submit" % (sid, s["state"])
    if retry:
        if not f or f["stage"] != sid:
            return False, "stage %s has no recorded failure" % sid
        used = len(t["attempts"][t.get("budget_from", 0):])
        cls_used = _m_ladder.class_retries(t, f)
        if used >= t["max_retries"]:
            return False, "RETRY CAP REACHED (%d of %d). Do not resubmit; report STOPPED with the diagnosis." % (used, t["max_retries"])
        if cls_used >= _m_state.failure_class(f["cls"])["budget"]:
            return False, "%s RETRY BUDGET USED (%d). Report STOPPED with the diagnosis." % (f["cls"], cls_used)
    checkpoint = _m_state.task_dir(n) / "agent-manifests.json"
    if checkpoint.exists():
        errors = _m_task_registry.validate_agent_manifests(n)
        if errors:
            return False, "manifest edit rejected: " + "; ".join(errors)
    probs = _m_task_registry.manifest_check(s["manifest"], ns, s["job"])
    if probs:
        return False, "manifest refused: " + "; ".join(probs)
    gx = _m_task_registry.gpu_expired(s)
    if gx:
        return False, gx + ". Report STOPPED; do not resubmit."
    if _m_red_alert.red_alert():                                                       # account RED ALERT: nothing new is created until NRP's dry-run accepts
        def hold(t):
            _m_model.transition(t, "block")
            if "pending" not in t:
                _m_state.tev(t, "submit of %s HELD: NRP RED ALERT (NRP refuses new pods on the account); sent when NRP's dry-run accepts" % s["job"])
            t.setdefault("pending", {"stage": sid, "reason": reason, "by": by, "since": _m_state.now(), "refusal": "NRP RED ALERT hold",
                                     "checked": _m_state.now(), "offenders": [], "hold": "red-alert"})
        _m_state.task_txn(n, hold)
        return True, ("HELD: NRP RED ALERT, NRP is refusing new pods on the account. The monitor sends this submit when its dry-run "
                      "accepts again. Do not retry yourself; resize or delete low pods instead.")
    st_ = _m_cluster.job_state(s["job"], ns)
    if st_ in ("running", "pending", "error"):
        return False, "Job %s is still %s" % (s["job"], st_)
    if st_ in ("ok", "FAILED"):
        save_task_logs(t, s, "before resubmit")
        d = _m_cluster.kubectl("-n", ns, "delete", "job", s["job"], "--wait=true", "--timeout=180s", timeout=240)
        if d.returncode and "NotFound" not in d.stderr:
            return False, "could not delete old Job %s: %s" % (s["job"], d.stderr.strip()[:150])
    # Shared exclusions live only in the submitted copy: expiry must restore capacity.
    doc = _m_task_registry.manifest_doc(s["manifest"])
    for node in _m_cluster.bad_nodes():
        _m_tier0.exclude_node(doc, node)
    with tempfile.TemporaryDirectory(prefix="nrp-submit-") as td:
        path = str(Path(td) / "job.json")
        _m_task_registry.manifest_write(path, doc)
        res = _m_cluster.apply_manifest(ns, path)
    if res == "blocked":
        def b(t):
            _m_model.transition(t, "block")
            if "pending" not in t:
                _m_state.tev(t, "submit of %s BLOCKED (account utilization or quota); the monitor checks the namespace once, wakes the coordinator, "
                       "and re-applies when the offenders change" % s["job"])
            t.setdefault("pending", {"stage": sid, "reason": reason, "by": by, "since": _m_state.now(), "refusal": _m_state.LAST_BLOCK.get("msg", "")[:300]})
            if _m_red_alert.red_alert():                                           # the RED ALERT wakes the offenders' owners; no per-task episode
                t["pending"].update(checked=_m_state.now(), offenders=[], hold="red-alert")
        _m_state.task_txn(n, b)
        _m_cluster.block_episode(n)
        return True, ("BLOCKED: NRP refused the submit (utilization block or quota). The monitor checked the namespace once and woke the "
                      "coordinator; it re-applies only when the offender set changes. Do not retry yourself.")
    if res != "ok":
        return False, "kubectl apply failed: %s" % res

    def ok(t):
        s2, f2 = _m_state.tstage(t, sid), t.get("failure")
        if retry and f2:
            t["attempts"].append({"stage": sid, "job": s2["job"], "cls": f2["cls"], "sig": f2["sig"], "detail": f2["detail"][:200],
                                  "fix": " ".join(reason.split())[:300], "by": by, "ts": _m_state.now(), "fingerprint": f2.get("fingerprint") or _m_decisions.fingerprint(t, f2),
                                  "resources_changed": f2.get("resource_values") is not None and f2["resource_values"] != _m_sizing.resource_values(doc),
                                  "resource_template": _m_sizing.resource_template(doc) if f2["cls"] == "resources" else None})
            s2["attempt"] = s2.get("attempt", 1) + 1
            t["failure"] = None
        s2.update(state="running", submitted=_m_state.now())
        s2.pop("pod_started", None)
        s2["dl"] = {"resubmits": (s2.get("dl") or {}).get("resubmits", 0)}      # a new Job gets fresh deadline tracking (Tier 0, deadline_watch)
        s2.pop("util_deleted", None)
        if (t.get("util_event") or {}).get("stage") == sid:
            t.pop("util_event", None)
        t.pop("pending", None)
        _m_model.transition(t, "resubmit" if retry else "submit",
                            "submitted %s (attempt %d) by %s: %s" % (s2["job"], s2["attempt"], by, reason[:200]))
    _m_state.task_txn(n, ok)
    _m_task_registry.agent_manifest_checkpoint(n)
    return True, "SUBMITTED %s attempt %d (retries used %d of %d)" % (s["job"], _m_state.tstage(_m_state.task_load(n), sid)["attempt"],
                                                                       len(_m_state.task_load(n)["attempts"]), t["max_retries"])


def s3_gate(s):
    """URIs in the stage's `after_s3` that do not (yet) exist. An unreadable answer counts as missing: the stage just waits."""
    from .. import s3 as _m_s3  # Local import breaks orchestration cycle; patches stay on the defining module.
    return [u for u in s.get("after_s3", []) if _m_s3.s3_exists(u, {}) is not True]


def note_waiting(n, sid, missing):
    """Record what a pending stage waits on (shown by `task show`); only writes when it changes."""
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if (_m_state.tstage(_m_state.task_load(n), sid).get("waiting_on") or []) == missing:
        return

    def f(t):
        _m_state.tstage(t, sid)["waiting_on"] = missing
        _m_state.tev(t, ("stage %s waits on %d S3 key(s): %s" % (sid, len(missing), ", ".join(missing)[:200])) if missing
            else "stage %s: every after_s3 key exists, submitting" % sid)
    _m_state.task_txn(n, f)


def advance_task(n, jobs, a):
    from . import model as _m_model  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import continuation as _m_continuation  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import red_alert as _m_red_alert  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import s3 as _m_s3  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import task_agents as _m_task_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import tier0 as _m_tier0  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import util as _m_util  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    from ..task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    if _m_ladder.terminal_task(n):
        return
    t = _m_state.task_load(n)
    if a.dry_run:                                                         # read-only: say what the pass would do
        for s in t["stages"]:
            info = jobs.get(s["job"])
            if s["state"] == "pending" and all(_m_state.tstage(t, x)["state"] == "done" for x in s["after"]):
                miss = s3_gate(s)
                if miss:
                    print("[dry-run] task %s: stage %s (%s) waits on %s" % (n, s["id"], s["job"], ", ".join(miss)))
                    continue
                print("[dry-run] task %s: would submit stage %s (%s)" % (n, s["id"], s["job"]))
            elif s["state"] == "running":
                print("[dry-run] task %s: stage %s Job %s is %s" % (n, s["id"], s["job"], info["state"] if info else "not in the cluster"))
        if t.get("failure"):
            print("[dry-run] task %s: failure [%s] %s -> would start a fix agent or escalate" % (n, t["failure"]["cls"], t["failure"]["detail"][:100]))
        if t["status"] == "blocked":
            print("[dry-run] task %s: submit is blocked; would %s" % (n, "re-check the namespace (no wake, no state change)"
                  if (t.get("pending") or {}).get("checked") is not None else "check the namespace once and wake the coordinator"))
        return
    if t["status"] == "blocked":
        p = t.get("pending") or {}
        if _m_red_alert.red_alert():                                                   # held account-wide; the alert, not the 6 h timer, tells the owner
            _m_state.PASS["held"] = _m_state.PASS.get("held", 0) + 1
            return
        if p and not _m_cluster.block_should_reapply(n):                                 # pods outside the bands explain it: wait, no retry loop
            ok = True
        else:
            ok, msg = do_submit(n, p.get("stage"), p.get("reason", "re-apply after block"), "monitor") if p else (False, "no pending submit")
        t = _m_state.task_load(n)
        if t["status"] == "blocked":
            if _m_state.now() - p.get("since", _m_state.now()) > _m_state.BLOCK_ESCALATE_S:
                offs = (t.get("pending") or {}).get("offenders") or []
                _m_ladder.escalate(n, "submits refused for %s (NRP utilization block or quota)%s" % (_m_state.ago(p["since"]), (
                    "; still outside the bands: " + ", ".join(o["pod"] for o in offs)) if offs else ""), a)
            return
        if not ok:
            _m_state.task_txn(n, lambda t: _m_model.transition(t, "resubmit"))
    _m_ladder.observe_task(n, jobs)
    _m_tier0.report_long_pending(n, jobs)
    if _m_state.task_load(n)["status"] in _m_state.TASK_HELD:
        return
    _m_util.process_util_event(n, a)
    t = _m_state.task_load(n)
    if t.get("failure"):
        if not _m_tier0.tier0_fix(n, a):                                           # fixed rules first (no model); the agents only when none applies
            _m_ladder.handle_failure(n, a)
        return
    for s in t["stages"]:
        if s["state"] == "pending" and all(_m_state.tstage(t, x)["state"] == "done" for x in s["after"]):
            if a.dry_run:
                print("[dry-run] task %s: would submit stage %s (%s)" % (n, s["id"], s["job"]))
                continue
            if s.get("after_s3") or s.get("waiting_on"):
                miss = s3_gate(s)
                note_waiting(n, s["id"], miss)
                if miss:
                    continue                                              # stays pending; checked again next pass
            if (not s.get("submitted") and s.get("attempt", 1) == 1
                    and not any(x.get("stage") == s["id"] for x in t["attempts"])
                    and s.get("done_s3") and all(_m_s3.s3_exists(u, {}) is True for u in s["done_s3"])):
                message = "stage %s done: success marker already present before submission (reused, not rerun)" % s["id"]
                def reuse(cur):
                    _m_state.tstage(cur, s["id"]).update(state="done", done_ts=_m_state.now())
                    _m_state.tev(cur, message)
                _m_state.task_txn(n, reuse)
                s.update(state="done")                                # dependents in this pass see completion too
                _m_notify.digest("done", message, n)
                continue
            ok, msg = do_submit(n, s["id"], "stage ready", "monitor")
            if not ok and msg.startswith("GPU APPROVAL"):
                _m_ladder.escalate(n, msg.split(". Report STOPPED")[0], a)
                return
            if not ok:
                _m_ladder.task_fail(n, s["id"], "infra", "apply:" + _m_state.norm_sig(msg), "submit failed: " + msg)
                _m_ladder.handle_failure(n, a)
                return
            if _m_state.task_load(n)["status"] == "blocked":
                return
    t = _m_state.task_load(n)
    if all(s["state"] == "done" for s in t["stages"]) and t["status"] in _m_state.TASK_LIVE:
        check = run_postcheck(t)
        _m_state.task_txn(n, lambda cur: cur.update(postcheck_result=check))
        if not check["ok"]:
            _m_ladder.task_fail(n, t["stages"][-1]["id"], "outputs", "postcheck", "postcheck failed: " + check["output"][-1000:])
            _m_ladder.handle_failure(n, a)
            return
        def finish(t):
            _m_model.transition(t, "finish", "all %d stages done" % len(t["stages"]), finished=_m_state.now())
        _m_state.task_txn(n, finish)
        _m_notify.digest("task-done", "%s: all %d stage(s) done in %s; %d retr%s" % (t["label"], len(t["stages"]), _m_state.ago(t["created"]),
               len(t["attempts"]), "y" if len(t["attempts"]) == 1 else "ies"), n)
        if not t.get("on_done") and not t.get("followup") and not t.get("digest_only"):
            _m_notify.digest("no-continuation", "%s finished and nothing was set to act on it (no on_done, followup or digest_only); its result "
                   "waits for a person: `nrp-monitor task show %s`" % (t["label"], n), n)
        if not t.get("handoff") or t["handoff"].get("thin"):
            _m_notify.digest("no-handoff", "%s finished with %s: a later fix or continue agent had only the task fields. Write one with templates/handoff.md "
                   "next time (`nrp-monitor task show %s`)" % (t["label"], "no handoff" if not t.get("handoff") else "a thin handoff", n), n)
        if t.get("code") and _m_task_registry.git("rev-list", "--count", "%s..HEAD" % t["code"]["base"], cwd=t["code"]["clone"]).stdout.strip() not in ("", "0"):
            _m_notify.digest("merge", "fixes on branch %s: git -C %s fetch %s %s" % (t["code"]["branch"], t["code"]["repo"], t["code"]["clone"],
                   t["code"]["branch"]), n)
        if t.get("followup") and not t.get("on_done") and not a.dry_run:
            text = ("You are a fresh read-only agent. NRP task %s finished: all stages succeeded.\nGoal: %s\nOrigin chat (who gets the result): %s\nNotes: %s\nStages:\n%s\n\nHandoff (from the agent that registered the task; read-only context):\n%s\n\n"
                    "WHAT TO REPORT:\n%s\n\nYour only shell tool is `nrp-task` (show, logs JOB, s3 ls URI, s3 cat URI; one command per call). "
                    "Saved logs are under %s/logs. Finish with `nrp-task report DONE \"one line\"` and reply with that line."
                    % (n, t["goal"], _m_wake.origin_plain(t.get("origin")), t["notes"], "\n".join("  - %s %s" % (s["job"], ", ".join(s["done_s3"])) for s in t["stages"]),
                       _m_wake.handoff_prompt(t), t["followup"], _m_state.task_dir(n)))
            text += ("\nPostcheck: " + json.dumps(_m_state.task_load(n).get("postcheck_result"))
                     + "\nStage outputs: " + json.dumps({s["id"]: s.get("outputs", {}) for s in _m_state.task_load(n)["stages"]})
                     + "\nRead saved logs/notes in the task directory. `nrp-task postcheck` reruns only the declared checker.")
            text += _m_continuation.person_resolution_context(_m_state.task_load(n))
            line, _ = _m_task_agents.run_task_agent(n, text, a, kind="followup")
            if _m_agents.is_unavailable(line):
                line = ("the completion report was not written (%s); read the result with `nrp-monitor task show %s`" % (line, n))
            _m_notify.digest("result", line, n)


def recover_held_completion(n, jobs):
    from . import model as _m_model  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import s3 as _m_s3  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import sizing as _m_sizing  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = _m_state.task_load(n)
    sid = (t.get("failure") or {}).get("stage")
    stages = [s for s in t["stages"] if s["id"] == sid] if sid else [s for s in t["stages"] if s["state"] in ("running", "failed")]
    completed = [s for s in stages if (jobs.get(s["job"]) or {}).get("state") == "ok"]
    if not completed:
        return False
    missing = [u for s in completed for u in s["done_s3"] if _m_s3.s3_exists(u, {}) is not True]
    if missing:
        reason = t.get("reason", "").split(" Completion check:", 1)[0] + " Completion check: Job complete but success markers missing or unreadable: " + ", ".join(missing)
        _m_state.task_txn(n, lambda t: t.update(reason=reason))
        return False
    def recover(t):
        for s in completed:
            _m_state.tstage(t, s["id"]).update(state="done", done_ts=_m_state.now())
            _m_sizing.propagate_resources(t, _m_state.tstage(t, s["id"]))
        for key in ("reason", "coordinator_since", "util_event"):
            t.pop(key, None)
        _m_model.transition(t, "release", "held stage completed with all success markers; hold cleared", failure=None)
    _m_state.task_txn(n, recover)
    return True


def process_tasks(a, st):
    from .. import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not a.dry_run:
        for n in _m_state.task_names():
            _m_ladder.terminal_task(n)
    names = [x for x in _m_state.task_names() if (_m_state.task_load(x) or {}).get("status") in _m_state.TASK_LIVE + _m_state.TASK_HELD]
    _m_state.PASS["tasks"] = len(names)
    with _m_cluster.pass_snapshot():
        for n in names:
            process_task(n, a)
    try:
        _m_ladder.check_coordinator_waits(a)
    except Exception as e:
        _m_state.log("coordinator wait check error: %s: %s" % (type(e).__name__, str(e)[:150]))


def process_task(n, a):
    from .. import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import tier0 as _m_tier0  # Local import breaks orchestration cycle; patches stay on the defining module.
    from ..task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = _m_state.task_load(n)
    try:
        # Deterministic manifest corruption cannot improve by retrying. Do not edit legacy files.
        if t["status"] not in _m_state.TASK_HELD and not a.dry_run:
            invalid = None
            for stage in t["stages"]:
                if stage.get("manifest"):
                    try:
                        _m_task_registry.manifest_doc(stage["manifest"])
                    except Exception as error:
                        invalid = _m_task_registry.manifest_error(stage["manifest"], error)
                        break
            if invalid:
                _m_state.log("task %s invalid manifest: %s" % (n, invalid))
                _m_state.task_txn(n, lambda cur: cur.update(task_exception=dict(
                    signature="invalid-manifest", count=1, detail=invalid, escalated=True)))
                _m_ladder.to_coordinator(n, "invalid task manifest: " + invalid, a, deputy=False)
                return
        if (t.get("task_exception") or {}).get("escalated") and t["status"] in _m_state.TASK_HELD:
            return
        jobs = _m_cluster.jobs_in(t["namespace"])
        if t["status"] in _m_state.TASK_HELD:
            if t.get("queue_hold") and not a.dry_run:
                _m_tier0.report_long_pending(n, jobs)
                t = _m_state.task_load(n)
            if t["status"] in _m_state.TASK_HELD and (a.dry_run or not recover_held_completion(n, jobs)):
                return
        advance_task(n, jobs, a)
        if t.get("task_exception") and not a.dry_run:
            _m_state.task_txn(n, lambda cur: cur.pop("task_exception", None))
    except Exception as e:
        detail = "%s: %s" % (type(e).__name__, str(e))
        _m_state.log("task %s error: %s" % (n, detail[:1000]))
        if not a.dry_run:
            signature = hashlib.sha256(detail.encode()).hexdigest()[:16]
            def record(cur):
                prior = cur.get("task_exception") or {}
                count = prior.get("count", 0) + 1 if prior.get("signature") == signature else 1
                cur["task_exception"] = dict(signature=signature, count=count, detail=detail,
                                             escalated=count >= _m_state.TASK_EXCEPTION_LIMIT)
            _m_state.task_txn(n, record)
            if _m_state.task_load(n)["task_exception"]["escalated"]:
                _m_ladder.to_coordinator(n, "task pass failed %d consecutive times: %s" % (_m_state.TASK_EXCEPTION_LIMIT, detail), a, deputy=False)


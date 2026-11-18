"""NRP monitor cluster (mechanical extraction; R3a)."""
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

# ---- cluster reads -------------------------------------------------------------------------------------------
def kubectl(*args, timeout=120):
    return subprocess.run(["kubectl", *args], capture_output=True, text=True, timeout=timeout)


def my_pods():
    """{name: owner_job_or_None} for the owner's pods that are Running, Pending or Failed (by annotation)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not _m_state.USER_ANN:
        raise RuntimeError("nrp_user_annotation is not set (config.json or NRP_MONITOR_USER_ANNOTATION): cannot tell which pods are yours")
    r = kubectl("-n", _m_state.NS, "get", "pods", "-o", "json")
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:150])
    out = {}
    for p in json.loads(r.stdout)["items"]:
        m = p["metadata"]
        if m.get("annotations", {}).get("nrp.ai/username") != _m_state.USER_ANN or m.get("deletionTimestamp"):
            continue
        if p["status"].get("phase") not in ("Running", "Pending", "Failed"):
            continue
        job = next((o["name"] for o in m.get("ownerReferences", []) if o.get("kind") == "Job"), None)
        out[m["name"]] = job
    return out


def job_state(name, ns):
    """'ok' | 'FAILED' | 'running' | 'pending' | 'missing' | 'error'"""
    r = kubectl("-n", ns, "get", "job", name, "-o", "jsonpath={.status.succeeded}/{.status.failed}/{.status.active}/{.spec.completions}"
                "/{.status.conditions[?(@.type==\"Complete\")].status}")
    if r.returncode:
        return "missing" if "NotFound" in r.stderr else "error"
    ok, fail, act, comp, done = (r.stdout.split("/") + ["", "", "", "", ""])[:5]
    if job_complete(int(ok) if ok.isdigit() else 0, int(comp) if comp.isdigit() else None, bool(act), done == "True"):
        return "ok"
    if fail.isdigit() and int(fail) >= 1 and not act:
        return "FAILED"
    return "running" if act else "pending"


def job_complete(succeeded, completions, active, complete_cond):
    """A Job is finished successfully only when ALL its completions succeeded. `status.succeeded >= 1` is NOT that: an Indexed Job
    (pv3 --parallel N, completions=N) has succeeded >= 1 as soon as its first shard exits, while the other shards still run; treating
    that as success made the monitor check a root marker too early and delete the Job's pods (finch-feature-followup, 2026-11-06).
    Complete=True is authoritative; else succeeded >= spec.completions; completions unset (work-queue Job) = one success and no pod active."""
    if complete_cond:
        return True
    if completions is not None:
        return succeeded >= completions
    return succeeded >= 1 and not active


def classify_job(j):
    s = j.get("status", {})
    conds = {c.get("type"): c.get("status") for c in s.get("conditions", [])}
    comp = (j.get("spec") or {}).get("completions")
    if job_complete(s.get("succeeded") or 0, comp if isinstance(comp, int) else None, bool(s.get("active")), conds.get("Complete") == "True"):
        return "ok"
    if conds.get("Failed") == "True" or ((s.get("failed") or 0) >= 1 and not s.get("active")):
        return "FAILED"
    return "running" if s.get("active") else "pending"


def fetch_jobs(ns):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    r = kubectl("-n", ns, "get", "jobs", "-o", "json")
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:150] or "kubectl get jobs failed")
    out = {}
    for j in json.loads(r.stdout).get("items", []):
        m = j["metadata"]
        out[m["name"]] = {"state": classify_job(j), "start": _m_state.parse_ts(j.get("status", {}).get("startTime")),
                          "deadline": (j.get("spec") or {}).get("activeDeadlineSeconds"),
                          "ours": m.get("annotations", {}).get("nrp.ai/username") == _m_state.USER_ANN}
    return out


def apply_manifest(ns, path):
    """'ok' | 'blocked' | error text. Server dry-run first."""
    from . import red_alert as _m_red_alert  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    for extra in (["--dry-run=server"], []):
        r = kubectl("-n", ns, "apply", *extra, "-f", path, timeout=180)
        if r.returncode:
            msg = (r.stderr.strip() or r.stdout.strip())[:400]
            if _m_state.BLOCK_RE.search(msg):
                _m_state.LAST_BLOCK["msg"] = msg
                _m_red_alert.red_alert_enter(ns, msg, "submit refused")
                return "blocked"
            return msg
    return "ok"


def pod_gpu_request(p):
    total = 0
    for c in p.get("spec", {}).get("containers", []):
        try:
            total += int((c.get("resources", {}).get("requests") or {}).get("nvidia.com/gpu", 0))
        except (TypeError, ValueError):
            pass
    return total


def namespace_offenders(ns):
    """Every Running pod in `ns`, whoever launched it (no annotation filter), through nrp-util-check: the pods outside NRP's bands
    (rule nrp or gpu; a lab-floor-only flag is not counted by NRP's webhook) or stuck. Returns a list of dicts: pod, owner (Job or other
    ownerReference), username (nrp.ai/username annotation, may be ""), service_account, ours (annotation == our owner annotation),
    usage ({cpu|mem|gpu: use/request/pct}) and line (nrp-util-check's text). Raises RuntimeError when kubectl or the metrics fail."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import util as _m_util  # Local import breaks orchestration cycle; patches stay on the defining module.
    r = kubectl("-n", ns, "get", "pods", "-o", "json")
    if r.returncode:
        raise RuntimeError("kubectl get pods: " + (r.stderr.strip() or r.stdout.strip())[:150])
    running = {}
    for p in json.loads(r.stdout or "{}").get("items", []):
        m = p.get("metadata", {})
        if p.get("status", {}).get("phase") == "Running" and not m.get("deletionTimestamp"):
            running[m["name"]] = p
    if not running:
        return []
    u = subprocess.run(["nrp-util-check", "-n", ns, "--min-age", "300"] + sorted(running), capture_output=True, text=True, timeout=300)
    if u.returncode not in (0, 4, 5):
        raise RuntimeError("nrp-util-check exit %s: %s" % (u.returncode, (u.stdout.strip() or u.stderr.strip())[:150]))
    out = []
    for line in u.stdout.splitlines():
        m = _m_state.FLAG.match(line)
        if not m or m.group(1) not in ("LOW", "STUCK") or m.group(2) not in running or _m_util.flag_rule(line) == "lab":
            continue
        p = running[m.group(2)]
        meta, refs = p["metadata"], p["metadata"].get("ownerReferences") or []
        ref = next((o for o in refs if o.get("kind") == "Job"), refs[0] if refs else None)
        user = (meta.get("annotations") or {}).get("nrp.ai/username") or ""
        usage = {k: {"use": float(use), "request": float(req), "pct": int(pct)} for k, use, req, pct, mx in _m_state.FLAG_RES.findall(line)}
        for pct, gi in _m_state.GPU_USE_RE.findall(line):
            usage["gpu"] = {"pct": int(pct), "request": pod_gpu_request(p)}
        out.append({"pod": m.group(2), "owner": "%s/%s" % (ref.get("kind"), ref.get("name")) if ref else "", "username": user,
                    "service_account": p.get("spec", {}).get("serviceAccountName") or "", "ours": bool(_m_state.USER_ANN) and user == _m_state.USER_ANN,
                    "usage": usage, "line": line.strip()[:300]})
    return sorted(out, key=lambda o: o["pod"])


def offender_text(o):
    who = ", ".join(x for x in (o["owner"], ("user " + o["username"]) if o["username"] else "", ("service account " + o["service_account"])
                                if o["service_account"] and not o["username"] else "") if x) or "owner unknown"
    use = "; ".join("%s %s" % (k, ("%g/%g (%d%%)" % (v["use"], v["request"], v["pct"])) if "use" in v else
                               ("%d%% of %d GPU" % (v["pct"], v["request"]))) for k, v in o["usage"].items())
    return "%s (%s; %s)" % (o["pod"], who, use or o["line"][:80])


def block_wake_text(n, stage, job, refusal, offenders, err):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    head = "NRP refused the submit of task %s (stage %s, Job %s): %s" % (n, stage, job, " ".join(refusal.split())[:200])
    if err:
        return ("%s. The namespace-wide utilization check FAILED (%s), so the cause is unknown. Look at all Running pods with "
                "`kubectl get pods` and `nrp-util-check`; do not retry in a loop. The monitor keeps the task blocked and re-applies it each pass; "
                "it tells the owner after 6 h." % (head, err[:120]))
    if not offenders:
        return ("%s. The namespace-wide utilization check found no Running pod outside the bands, so this may be a quota block or metrics lag. "
                "The monitor keeps the task blocked and re-applies each pass; it tells the owner after 6 h." % head)
    ours, others = [o for o in offenders if o["ours"]], [o for o in offenders if not o["ours"]]
    parts = []
    if ours:
        parts.append("OURS (annotation matches): " + "; ".join(offender_text(o) for o in ours))
    if others:
        parts.append("OTHERS' (not launched by us): " + "; ".join(offender_text(o) for o in others))
    return ("%s. Namespace-wide check: %d Running pod(s) outside the bands. %s. Fix or delete our own pods; ask the owner before touching "
            "anyone else's. The monitor re-checks every %d min and re-applies the submit only when the offender set changes; never retry in a loop."
            % (head, len(offenders), " | ".join(parts), _m_state.BLOCK_RECHECK_S // 60))


def block_episode(n):
    """First block of a pending submit: run the namespace-wide check once, save it on t["pending"], write a digest line and wake the
    coordinator chat once (the task stays `blocked`, so the monitor goes on re-applying when the offenders clear). Later calls in the same
    episode do nothing. A failed check is logged and still produces the one wake, carrying the raw refusal."""
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = _m_state.task_load(n)
    p = (t or {}).get("pending") or {}
    if not t or p.get("checked") is not None:
        return
    ns, offenders, err = t["namespace"], [], None
    try:
        offenders = namespace_offenders(ns)
    except Exception as e:
        err = "%s: %s" % (type(e).__name__, str(e)[:150])
        _m_state.log("task %s: namespace utilization check failed: %s" % (n, err))
    refusal = p.get("refusal") or _m_state.LAST_BLOCK.get("msg") or "utilization block or quota"
    text = block_wake_text(n, p.get("stage"), _m_state.tstage(t, p["stage"])["job"], refusal, offenders, err)
    out = {}

    def f(t):
        pp = t.get("pending")
        if t["status"] != "blocked" or not pp or pp.get("checked") is not None:
            return False
        pp.update(checked=_m_state.now(), rechecked=_m_state.now(), offenders=offenders, check_error=err, refusal=refusal[:300], woke=_m_state.now())
        out["event"] = _m_wake.queue_task_webhook(t, "escalation", summary=text[:2400] + " Look: `nrp-monitor task show %s`." % n)
        _m_state.tev(t, "submit BLOCKED: %s" % (("%d offender(s): %s" % (len(offenders), ", ".join(o["pod"] for o in offenders))) if not err else "namespace check failed"))
    if not _m_state.task_txn(n, f):
        return
    short = lambda os_: ", ".join("%s [%s]" % (o["pod"], o["owner"] or o["username"] or o["service_account"] or "?") for o in os_) or "none"
    brief = ("namespace check failed (%s)" % err if err else "%d pod(s) outside the bands. ours: %s. others: %s" % (
        len(offenders), short([o for o in offenders if o["ours"]]), short([o for o in offenders if not o["ours"]])))
    _m_notify.digest("block", "%s: submit refused by NRP; %s" % (t["label"], brief), n)
    _m_state.PASS["coordinator"] = _m_state.PASS.get("coordinator", 0) + 1
    if not out["event"]:                                                     # no coordinator chat to wake: the digest line above is the report; the 6 h fallback tells the owner
        _m_state.log("task %s: submit blocked and the task has no wake target; digest only" % n)


def block_should_reapply(n):
    """True when the pending submit should be applied again this pass. Pods outside the bands explain the block: no re-apply until a
    re-check (at most every BLOCK_RECHECK_S) finds the set changed (or empty). No offenders or a failed check: the block is
    unexplained, so it goes on being applied each pass, as before, with the 6 h escalation as the fallback."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    p = (_m_state.task_load(n) or {}).get("pending") or {}
    if p.get("checked") is None:
        block_episode(n)
        p = (_m_state.task_load(n) or {}).get("pending") or {}
    if not p.get("offenders"):
        return True
    if _m_state.now() - p.get("rechecked", p.get("checked", 0)) < _m_state.BLOCK_RECHECK_S:
        return False
    try:
        new = namespace_offenders(_m_state.task_load(n)["namespace"])
    except Exception as e:
        _m_state.log("task %s: namespace utilization re-check failed: %s" % (n, str(e)[:150]))
        _m_state.task_txn(n, lambda t: (t.get("pending") or {}).update(rechecked=_m_state.now()) if t.get("pending") else False)
        return False
    changed = {o["pod"] for o in new} != {o["pod"] for o in p["offenders"]}

    def f(t):
        if not t.get("pending"):
            return False
        t["pending"].update(offenders=new, rechecked=_m_state.now())
        if changed:
            _m_state.tev(t, "block re-check: offender set changed (%s); re-applying the submit" % (", ".join(o["pod"] for o in new) or "none left"))
    _m_state.task_txn(n, f)
    return changed


def thanos_query(expr):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    try:
        with urllib.request.urlopen(_m_state.THANOS_URL + "?" + urllib.parse.urlencode({"query": expr}), timeout=60) as r:
            d = json.load(r)
        return d["data"]["result"] if d.get("status") == "success" else []
    except Exception as e:
        _m_state.log("tier0: thanos query failed: %s" % type(e).__name__)
        return []


def bad_nodes():
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return {n: r for n, r in _m_notify.read_json(_m_state.STATE / "bad-nodes.json", {}).items() if r.get("expires", 0) > _m_state.now()}


def record_bad_node(node, why, fault=None):
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    with _m_state.state_lock():
        nodes = _m_notify.read_json(_m_state.STATE / "bad-nodes.json", {})
        if fault and (nodes.get(node) or {}).get("fault") == fault:
            return
        nodes[node] = {"last_fault": _m_state.now(), "expires": _m_state.now() + 86400, "reason": why[:200], "fault": fault}
        _m_notify.write_json(_m_state.STATE / "bad-nodes.json", nodes)


def bad_node_lines():
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return ["excluded node %s until %s (last fault %s)" % (n, _m_state.iso_at(r["expires"]), _m_state.iso_at(r["last_fault"]))
            for n, r in sorted(bad_nodes().items())]


def job_pods(ns, job):
    r = kubectl("-n", ns, "get", "pods", "-l", "job-name=" + job, "-o", "json")
    try:
        return json.loads(r.stdout or "{}").get("items", []) if r.returncode == 0 else []
    except ValueError:
        return []


def pending_reason(t, s):
    """One line saying why the scheduler has not started a Pending Job: its PodScheduled message, plus the node restrictions in our own
    manifest (for example a GPU allow-list) when it reports nodes excluded by affinity/selector."""
    from .task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    pods = job_pods(t["namespace"], s["job"])
    msgs = []
    for p in pods:
        for c in (p.get("status") or {}).get("conditions") or []:
            if c.get("type") == "PodScheduled" and c.get("status") == "False" and c.get("message"):
                msgs.append(c["message"])
    if not pods:
        return "the Job has no pod yet (admission, quota or the Job controller)"
    if not msgs:
        return "a pod exists but the scheduler gave no reason yet"
    msg = " ".join(msgs[0].split())[:300]
    own = []
    try:
        pod = _m_task_registry.manifest_doc(s["manifest"])["spec"]["template"]["spec"]
        for term in (((pod.get("affinity") or {}).get("nodeAffinity") or {}).get("requiredDuringSchedulingIgnoredDuringExecution") or {}).get("nodeSelectorTerms") or []:
            own += ["%s %s %s" % (e.get("key"), e.get("operator"), ",".join(map(str, e.get("values") or []))[:80]) for e in term.get("matchExpressions") or []]
        own += ["%s=%s" % kv for kv in (pod.get("nodeSelector") or {}).items()]
    except Exception:
        pass
    if own and re.search(r"affinity|selector", msg, re.I):
        msg += " | our manifest restricts nodes: %s (an own allow-list may be what excludes them)" % "; ".join(own)[:200]
    return msg


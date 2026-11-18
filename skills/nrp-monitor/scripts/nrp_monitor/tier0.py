"""NRP monitor tier0 (mechanical extraction; R3a)."""
import json
import re
from pathlib import Path

from . import cluster as _m_cluster, config as _m_config, decisions as _m_decisions, notify as _m_notify, sizing as _m_sizing, state as _m_state
from .task import model as _m_task_model, registry as _m_task_registry




def vanished_nodes(t, s):
    window = max(300, int(_m_state.now() - (s.get("submitted") or _m_state.now() - 86400)) + 120)
    expr = 'max_over_time(kube_pod_info{namespace=%s,pod=~%s}[%ds])' % (
        json.dumps(t["namespace"]), json.dumps(re.escape(s["job"]) + "-.*"), window)
    return sorted({r["metric"]["node"] for r in _m_cluster.thanos_query(expr) if r.get("metric", {}).get("node")})


def tier0_oom(t, s, f):
    """(manifest doc, reason, record) raising the OOMKilled container's memory to observed peak x1.3, or None to leave it to the agents."""
    cname = None
    for p in _m_cluster.job_pods(t["namespace"], s["job"]):
        for cs in (p.get("status") or {}).get("containerStatuses") or []:
            term = (cs.get("state") or {}).get("terminated") or (cs.get("lastState") or {}).get("terminated") or {}
            if term.get("reason") == "OOMKilled":
                cname = cs.get("name")
    try:
        doc = _m_task_registry.manifest_doc(s["manifest"])
        cs_ = doc["spec"]["template"]["spec"]["containers"]
    except Exception:
        return None
    c = next((x for x in cs_ if x.get("name") == cname), cs_[0] if len(cs_) == 1 or not cname else None)
    if c is None:
        return None
    res = c.setdefault("resources", {})
    lim = _m_sizing.mem_bytes((res.get("limits") or {}).get("memory") or (res.get("requests") or {}).get("memory") or "")
    true_peak = _m_sizing.container_memory_peak(t, s, c["name"], single=len(cs_) == 1)
    peak = _m_sizing.thanos_peak_mem(t["namespace"], s["job"], c["name"], s.get("submitted") or _m_state.now() - 3600)
    if peak is None:
        peak = true_peak
    if not lim or peak is None:
        return None
    base = max(peak, lim)                                     # an OOM-killed container reached its limit even if the 30 s samples missed it
    new = 2 * lim if true_peak is None and peak < .5 * lim else base * _m_state.OOM_FACTOR
    cap = float(_m_state.OWNER.get("tier0_mem_cap_gi") or _m_state.OOM_MAX_GI_DEFAULT) * 2 ** 30
    if new > cap:
        return None
    tol = float(_m_config.util_policy().get("limit_to_request_tolerance") or 0.2)
    new_text = _m_sizing.mem_text(new)
    new_b = _m_sizing.mem_bytes(new_text)
    old_req = _m_sizing.mem_bytes((res.get("requests") or {}).get("memory") or "") or lim
    req_b = new_b if old_req >= lim else min(new_b, max(old_req, new_b / (1 + tol)))        # limit stays within the shared tolerance of the request
    res.setdefault("limits", {})["memory"] = new_text
    res.setdefault("requests", {})["memory"] = _m_sizing.mem_text(req_b)
    return doc, "OOM at %s (observed peak %.1fGi) -> memory %s (base x%g, Tier 0 rule)" % (
        _m_sizing.mem_text(lim), peak / 2 ** 30, new_text, new / base), {"rule": "oom", "memory": new_text}


def node_fault_of(t, s, f):
    """(node, evidence) of a pod of this stage's Job that hit a known node fault, else None. Pod status and conditions plus the saved log tail."""
    tail = ""
    try:
        tail = Path(f.get("logs") or "").read_text()[-8000:] if f.get("logs") else ""
    except OSError:
        pass
    pods = _m_cluster.job_pods(t["namespace"], s["job"])
    for p in pods:
        node = (p.get("spec") or {}).get("nodeName")
        ps = p.get("status") or {}
        bits = [ps.get("reason") or "", ps.get("message") or ""]
        for c in ps.get("conditions") or []:
            bits.append(c.get("reason") or "")
            bits.append(c.get("message") or "")
        for cs in ps.get("containerStatuses") or []:
            for k in ("state", "lastState"):
                for v in (cs.get(k) or {}).values():
                    bits += [(v or {}).get("reason") or "", (v or {}).get("message") or ""]
        text = " ".join(bits) + "\n" + (tail if len(pods) == 1 else "")     # the log tail names one pod only when there is one
        m = _m_state.NODE_FAULT_RE.search(text)
        if m and node:
            return node, m.group(0)
    if not pods:
        # Historical placement alone is not a fault. Restrict inference to a vanished
        # failed pod with no useful diagnostics, or explicit node-fault evidence.
        evidence = _m_state.NODE_FAULT_RE.search(tail + " " + str(f.get("detail", "")))
        if evidence or (f.get("cls") in ("infra", "unknown") and (not tail.strip() or re.search(
                r"kubectl failed|NotFound|No resources found|no pods found|timed out waiting", tail, re.I))):
            nodes = vanished_nodes(t, s)
            if len(nodes) == 1:
                return nodes[0], evidence.group(0) if evidence else "failed pod vanished without diagnostics"
    return None


def exclude_node(doc, node):
    """Add `kubernetes.io/hostname NotIn [node]` to every required node-affinity term of the Job's pod spec (idempotent)."""
    pod = doc["spec"]["template"]["spec"]
    na = pod.setdefault("affinity", {}).setdefault("nodeAffinity", {})
    req = na.setdefault("requiredDuringSchedulingIgnoredDuringExecution", {})
    terms = req.setdefault("nodeSelectorTerms", [])
    if not terms:
        terms.append({})
    for term in terms:
        exprs = term.setdefault("matchExpressions", [])
        e = next((x for x in exprs if x.get("key") == "kubernetes.io/hostname" and x.get("operator") == "NotIn"), None)
        if e is None:
            exprs.append({"key": "kubernetes.io/hostname", "operator": "NotIn", "values": [node]})
        elif node not in e.get("values", []):
            e["values"] = list(e.get("values", [])) + [node]


def tier0_node(t, s, f):
    hit = node_fault_of(t, s, f)
    if not hit:
        return None
    node, why = hit
    _m_cluster.record_bad_node(node, why, "%s/%s/%s" % (t["name"], s["id"], f.get("ts", s.get("submitted"))))
    excluded = [x for x in t.get("tier0") or [] if x.get("stage") == s["id"] and x.get("rule") == "node"]
    if len(excluded) >= _m_state.NODE_EXCLUDE_MAX or any(x.get("node") == node for x in excluded):
        return None
    try:
        doc = _m_task_registry.manifest_doc(s["manifest"])
        # The shared expiring list is applied by do_submit, not persisted here.
    except Exception:
        return None
    return doc, "known node fault on %s (%s) -> node excluded, resubmitted (Tier 0 rule)" % (node, why[:60]), {"rule": "node", "node": node}


def tier0_lost(t, s, f):
    """(unchanged manifest doc, reason, record) for a lost pod; do_submit applies the shared bad-node list and the stage's budget."""
    try:
        doc = _m_task_registry.manifest_doc(s["manifest"])
    except Exception:
        return None
    return doc, "pod lost without an exit or traceback (environment, not code) -> resubmitted unchanged (Tier 0 rule)", {"rule": "lost"}


def _oom_matches(t, s, f):            # an OOM, and this stage was not resized by the rule already (a second OOM is not a sizing problem)
    return str(f.get("sig", "")).startswith("oom@") and not any(
        x.get("stage") == s["id"] and x.get("rule") == "oom" for x in t.get("tier0") or [])


# Tier 0 rules, tried in order for the classes that list them (state.CLASSES). `apply` returns (manifest doc, reason, record) or None.
RULES = (
    {"name": "node", "matches": lambda t, s, f: True, "apply": tier0_node},
    {"name": "oom", "matches": _oom_matches, "apply": tier0_oom},
    {"name": "lost", "matches": lambda t, s, f: f.get("sig") == _m_state.LOST_SIG, "apply": tier0_lost},
)


def tier0_fix(n, a):
    """True when a Tier 0 rule edited the manifest and resubmitted the failed stage. Never raises, never starts a model; False hands the
    failure to handle_failure unchanged (watch-only tasks, repeats, anything over a cap, no rule matched)."""
    from . import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import pass_ as _m_task_pass_  # Local import breaks orchestration cycle; patches stay on the defining module.
    try:
        if _m_ladder.terminal_task(n):
            return False
        t = _m_state.task_load(n)
        f = (t or {}).get("failure")
        rules = [r for r in RULES if r["name"] in _m_state.failure_class((f or {}).get("cls"))["rules"]]
        if not f or t["mode"] != "auto" or a.dry_run or not rules:
            return False
        if _m_decisions.apply_decision(n, a):
            return True
        s = _m_state.tstage(t, f["stage"])
        if not s.get("manifest"):
            return False
        node_rule = tier0_node(t, s, f)  # record a fresh fault even if the retry budget is used
        if f["sig"] != _m_state.LOST_SIG and f["sig"] in [x["sig"] for x in t["attempts"] if x["stage"] == f["stage"]]:
            return False                                       # a lost pod may repeat on the same stage; its per-stage infra budget caps it
        for rule in rules:
            r = rule["matches"](t, s, f) and (node_rule if rule["name"] == "node" else rule["apply"](t, s, f))
            if not r:
                continue
            doc, reason, rec = r
            before = Path(s["manifest"]).read_text()
            _m_task_registry.manifest_write(s["manifest"], doc)
            ok, msg = _m_task_pass_.do_submit(n, s["id"], reason, "tier0")
            if not ok:
                Path(s["manifest"]).write_text(before)         # nothing was submitted: leave the manifest as it was
                _m_state.log("task %s: tier0 %s not applied: %s" % (n, rec["rule"], msg[:200]))
                return False
            _m_state.task_txn(n, lambda t: t.setdefault("tier0", []).append(dict(rec, stage=s["id"], ts=_m_state.now())))
            _m_notify.digest("retry", "%s [%s] -> %s" % (s["job"], f["cls"], reason[:250]), n)
            _m_decisions.cost_event(n, "rule", "0", "resolved", stage=f["stage"], fingerprint=f.get("fingerprint") or _m_decisions.fingerprint(t, f))
            _m_state.PASS["tier0"] = _m_state.PASS.get("tier0", 0) + 1
            return True
    except Exception as e:
        _m_state.log("task %s: tier0 error: %s: %s" % (n, type(e).__name__, str(e)[:200]))
    return False


def queue_ceiling_seconds(value):
    m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)(s|m|h|d)", str(value))
    if not m or float(m[1]) <= 0:
        raise ValueError("invalid queue duration")
    return float(m[1]) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[m[2]]


def report_long_pending(n, jobs):
    """Record bounded Pending reports and ask the coordinator before a long queue wait continues. Never raises."""
    try:
        _report_long_pending(n, jobs)
    except Exception as e:
        _m_state.log("task %s: pending report error: %s: %s" % (n, type(e).__name__, str(e)[:200]))


def _report_long_pending(n, jobs):
    from . import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = _m_state.task_load(n)
    for s in t["stages"]:
        if s["state"] != "running":
            continue
        info = jobs.get(s.get("job"))
        if not info or info["state"] not in ("running", "pending"):
            continue
        if s.get("pod_started") and not s.get("queue_wait") and t.get("queue_hold") != s["id"]:
            continue                                   # already running, nothing queued: no extra kubectl call
        try:
            pods = _m_cluster.job_pods(t["namespace"], s["job"])
        except Exception as e:
            _m_state.log("task %s: pending observation unavailable: %s" % (n, type(e).__name__))
            continue
        scheduled = s.get("pod_started") or any((p.get("spec") or {}).get("nodeName") or any(
            c.get("type") == "PodScheduled" and c.get("status") == "True"
            for c in (p.get("status") or {}).get("conditions", [])) for p in pods)
        q = s.get("queue_wait") or {}
        if scheduled:
            def clear(t):
                _m_state.tstage(t, s["id"]).pop("queue_wait", None)
                _m_state.tstage(t, s["id"]).pop("pending_report", None)
                if t.get("queue_hold") == s["id"]:
                    t.pop("queue_hold", None)
                    _m_task_model.transition(t, "release", "stage %s scheduled; queue hold cleared automatically" % s["id"], reason="")
            _m_state.task_txn(n, clear)
            continue
        unschedulable = any(c.get("type") == "PodScheduled" and c.get("status") == "False" and
                            c.get("reason") == "Unschedulable" for p in pods
                            for c in (p.get("status") or {}).get("conditions", []))
        if q.get("attempt") != s.get("attempt", 1):
            q = {}
        if unschedulable and not q:
            q = {"since": _m_state.now(), "attempt": s.get("attempt", 1), "multiplier": 1}
            _m_state.task_txn(n, lambda t: _m_state.tstage(t, s["id"]).update(queue_wait=q))
        reason = _m_cluster.pending_reason(t, s)
        last = s.get("pending_report") or {}
        if _m_state.now() - s.get("submitted", _m_state.now()) >= _m_state.PENDING_REPORT_S and (
                last.get("reason") != reason or _m_state.now() - last.get("at", 0) >= _m_state.PENDING_REREPORT_S):
            msg = "stage %s Job %s Pending %s: %s" % (s["id"], s["job"], _m_state.ago(s["submitted"]), reason)
            _m_state.task_txn(n, lambda t: (_m_state.tstage(t, s["id"]).update(pending_report={"reason": reason, "at": _m_state.now()}), _m_state.tev(t, msg)))
            _m_notify.digest("pending", msg, n)
        gpu = _m_task_registry.manifest_gpu(s.get("manifest")) or any(
            float(((c.get("resources") or {}).get(k) or {}).get("nvidia.com/gpu", 0)) > 0
            for p in pods for c in (p.get("spec") or {}).get("containers", []) for k in ("requests", "limits"))
        ceiling = queue_ceiling_seconds(s["queue_wait_ceiling"]) if "queue_wait_ceiling" in s else (6 * 3600 if gpu else None)
        if ceiling and q and not q.get("fired") and _m_state.now() - q["since"] >= ceiling * q.get("multiplier", 1) and _m_state.task_load(n)["status"] not in _m_state.TASK_HELD:
            q["fired"] = True
            _m_state.task_txn(n, lambda t: (_m_state.tstage(t, s["id"]).update(queue_wait=q), t.update(queue_hold=s["id"])))
            choices = "keep waiting (nrp-monitor task resume %s re-arms at 2x)" % n
            if s.get("cpu_fallback"):
                choices += ", switch to declared CPU fallback %s" % json.dumps(s["cpu_fallback"])
            _m_ladder.to_coordinator(n, "stage %s queue wait %s: %s. Choose: %s, or cancel. Job stays queued." % (s["id"], _m_state.ago(q["since"]), reason, choices))


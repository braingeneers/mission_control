"""NRP monitor sizing (mechanical extraction; R3a)."""
import json
import re

from . import cluster as _m_cluster, state as _m_state


def cpu_quantity(value):
    text = str(value).strip()
    factor = {"m": .001, "u": .000001, "n": .000000001}.get(text[-1:], 1)
    return float(text[:-1] if factor != 1 else text) * factor






def true_memory_peak(text, container=None):
    """Read the helper's JSON lines. RSS fallback is evidence, not a cgroup true peak."""
    peaks = []
    for line in text.splitlines():
        if not line.startswith("NRP_MEMORY_PEAK "):
            continue
        try:
            row = json.loads(line.split(" ", 1)[1])
            value = row["bytes"]
            if (row.get("source") in ("cgroup_v2", "cgroup_v1") and
                    row.get("container") == container and
                    isinstance(value, int) and not isinstance(value, bool) and value > 0):
                peaks.append(value)
        except (ValueError, KeyError, TypeError):
            continue
    return max(peaks) if peaks else None


def saved_memory_peak(t, s, container=None, all_attempts=False):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    logs = _m_state.task_dir(t["name"]) / "logs"
    paths = logs.glob(s["job"] + "-a*.txt") if all_attempts else [logs / ("%s-a%d.txt" % (s["job"], s.get("attempt", 1)))]
    peaks = []
    for path in paths:
        try:
            peak = true_memory_peak(path.read_text(), container)
            if peak: peaks.append(peak)
        except OSError:
            pass
    return max(peaks) if peaks else None




def mem_bytes(q):
    """Bytes of a Kubernetes memory quantity ('512Mi', '4Gi', '2G', '123456'); None when not understood."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    m = re.fullmatch(r"([\d.]+)([A-Za-z]{0,2})", str(q).strip())
    if not m or m.group(2) not in _m_state._MEM_UNITS:
        return None
    try:
        return float(m.group(1)) * _m_state._MEM_UNITS[m.group(2)]
    except ValueError:
        return None


def mem_text(b):
    import math
    return "%dGi" % math.ceil(b / 2 ** 30) if b >= 2 ** 30 else "%dMi" % max(64, math.ceil(b / 2 ** 20))


def zero_node_reason(doc):
    """Required selectors are AND; affinity terms are OR. Read errors fail open."""
    from . import cluster as _m_cluster
    from . import state as _m_state
    global UTIL_NODE_CACHE
    spec = doc["spec"]["template"]["spec"]
    selector = spec.get("nodeSelector") or {}
    required = spec.get("affinity", {}).get("nodeAffinity", {}).get("requiredDuringSchedulingIgnoredDuringExecution")
    if not selector and required is None:
        return None
    if "util_nodes" not in _m_state.PASS:
        try:
            r = _m_cluster.kubectl("get", "nodes", "-o", "json")
            UTIL_NODE_CACHE = json.loads(r.stdout)["items"] if r.returncode == 0 else None
        except Exception:
            UTIL_NODE_CACHE = None
        _m_state.PASS["util_nodes"] = len(UTIL_NODE_CACHE) if UTIL_NODE_CACHE is not None else -1
    nodes = UTIL_NODE_CACHE
    if nodes is None:
        return None
    def matches(e, labels):
        k, op, vals = e["key"], e["operator"], e.get("values", [])
        v = labels.get(k)
        if op == "In": return v in vals
        if op == "NotIn": return v not in vals
        if op == "Exists": return k in labels
        if op == "DoesNotExist": return k not in labels
        if op in ("Gt", "Lt"):
            try: return int(v) > int(vals[0]) if op == "Gt" else int(v) < int(vals[0])
            except (ValueError, TypeError, IndexError): return False
        return False
    for node in nodes:
        if node.get("spec", {}).get("unschedulable"):
            continue
        labels = node["metadata"].get("labels", {})
        if any(labels.get(k) != v for k, v in selector.items()):
            continue
        if required is None:
            return None
        for term in required.get("nodeSelectorTerms", []):
            if (term.get("matchExpressions") or term.get("matchFields")) and all(matches(e, labels) for e in term.get("matchExpressions", [])) and all(
                    matches(e, {"metadata.name": node["metadata"]["name"]}) for e in term.get("matchFields", [])):
                return None
    return "zero schedulable nodes match nodeSelector=%s required nodeAffinity=%s" % (selector, required)


UTIL_NODE_CACHE = None


def thanos_peak_mem(ns, job, container, since_ts, per_pod=False):
    """Peak working-set bytes of the Job's pods (one container) since `since_ts`, from NRP's Prometheus; None when unavailable."""
    window = max(300, int(_m_state.now() - since_ts) + 120)
    expr = 'max(max_over_time(container_memory_working_set_bytes{namespace="%s",pod=~"%s-.*",container="%s"}[%ds]))' % (ns, job, container, window)
    if per_pod:
        expr = expr.replace("max(max_over_time", "max by (pod) (max_over_time", 1)
    res = _m_cluster.thanos_query(expr)
    if per_pod:
        import math
        peaks = {}
        for r in res:
            try:
                value = float(r["value"][1])
                if math.isfinite(value) and value >= 0:
                    peaks[r["metric"]["pod"]] = value
            except (KeyError, ValueError, TypeError, IndexError):
                continue
        return peaks
    return float(res[0]["value"][1]) if res else None



def job_pod_ages(t, s, pods=None):
    """Ages from each pod's start time, falling back to its creation time."""
    from . import cluster as _m_cluster
    from . import state as _m_state
    if pods is None:
        pods = _m_cluster.job_pods(t["namespace"], s["job"])
    return {p["metadata"]["name"]: max(0, _m_state.now() - (
        _m_state.parse_ts(p.get("status", {}).get("startTime") or p["metadata"].get("creationTimestamp", ""))
        or _m_state.now())) for p in pods}


def memory_low_evidence(t, s, flagged_pod, working_set_only=False):
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    import math
    import statistics
    doc = _m_task_registry.manifest_doc(s["manifest"])
    containers = doc["spec"]["template"]["spec"]["containers"]
    resources = containers[0].get("resources", {})
    request = (mem_bytes(resources.get("requests", {}).get("memory", "")) or 0) / 2**30
    limit = (mem_bytes(resources.get("limits", {}).get("memory", "")) or 0) / 2**30
    runtime = s.get("measured_runtime_seconds")
    threshold = float(runtime) * .25 if runtime else 1800
    pods = _m_cluster.job_pods(t["namespace"], s["job"])
    ages = job_pod_ages(t, s, pods)
    age = ages.get(flagged_pod, max(0, _m_state.now() - s.get("pod_started", _m_state.now())))
    since = min(s.get("memory_since", _m_state.now()), t.get("created", _m_state.now()), s.get("submitted", _m_state.now()),
                *(_m_state.now() - age for age in ages.values()))
    peaks = thanos_peak_mem(t["namespace"], s["job"], containers[0]["name"], since, per_pod=True)
    true_peak = container_memory_peak(t, s, containers[0]["name"], single=len(containers) == 1, all_attempts=True)
    previous = s.get("memory_peaks_gi", {})
    peaks = {k: max(v / 2**30, previous.get(k, 0)) for k, v in peaks.items()} | {k: v for k, v in previous.items() if k not in peaks}
    for name in peaks:
        ages.setdefault(name, None)
    oom = list(s.get("oom_limits_gi", []))
    for attempt in t.get("attempts", []):
        if attempt.get("stage") == s["id"] and str(attempt.get("sig", "")).startswith("oom@"):
            b = mem_bytes(attempt["sig"].split("@", 1)[1])
            if b: oom.append(b / 2**30)
    for p in pods:
        for cs in p.get("status", {}).get("containerStatuses", []) or []:
            if any((cs.get(k, {}).get("terminated") or {}).get("reason") == "OOMKilled" for k in ("state", "lastState")):
                pc = next((c for c in p.get("spec", {}).get("containers", []) if c["name"] == cs.get("name")), {})
                b = mem_bytes(pc.get("resources", {}).get("limits", {}).get("memory", ""))
                if b: oom.append(b / 2**30)
    need = max(list(peaks.values()) + oom + [true_peak / 2**30 if true_peak and not peaks else 0])   # memory.peak counts page cache
    right = math.ceil(need * 1.5)
    spread = max(peaks.values()) / statistics.median(peaks.values()) if peaks and statistics.median(peaks.values()) else None
    missing = sorted((set(ages) | {flagged_pod}) - set(peaks))
    verdict = "missing peaks: review" if not peaks or missing else ("sized correctly" if request <= 1.2 * right else "oversized")
    finished = set(s.get("memory_completed_pods", [])) | {p["metadata"]["name"] for p in pods if p.get("status", {}).get("phase") == "Succeeded"}
    low_whole_life = sorted(k for k, v in peaks.items() if k in finished and v < .2 * request)
    if spread and spread > 3 and low_whole_life and not missing: verdict = "inputs differ in size"
    _m_state.task_txn(t["name"], lambda t: _m_state.tstage(t, s["id"]).update(memory_peaks_gi=peaks, oom_limits_gi=sorted(set(oom)), memory_since=since, memory_completed_pods=sorted(finished)))
    return dict(peaks_gi=peaks, ages_seconds=ages, request_gi=request, limit_gi=limit, oom_limits_gi=oom,
                true_peak_gi=true_peak / 2**30 if true_peak else None, need_gi=need, right_gi=right, spread=spread, suggested_verdict=verdict, ramp_up=age < threshold,
                missing_peak_pods=missing, low_whole_life=low_whole_life, measured_runtime_seconds=runtime, remaining_seconds=max(0, runtime-age) if runtime else None)



def thanos_peak_cpu(ns, job, container, since_ts):
    """Whole-life peak CPU rate for one Job container; None without samples."""
    window = max(300, int(_m_state.now() - since_ts) + 120)
    rows = _m_cluster.thanos_query('max(max_over_time(rate(container_cpu_usage_seconds_total{namespace=%s,pod=~%s,container=%s}[5m])[%ds:30s]))' % (json.dumps(ns), json.dumps(re.escape(job) + "-.*"), json.dumps(container), window))
    return float(rows[0]["value"][1]) if rows else None


def cpu_request(peak, small):
    """Utilization sizing: 1.5 times peak, rounded up to millicores, with policy floor."""
    import math
    return str(max(float(small.get("cpu", 1)), math.ceil(peak * 1500) / 1000)) if peak is not None else None


def container_memory_peak(t, s, container, single=False, all_attempts=False):
    """Saved cgroup peak, allowing unnamed legacy evidence only for a single container."""
    peak = saved_memory_peak(t, s, container, all_attempts=all_attempts)
    if peak is None and single:
        peak = saved_memory_peak(t, s, all_attempts=all_attempts)
    return peak

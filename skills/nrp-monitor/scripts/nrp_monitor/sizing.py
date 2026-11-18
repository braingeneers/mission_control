"""NRP monitor sizing (mechanical extraction; R3a)."""
import json
import re


def cpu_quantity(value):
    text = str(value).strip()
    factor = {"m": .001, "u": .000001, "n": .000000001}.get(text[-1:], 1)
    return float(text[:-1] if factor != 1 else text) * factor


def resource_values(doc):
    return [{"name": c["name"], **{kind: {key: value for key, value in
            c.get("resources", {}).get(kind, {}).items() if key in ("cpu", "memory")}
            for kind in ("requests", "limits")}}
            for c in doc["spec"]["template"]["spec"]["containers"]]


def resource_template(doc):
    values = resource_values(doc)
    containers = doc["spec"]["template"]["spec"]["containers"]
    return [{"name": value["name"], "image": container.get("image"),
             "resources": {kind: value[kind] for kind in ("requests", "limits")}}
            for value, container in zip(values, containers)]


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


def propagate_resources(t, source):
    """Explicit resource_group asserts compatible templates; only raise CPU/memory in files."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    group = source.get("resource_group")
    proof = next((x for x in reversed(t.get("attempts", [])) if x.get("stage") == source["id"]
                  and x.get("cls") == "resources"), {})
    if (source.get("state") != "done" or not group or not proof.get("resources_changed")
            or proof.get("by") not in ("tier0", "agent", "monitor") or not proof.get("resource_template")):
        return
    try:
        # Propagate what actually ran, even if a review edited the manifest for later runs.
        src = proof["resource_template"]
        signature = [(c["name"], c.get("image")) for c in src]
        for sibling in t["stages"]:
            if sibling["id"] == source["id"] or sibling["state"] == "done" or sibling.get("resource_group") != group:
                continue
            try:
                doc = _m_task_registry.manifest_doc(sibling["manifest"])
                dst = doc["spec"]["template"]["spec"]["containers"]
                if [(c["name"], c.get("image")) for c in dst] != signature:
                    continue
                changes = []
                for a, b in zip(src, dst):
                    for kind in ("requests", "limits"):
                        for resource in ("cpu", "memory"):
                            value = a.get("resources", {}).get(kind, {}).get(resource)
                            old = b.get("resources", {}).get(kind, {}).get(resource)
                            parse = mem_bytes if resource == "memory" else cpu_quantity
                            if value is not None and (old is None or parse(str(value)) > parse(str(old))):
                                b.setdefault("resources", {}).setdefault(kind, {})[resource] = value
                                changes.append("%s.%s.%s=%s" % (b["name"], kind, resource, value))
                if changes:
                    _m_task_registry.manifest_write(sibling["manifest"], doc)
                    _m_state.tev(t, "resource propagation %s -> %s (manifest only): %s" % (source["id"], sibling["id"], ", ".join(changes)))
            except (OSError, ValueError, KeyError, TypeError) as e:
                _m_state.tev(t, "resource propagation to %s skipped: %s" % (sibling["id"], e))
    except (OSError, ValueError, KeyError, TypeError) as e:
        _m_state.tev(t, "resource propagation from %s skipped: %s" % (source["id"], e))


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

"""Stage Job lifecycle: manifest resources, diagnostics, guarded submission and replacement.

Sizing evidence belongs to sizing.py; task state transitions stay in task/model.py.
All destructive action guards retain fresh single-Job reads.
"""
import re
import subprocess
import tempfile
from pathlib import Path


def save_task_logs(t, s, reason):
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
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


def do_submit(n, sid, reason, by):
    """Submit a stage's manifest. A failed stage = a retry (budgets enforced here, whoever asks). Returns (ok, message)."""
    from .task import model as _m_model  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import code_shipping
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import red_alert as _m_red_alert  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import sizing as _m_sizing  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import tier0 as _m_tier0  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
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
    from . import sizing as _m_sizing
    zero = _m_sizing.zero_node_reason(_m_task_registry.manifest_doc(s["manifest"]))
    if zero:
        _m_ladder.task_fail(n, sid, "unschedulable", "zero-nodes", zero)
        _m_ladder.to_coordinator(n, zero, deputy=False)
        return False, zero
    st_ = _m_cluster.job_state(s["job"], ns)
    if st_ in ("running", "pending", "error"):
        return False, "Job %s is still %s" % (s["job"], st_)
    doc = _m_task_registry.manifest_doc(s["manifest"])
    try:
        bundle = code_shipping.ensure_bundle(t, s, doc)
    except (_m_state.ChainError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
        return False, "code bundle refused: %s" % exc
    if bundle:
        _m_state.task_txn(n, lambda task: code_shipping.record_bundle(task, s["job"], bundle))
    for resource in (doc, doc["spec"]["template"]):
        metadata = resource.get("metadata") or {}
        resource["metadata"] = metadata
        labels = metadata.get("labels") or {}
        metadata["labels"] = labels
        labels.setdefault(_m_state.OWNER_LABEL_KEY, _m_state.OWNER_LABEL)
    if st_ in ("ok", "FAILED"):
        d = delete_stage_job(t, s, "before resubmit")
        if d.returncode and "NotFound" not in d.stderr:
            return False, "could not delete old Job %s: %s" % (s["job"], d.stderr.strip()[:150])
    # Shared exclusions live only in the submitted copy: expiry must restore capacity.
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
                                  "resources_changed": f2.get("resource_values") is not None and f2["resource_values"] != resource_values(doc),
                                  "resource_template": resource_template(doc) if f2["cls"] == "resources" else None})
            s2["attempt"] = s2.get("attempt", 1) + 1
            t["failure"] = None
        s2.update(state="running", submitted=_m_state.now())
        history = s2.setdefault("submitted_code_history", [])
        for info in (s2.get("submitted_code"), s2.get("done_code"), bundle):
            if info and info not in history:
                history.append(info)
        if bundle:
            s2["submitted_code"] = bundle
        else:
            s2.pop("submitted_code", None)
        s2.pop("done_code", None)
        s2.pop("done_ts", None)
        s2.pop("pod_started", None)
        s2["dl"] = {"resubmits": (s2.get("dl") or {}).get("resubmits", 0)}      # a new Job gets fresh deadline tracking (Tier 0, deadline_watch)
        for key in ("nrp_flag_since", "nrp_woken", "nrp_stopped"):
            s2.pop(key, None)
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


def utilization_restart(n, sid=None, cpu=None, mem=None, container_resources=None, coordinator_sized=False):
    """Explicit replacement, without a failure or retry. Delete only a registered stage Job."""
    from . import ladder as _m_ladder
    from . import notify as _m_notify
    from . import sizing as _m_sizing
    from . import state as _m_state
    from .task import registry as _m_task_registry
    from .task import model as _m_model
    t = _m_state.task_load(n)
    if not t or _m_ladder.terminal_task(n):
        return False, "task missing or terminal"
    candidates = [s for s in t["stages"] if s["state"] == "running"]
    s = _m_state.tstage(t, sid) if sid else (candidates[0] if len(candidates) == 1 else None)
    if not s or s["state"] not in ("running", "pending"):
        return False, "select a running or pending stage"
    problems = _m_task_registry.manifest_configmap_problems(s["manifest"])
    if problems:
        return False, "manifest refused: " + "; ".join(problems)
    doc = _m_task_registry.manifest_doc(s["manifest"])
    import math
    for value, parse in ((cpu, _m_sizing.cpu_quantity), (mem, _m_sizing.mem_bytes)):
        if value is None:
            continue
        try:
            parsed = parse(str(value)) or 0
            if not math.isfinite(parsed) or parsed <= 0:
                return False, "resources must be positive finite quantities"
        except (ValueError, TypeError, OverflowError):
            return False, "invalid resource quantity"
    for c in doc["spec"]["template"]["spec"]["containers"]:
        sized = (container_resources or {}).get(c["name"], {})
        for key, value in (("cpu", sized.get("cpu", cpu)), ("memory", sized.get("memory", mem))):
            if value is not None:
                for kind in ("requests", "limits"):
                    c.setdefault("resources", {}).setdefault(kind, {})[key] = str(value)
    r = delete_stage_job(t, s, "utilization restart")
    if r.returncode and "NotFound" not in r.stderr:
        return False, "could not delete old Job: " + r.stderr[:150]
    _m_task_registry.manifest_write(s["manifest"], doc)
    def reset(cur):
        stage = _m_state.tstage(cur, s["id"])
        stage.update(state="pending", attempt=stage.get("attempt", 1) + 1)
        if coordinator_sized:
            stage["coordinator_sized"] = _m_state.now()
        for key in ("nrp_flag_since", "nrp_woken", "nrp_stopped", "submitted"):
            stage.pop(key, None)
        cur.pop("util_event", None)
        cur["webhook_outbox"] = []
        _m_model.transition(cur, "release")
        _m_state.tev(cur, "utilization restart stage %s cpu=%s memory=%s (no retry)" % (s["id"], cpu, mem))
    _m_state.task_txn(n, reset)
    _m_notify.digest("util-restart", "stage %s cpu=%s memory=%s" % (s["id"], cpu, mem), n)
    return True, "restart queued for next pass"


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


def propagate_resources(t, source):
    """Explicit resource_group asserts compatible templates; only raise CPU/memory in files."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import sizing as _m_sizing
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
                            parse = _m_sizing.mem_bytes if resource == "memory" else _m_sizing.cpu_quantity
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


def delete_stage_job(t, s, reason):
    """Save stage diagnostics before deleting its registered Job; return raw kubectl result."""
    from . import cluster as _m_cluster
    save_task_logs(t, s, reason)
    return _m_cluster.delete_owned_job(t["namespace"], s["job"], wait=True)

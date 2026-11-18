"""NRP monitor decisions (mechanical extraction; R3a)."""
import fcntl
import hashlib
import json
import re
import sys

from . import notify as _m_notify, s3 as _m_s3, state as _m_state
from .task import registry as _m_task_registry


# ---- failure decisions and cost evidence ---------------------------------------------------------------
def scaled_retry_cap(stages):
    return max(4, (len(stages) + 3) // 4)


def fingerprint(t, failure):
    stage = _m_state.tstage(t, failure["stage"])
    def normalize(value):
        value = str(value).lower().replace(stage["job"].lower(), "STAGE")
        value = re.sub(r"[0-9a-f]{8,}", "H", value)
        value = re.sub(r"\d+", "N", value)
        return " ".join(value.split())
    group = stage.get("resource_group")
    if not group:
        def command(tokens):
            if not isinstance(tokens, list):
                return tokens
            result, selector = [], False
            flag = r"(?i)(?:--)?(?:(?:shard|partition|array|worker)[-_]?(?:index|id)|index|rank)"
            for token in tokens:
                value = str(token)
                if selector and re.fullmatch(r"[0-9]+", value):
                    value = "N"
                value = re.sub(r"^(" + flag.replace("(?i)", "") + r")=([0-9]+)$", r"\1=N", value, flags=re.I)
                selector = bool(re.fullmatch(flag, value))
                result.append(value.replace(stage["job"], "STAGE"))
            return result
        try:
            containers = _m_task_registry.manifest_doc(stage["manifest"])["spec"]["template"]["spec"]["containers"]
            group = [(c.get("image"), command(c.get("command")), command(c.get("args"))) for c in containers]
        except (OSError, ValueError, KeyError, TypeError):
            # Missing identity must not allow a decision to cross unknown stages.
            group = ["unknown manifest", stage["id"]]
    return hashlib.sha256(json.dumps([normalize(failure.get("detail", "")), failure["cls"], group],
                                     sort_keys=True).encode()).hexdigest()[:16]


def failure_context(t):
    f = t.get("failure") or {}
    fp = f.get("fingerprint") or (fingerprint(t, f) if f else None)
    return "\nFailure fingerprint: %s\nTask decisions: %s\n" % (fp, json.dumps(decisions(t["name"])))


def cost_event(task, kind, tier, outcome, stage=None, runner=None, model=None, result=None, **extra):
    result = result or {}
    row = dict(ts=_m_state.now(), task=task, stage=stage, kind=kind, tier=tier, runner=runner, model=model,
               cost_usd=result.get("total_cost_usd"), usage=result.get("usage"),
               input_tokens=(result.get("usage") or {}).get("input_tokens"),
               output_tokens=(result.get("usage") or {}).get("output_tokens"), outcome=outcome, **extra)
    _m_state.STATE.mkdir(parents=True, exist_ok=True)
    with (_m_state.STATE / "costs.jsonl").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def cost_rows():
    rows = []
    try:
        for line in (_m_state.STATE / "costs.jsonl").read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    except FileNotFoundError:
        pass
    return rows


def decisions(n):
    return _m_notify.read_json(_m_state.task_dir(n) / "decisions.json", [])


def postcheck_failure(f):
    return f.get("sig") == "postcheck" or f.get("cls") == "postcheck"


def record_decision(t, fp, action, why, scope="task", max_uses=None, who="coordinator"):
    f = t.get("failure") or {}
    if action not in _m_state.DECISION_ACTIONS or scope not in ("stage", "task"):
        raise ValueError("invalid decision action or scope")
    if not re.fullmatch(r"[0-9a-f]{16}", fp):
        raise ValueError("fingerprint must be 16 lowercase hex characters")
    if max_uses is not None and max_uses < 1:
        raise ValueError("max_uses must be positive")
    if scope == "stage" and not f.get("stage"):
        raise ValueError("stage scope needs a current failed stage")
    if action == "skip_reuse" and postcheck_failure(f):
        raise ValueError("skip_reuse cannot resolve a failing postcheck; the coordinator must fix the acceptance script")
    entries = decisions(t["name"])
    entry = dict(fingerprint=fp, action=action, scope=scope, stage=f.get("stage"), max_uses=max_uses,
                 uses=0, who=who, why=why, ts=_m_state.now())
    # Newest decision supersedes the same scope and fingerprint.
    entries = [d for d in entries if (d["fingerprint"], d["scope"], d.get("stage") if scope == "stage" else None) !=
               (fp, scope, entry["stage"] if scope == "stage" else None)]
    entries.append(entry)
    _m_notify.write_json(_m_state.task_dir(t["name"]) / "decisions.json", entries)
    _m_state.tev(t, "recorded decision %s: %s (%s)" % (fp, action, why))


def _decide_escalate(n, t, f, fp, d, a):
    from . import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    _m_ladder.to_coordinator(n, "coordinator decision %s: %s" % (fp, d["why"]), a, deputy=False)
    return True


def _decide_skip_reuse(n, t, f, fp, d, a):
    stage = _m_state.tstage(t, f["stage"])
    if not stage.get("done_s3") or not all(_m_s3.s3_exists(uri, t) for uri in stage["done_s3"]):
        return False

    def done(task):
        _m_state.tstage(task, f["stage"])["state"] = "done"
        task["failure"] = None
    _m_state.task_txn(n, done)
    return True


def _decide_resubmit(n, t, f, fp, d, a):
    from . import stage_jobs as _m_stage_jobs
    return _m_stage_jobs.do_submit(n, f["stage"], "coordinator decision %s: %s" % (fp, d["why"]), "decision")[0]


DECISION_APPLY = {"escalate": _decide_escalate, "skip_reuse": _decide_skip_reuse}   # any other action resubmits the stage


def apply_decision(n, a):
    from . import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    if _m_ladder.terminal_task(n):
        return False
    t = _m_state.task_load(n)
    f = t.get("failure")
    if not f or t["mode"] != "auto" or a.dry_run:
        return False
    if postcheck_failure(f):
        _m_ladder.to_coordinator(n, "postcheck failed: the coordinator must fix the acceptance script; skip_reuse cannot resolve it. " + f.get("detail", ""), a, deputy=False)
        return True
    fp = f.get("fingerprint") or fingerprint(t, f)
    entries = decisions(n)
    for d in reversed(entries):
        if d["fingerprint"] != fp or (d["scope"] == "stage" and d.get("stage") != f["stage"]):
            continue
        progress = sorted(set(t.get("completed_stages", [])) | {s["id"] for s in t["stages"] if s["state"] == "done"})
        streak = (t.get("decision_streaks") or {}).get(fp)
        count = (streak["count"] if streak["progress"] == progress else 0) if streak else d.get("uses", 0)
        if count >= _m_state.DECISION_NO_PROGRESS_LIMIT:
            _m_ladder.to_coordinator(n, "decision %s applied %d times without progress (no new stage completed); coordinator action required" % (fp, count), a, deputy=False)
            return True
        if d.get("max_uses") is not None and d.get("uses", 0) >= d["max_uses"]:
            continue
        action = d["action"]
        if not DECISION_APPLY.get(action, _decide_resubmit)(n, t, f, fp, d, a):
            return False
        def consumed(task):
            # A coordinator can replace a decision while submit waits on kubectl. Never overwrite that newer log.
            current = decisions(n)
            for entry in current:
                if (entry["fingerprint"], entry["scope"], entry.get("stage"), entry["ts"]) == (d["fingerprint"], d["scope"], d.get("stage"), d["ts"]):
                    entry["uses"] = entry.get("uses", 0) + 1
                    _m_notify.write_json(_m_state.task_dir(n) / "decisions.json", current)
                    break
            task.setdefault("decision_streaks", {})[fp] = {"count": count + 1, "progress": progress}
            _m_state.tev(task, "applied coordinator decision %s" % fp)
        _m_state.task_txn(n, consumed)
        cost_event(n, "decision", "0", "escalated" if action == "escalate" else "resolved",
                   stage=f["stage"], fingerprint=fp)
        return True
    return False


def cmd_decide(a):
    if not _m_state.task_load(a.name):
        sys.exit("no task %s" % a.name)
    _m_state.task_txn(a.name, lambda t: record_decision(t, a.fingerprint, a.action, a.why, a.scope, a.max_uses))


def cmd_wake_review(a):
    wakes = [r for r in cost_rows() if r.get("task") == a.name and r.get("kind") == "coordinator_wake"]
    if not wakes:
        sys.exit("no coordinator wake recorded for " + a.name)
    cost_event(a.name, "wake_review", "coordinator", "done", by=a.by, why=a.why, wake_id=wakes[-1]["event_id"])


def cmd_costs(a):
    rows = [r for r in cost_rows() if (not a.task or r.get("task") == a.task) and r["ts"] >= _m_state.now() - a.days * 86400]
    counts, costs, resolved, reviews = {}, {}, {}, {}
    by_kind, by_task = {}, {}
    latest_reviews = {r.get("wake_id"): r for r in rows if r["kind"] == "wake_review"}
    for r in rows:
        if r["kind"] == "coordinator_wake":
            key = (r["task"], r.get("wake_kind", "unknown"))
            counts[key] = counts.get(key, 0) + 1
            by_kind[key[1]] = by_kind.get(key[1], 0) + 1
            by_task[key[0]] = by_task.get(key[0], 0) + 1
        if r["kind"] == "wake_review" and latest_reviews.get(r.get("wake_id")) == r:
            key = (r["by"], r["why"])
            reviews[key] = reviews.get(key, 0) + 1
        if r.get("cost_usd") is not None:
            key = (str(r["tier"]), str(r.get("model")))
            costs[key] = costs.get(key, 0) + r["cost_usd"]
        if r.get("fingerprint") and r["outcome"] == "resolved":
            key = str(r["tier"])
            resolved[key] = resolved.get(key, 0) + 1
    print("Completion wakes avoided: %d" % sum(r["kind"] == "wake_avoided" for r in rows))
    print("Coordinator wakes by task / kind:")
    for (task, kind), count in sorted(counts.items()):
        print("  %s / %s: %d" % (task, kind, count))
    print("Wake totals by task: " + json.dumps(by_task, sort_keys=True))
    print("Wake totals by kind: " + json.dumps(by_kind, sort_keys=True))
    print("Resolved failures by tier (recorded resolution events):")
    total = sum(resolved.values())
    for tier in ("0", "1", "2", "deputy", "coordinator"):
        count = resolved.get(tier, 0)
        print("  %s: %d (%.1f%%)" % (tier, count, 100 * count / total if total else 0))
    print("Agent costs by tier / model (unreported costs excluded):")
    for (tier, model), cost in sorted(costs.items()):
        print("  %s / %s: $%.6f" % (tier, model, cost))
    print("Wake reviews by intended handler / reason:")
    for (by, why), count in sorted(reviews.items()):
        print("  %s / %s: %d" % (by, why, count))


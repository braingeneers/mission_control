"""NRP monitor util (mechanical extraction; R3a)."""
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


def flag_rule(line):
    """Which rule flagged a pod: `gpu`, `nrp` (a CPU/memory band NRP counts) or `lab` (the lab floor only), from the `rule=` token that
    nrp-util-check ends its line with; a line without one (an older nrp-util-check) is read from its tag. `unknown` when neither says."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    m = _m_state.FLAG_RULE_RE.search(line or "")
    if m:
        return m.group(1)
    if "[NRP violation]" in (line or ""):
        return "nrp"
    if re.search(r"\bgpu\b", line or ""):
        return "gpu"
    return "lab" if re.search(r"\[lab \d+% rule", line or "") else "unknown"


def waiver_stage(t, w):
    return next((s for s in t.get("stages", []) if s.get("job") == w.get("job")), None)


def waiver_active(t, w):
    """A util waiver holds while it has not run out and the very Job it was given for still runs (a resubmit or a finished Job ends it)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    s = waiver_stage(t, w)
    return bool(s) and s.get("state") == "running" and s.get("submitted") == w.get("submitted") and _m_state.now() < w.get("until", 0)


def active_waiver(t, sid):
    """The live util waiver of stage `sid`'s Job, or None. Reads only what `util_waivers` holds, so a task written before waivers existed has none."""
    if not t:
        return None
    s = next((x for x in t.get("stages", []) if x.get("id") == sid), None)
    return next((w for w in t.get("util_waivers") or [] if s and w.get("job") == s.get("job") and waiver_active(t, w)), None)


def util_ok_extract(text):
    """The evidence text after the LAST `UTIL_OK:` line of a fix agent's answer (that line and the lines after it up to a blank line,
    HANDOFF_ENTRY or FOR_OWNER), whitespace collapsed, at most 400 characters; None when the answer has no such line."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    ms = list(_m_state.UTIL_OK_RE.finditer(text or ""))
    if not ms:
        return None
    m = ms[-1]
    parts = [m.group(1)]
    for l in text[m.end():].split("\n")[1:]:
        if not l.strip() or re.match(r"^[ \t>*_`#-]*(HANDOFF_ENTRY|FOR_OWNER)\b", l):
            break
        parts.append(l)
    out = " ".join(" ".join(parts).replace("*", "").replace("`", "").split())[:_m_state.UTIL_OK_REASON_MAX]
    return out


def util_waiver_check(t, f, claim):
    """(ok, why): whether the script accepts the fix agent's UTIL_OK. The script decides, never the agent's claim: the failure is class util;
    the flag came from the lab floor only (not an NRP band, not a GPU flag); the stage is not a GPU stage; the Job exists and is running now;
    the task still has waivers left."""
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import config as _m_config  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    cap = _m_config.util_waiver_max()
    s = next((x for x in t["stages"] if x["id"] == f.get("stage")), None)
    if not claim:
        return False, "UTIL_OK gave no evidence"
    if f.get("cls") != "util":
        return False, "the failure class is %s, not util" % f.get("cls")
    rule = f.get("rule")
    if rule != "lab":
        return False, ("the flag came from rule %s (NRP-band and GPU flags are never waived)" % rule) if rule else \
            "the failure records no flag rule (written before waivers existed)"
    if s is None or s["job"] != f.get("job"):
        return False, "the failed stage is not in the task"
    if s.get("gpu_ok_until") or s.get("gpu_plan") or (s.get("manifest") and _m_task_registry.manifest_gpu(s["manifest"])):
        return False, "stage %s requests a GPU (GPU stages are never waived)" % s["id"]
    for note in (t.get("util") or [])[-5:]:                                   # another pod of the Job flagged outside NRP's bands or on a GPU
        m = re.match(r"^(\S+) \[(nrp|gpu)\] ", note)
        try:
            if m and _m_state.now() - datetime.fromisoformat(m.group(1)).timestamp() < 2 * 3600:
                return False, "another flag on this task's pods came from rule %s at %s" % (m.group(2), m.group(1))
        except ValueError:
            pass
    if len(t.get("util_waivers") or []) >= cap:
        return False, "this task has used its %d util waiver(s)" % cap
    st_ = _m_cluster.job_state(f["job"], t["namespace"])
    if st_ != "running":
        return False, "Job %s is %s now, not running" % (f["job"], st_)
    return True, ""


def util_waive(n, f, claim, a):
    """Accept the waiver: the stage goes back to running, the failure clears, no retry is used, nobody is messaged. Returns (ok, why)."""
    from . import config as _m_config  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = _m_state.task_load(n)
    ok, why = util_waiver_check(t, f, claim)
    if not ok:
        return False, why
    hours = _m_config.util_waiver_hours()
    out = {}

    def acc(t):
        cur = t.get("failure")
        if not cur or cur.get("ts") != f.get("ts"):
            out["why"] = "the failure changed while the waiver was checked"
            return False
        s = _m_state.tstage(t, f["stage"])
        at = _m_state.now()
        w = {"job": f["job"], "pod": f.get("pod") or "", "stage": f["stage"], "reason": claim[:_m_state.UTIL_OK_REASON_MAX], "at": at,
             "until": at + hours * 3600, "submitted": s.get("submitted")}
        t.setdefault("util_waivers", []).append(w)
        t["failure"] = None
        s["state"] = "running"
        s.pop("util_deleted", None)
        t.pop("util_ok_claim", None)
        out["w"], out["k"] = w, len(t["util_waivers"])
        _m_state.tev(t, "util waiver %d of %d for %s until %s: %s" % (out["k"], _m_config.util_waiver_max(), f["job"], _m_state.iso(w["until"]), claim[:160]))
        try:
            when = datetime.fromtimestamp(at, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            _m_wake.handoff_append(t, "%s | monitor | util waiver %d of %d | [util] stage %s" % (when, out["k"], _m_config.util_waiver_max(), f["stage"]),
                           [("Fix log", "Util flag waived until %s (the Job runs and only the lab floor flagged it): %s" % (_m_state.iso(w["until"]), claim[:_m_state.UTIL_OK_REASON_MAX]))])
        except Exception as e:
            _m_state.log("task %s: handoff entry for the waiver not written: %s: %s" % (t["name"], type(e).__name__, str(e)[:120]))
    if not _m_state.task_txn(n, acc):
        return False, out.get("why", "the task changed")
    _m_decisions.cost_event(n, "waiver_resolution", "2", "resolved", stage=f["stage"], fingerprint=f.get("fingerprint") or _m_decisions.fingerprint(t, f))
    _m_notify.digest("util-waived", "Job %s is running and only the lab utilization floor flags it (waiver %d of %d, until %s): %s"
           % (f["job"], out["k"], _m_config.util_waiver_max(), _m_state.iso(out["w"]["until"]), claim[:240]), n)
    return True, ""


def task_pod_flag(st, n, sid, pod, kind, line):
    """Utilization is a judge event, never a stage failure. STUCK remains an infrastructure failure."""
    from . import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if kind == "STUCK":
        _m_ladder.task_fail(n, sid, "infra", "stuck:" + _m_state.norm_sig(line.split(" ", 2)[-1])[:60], "pod %s STUCK: %s" % (pod, line[:200]))
        return
    rule = flag_rule(line)
    if rule == "lab" and active_waiver(_m_state.task_load(n), sid):               # the owner-side lab floor only, and the fix agent showed the Job is healthy
        st["strikes"].pop(pod, None)
        return
    t = _m_state.task_load(n)
    stage = _m_state.tstage(t, sid)
    evidence = memory_low_evidence(t, stage, pod, working_set_only=rule == "nrp") if kind == "LOW" and any(k == "mem" and int(pct) < 20 for k, use, req, pct, mx in _m_state.FLAG_RES.findall(line)) else None
    if evidence and evidence["ramp_up"]:
        return
    if stage["state"] != "running":
        return
    event = {"stage": sid, "job": stage["job"], "cls": "util", "sig": "util:" + _m_state.norm_sig(line),
             "detail": line, "ts": _m_state.now(), "evidence": evidence, "rule": rule, "pod": pod}
    def record(t):
        t.setdefault("util", []).append("%s [%s] %s" % (_m_state.iso(), rule, line[:200]))
        del t["util"][:-10]
        if not t.get("util_event"):
            t["util_event"] = event
            _m_state.tev(t, "utilization observation (stage keeps running): " + line)
            if evidence:
                _m_state.tev(t, "memory request=%gGi limit=%gGi need=%gGi right=%dGi spread=%s: %s" % (
                    evidence["request_gi"], evidence["limit_gi"], evidence["need_gi"], evidence["right_gi"],
                    evidence["spread"], evidence["suggested_verdict"]))
    _m_state.task_txn(n, record)


def process_util_event(n, a):
    from . import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import task_agents as _m_task_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    if _m_ladder.terminal_task(n):
        return
    t = _m_state.task_load(n)
    event = t.get("util_event")
    if not event or t.get("failure") or a.dry_run:
        return
    if _m_state.tstage(t, event["stage"])["state"] != "running":
        _m_state.task_txn(n, lambda t: t.pop("util_event", None))
        return
    context = dict(t, failure=event)
    numbers = json.dumps(event.get("evidence"), sort_keys=True)
    if event.get("rule") == "nrp":                                        # below NRP's own floor: the review may not end in "no change"
        return util_nrp_review(n, t, event, context, numbers, a)
    prompt = _m_ladder.triage_prompt(context) + "\nMemory evidence (GiB): " + numbers + "\n" + _m_state.MEMORY_RULE
    line, _ = _m_task_agents.run_task_agent(n, prompt, a, kind="triage")
    if _m_agents.is_unavailable(line):
        return
    runs = _m_state.task_load(n).get("agent_runs") or []
    verdict = runs[-1].get("verdict", "ESCALATE") if runs else "ESCALATE"
    if verdict not in _m_state.TRIAGE_CLOSE and t.get("mode") == "watch":
        _m_notify.digest("util-review", "watch-only task: judge recommends fixer review; running Job left alone. " + line, n)
    elif verdict not in _m_state.TRIAGE_CLOSE:
        context["failure"]["triage_text"] = "%s: %s" % (verdict, runs[-1].get("verdict_text", line) if runs else line)
        line, _ = _m_task_agents.run_task_agent(n, _m_task_agents.task_prompt(context) + "\nMemory evidence (GiB): " + numbers + "\n" + _m_state.MEMORY_RULE, a)
        if _m_agents.is_unavailable(line):
            return
    _m_state.task_txn(n, lambda t: (t.pop("util_event", None), _m_state.tstage(t, event["stage"]).update(util_reviewed=_m_state.now()), _m_state.tev(t, "utilization review: " + line)))


def util_nrp_review(n, t, event, context, numbers, a):
    """An NRP-floor observation: the fixer resizes/restarts, or (watch-only, or the fixer left the same Job running) the coordinator chat is
    woken visibly. Never closed as "no change"."""
    from . import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import task_agents as _m_task_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    sid = event["stage"]
    before = _m_state.tstage(t, sid).get("submitted")
    line = "watch-only task: no fixer"
    if t.get("mode") != "watch":
        line, _ = _m_task_agents.run_task_agent(n, _m_task_agents.task_prompt(context) + "\nMemory evidence (GiB): " + numbers + "\n" + _m_state.MEMORY_RULE + "\n" + _m_state.NRP_UTIL_RULE, a)
        if _m_agents.is_unavailable(line):
            return
    cur = _m_state.task_load(n)
    s = _m_state.tstage(cur, sid)
    acted = s.get("submitted") != before or s["state"] != "running" or (cur.get("failure") or {}).get("stage") == sid
    text = ("NRP task %s: Job %s is below NRP's 20%% utilization floor (an NRP violation: NRP refuses new pods on the whole account when "
            "pods stay below it). %s Resize now: request = ceil(NRP Thanos whole-life working-set peak x 1.5), limit within 20%% of request "
            "(never from a cgroup memory.peak / profile peak: it counts page cache); restart only if the stage resumes from saved progress, "
            "otherwise decide now whether to delete it. \"No change\" is not an allowed answer. Evidence (GiB): %s. Look: `nrp-monitor task show %s`."
            % (n, event["job"], event["detail"][:200], numbers[:900], n))

    def f(t):
        t.pop("util_event", None)
        _m_state.tstage(t, sid).update(util_reviewed=_m_state.now())
        _m_state.tev(t, "utilization review (NRP floor): " + line)
        if not acted:
            woke = _m_wake.queue_task_webhook(t, "util_nrp", summary=text)
            _m_state.tev(t, "NRP floor not fixed by the review; coordinator chat %s" % ("woken" if woke else "has no wake target (digest only)"))
    _m_state.task_txn(n, f)
    if not acted:
        _m_notify.digest("util-review", "NRP violation not fixed by the review; coordinator chat woken: " + event["detail"][:200], n)


def memory_low_evidence(t, s, flagged_pod, working_set_only=False):
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import sizing as _m_sizing  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import tier0 as _m_tier0  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    import math
    import statistics
    doc = _m_task_registry.manifest_doc(s["manifest"])
    containers = doc["spec"]["template"]["spec"]["containers"]
    resources = containers[0].get("resources", {})
    request = (_m_sizing.mem_bytes(resources.get("requests", {}).get("memory", "")) or 0) / 2**30
    limit = (_m_sizing.mem_bytes(resources.get("limits", {}).get("memory", "")) or 0) / 2**30
    runtime = s.get("measured_runtime_seconds")
    threshold = float(runtime) * .25 if runtime else 1800
    pods = _m_cluster.job_pods(t["namespace"], s["job"])
    ages = {p["metadata"]["name"]: max(0, _m_state.now() - (_m_state.parse_ts(p.get("status", {}).get("startTime") or p["metadata"].get("creationTimestamp", "")) or _m_state.now())) for p in pods}
    age = ages.get(flagged_pod, max(0, _m_state.now() - s.get("pod_started", _m_state.now())))
    since = min(s.get("memory_since", _m_state.now()), t.get("created", _m_state.now()), s.get("submitted", _m_state.now()),
                *(_m_state.now() - age for age in ages.values()))
    peaks = _m_tier0.thanos_peak_mem(t["namespace"], s["job"], containers[0]["name"], since, per_pod=True)
    true_peak = _m_sizing.saved_memory_peak(t, s, containers[0]["name"], all_attempts=True)
    if true_peak is None and len(containers) == 1:
        true_peak = _m_sizing.saved_memory_peak(t, s, all_attempts=True)
    previous = s.get("memory_peaks_gi", {})
    peaks = {k: max(v / 2**30, previous.get(k, 0)) for k, v in peaks.items()} | {k: v for k, v in previous.items() if k not in peaks}
    for name in peaks:
        ages.setdefault(name, None)
    oom = list(s.get("oom_limits_gi", []))
    for attempt in t.get("attempts", []):
        if attempt.get("stage") == s["id"] and str(attempt.get("sig", "")).startswith("oom@"):
            b = _m_sizing.mem_bytes(attempt["sig"].split("@", 1)[1])
            if b: oom.append(b / 2**30)
    for p in pods:
        for cs in p.get("status", {}).get("containerStatuses", []) or []:
            if any((cs.get(k, {}).get("terminated") or {}).get("reason") == "OOMKilled" for k in ("state", "lastState")):
                pc = next((c for c in p.get("spec", {}).get("containers", []) if c["name"] == cs.get("name")), {})
                b = _m_sizing.mem_bytes(pc.get("resources", {}).get("limits", {}).get("memory", ""))
                if b: oom.append(b / 2**30)
    need = max(list(peaks.values()) + oom + [true_peak / 2**30 if true_peak and not working_set_only else 0])   # memory.peak counts page cache
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


def check_orphans(a, st):
    """the owner's running Jobs that no task, chain or registration covers go to the digest once."""
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    try:
        js = _m_cluster.jobs_in(_m_state.NS)
    except Exception:
        return
    known = set()
    for n in _m_state.task_names():
        known |= {s["job"] for s in (_m_state.task_load(n) or {}).get("stages", [])}
    known |= {j for j, r in st["jobs"].items() if r.get("status") == "watching"}
    seen = _m_notify.read_json(_m_state.ORPHANS, {})
    live = {j for j, i in js.items() if i["ours"] and i["state"] in ("running", "pending") and j not in known}
    for j in sorted(live - set(seen)):
        if not a.dry_run:
            _m_notify.digest("unregistered", "Job %s is running but no task or chain watches it" % j)
        seen[j] = _m_state.iso()
    seen = {j: v for j, v in seen.items() if j in live}
    if not a.dry_run:
        _m_notify.write_json(_m_state.ORPHANS, seen)


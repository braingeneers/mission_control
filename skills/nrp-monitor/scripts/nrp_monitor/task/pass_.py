"""NRP monitor task/pass_ (mechanical extraction; R3a)."""
import hashlib
import json
import os
import subprocess

# ---- task pass ---------------------------------------------------------------------------------------------------


def run_postcheck(t):
    from .. import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    check = t.get("postcheck")
    if not check:
        return {"ok": True, "output": "no postcheck declared"}
    try:
        r = subprocess.run(check["cmd"], cwd=next((c for c in [(t.get("code") or {}).get("clone")] if c and os.path.isdir(c)), None) or _m_state.task_dir(t["name"]),
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
    from .. import stage_jobs as _m_stage_jobs
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
            ok, msg = _m_stage_jobs.do_submit(n, p.get("stage"), p.get("reason", "re-apply after block"), "monitor") if p else (False, "no pending submit")
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
            ok, msg = _m_stage_jobs.do_submit(n, s["id"], "stage ready", "monitor")
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
        if (t.get("code") and os.path.isdir(t["code"]["clone"]) and _m_task_registry.git(          # commits past the task-add snapshot are a fixer's
                "rev-list", "--count", "%s..HEAD" % (t["code"].get("snapshot") or t["code"]["base"]), cwd=t["code"]["clone"]).stdout.strip() not in ("", "0")):
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
    from .. import stage_jobs as _m_stage_jobs
    from . import model as _m_model  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import s3 as _m_s3  # Local import breaks orchestration cycle; patches stay on the defining module.
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
            _m_stage_jobs.propagate_resources(t, _m_state.tstage(t, s["id"]))
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


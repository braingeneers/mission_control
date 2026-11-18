"""NRP monitor legacy (mechanical extraction; R3a)."""
import re
import subprocess
from pathlib import Path

# ---- run -----------------------------------------------------------------------------------------------------
def acct_alarm(st, lines, bad, dry, mine=None):
    """Push once when NRP's own count (or our [NRP violation]/STUCK flags) is 3+ on 2 passes in a row.
    One high pass is ignored: nrp-util-check's account count includes pods that started a minute ago."""
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    acct = max([int(m.group(1)) for l in lines for m in [_m_state.ACCT.search(l)] if m] or [0])
    nrp = [f[1] for f in bad if f[0] == "STUCK" or "[NRP violation]" in f[2]]
    hi = acct >= 3 or len(nrp) >= 3
    if not dry:
        st["acct_hi"] = st.get("acct_hi", 0) + 1 if hi else 0
    if hi and st.get("acct_hi", 0) >= 2:
        owners = [o for o in (_m_wake.owner_of_job(st, (mine or {}).get(p)) for p in nrp) if o]     # chats whose pods are flagged (may be none)
        _m_notify.push("NRP counts %d of your running pods outside its utilization bands on 2 passes in a row (it blocks new submits "
             "past 4)%s. The monitor deletes and resizes task and chain pods at strike 2; other pods need you."
             % (acct, ("; flagged: " + ", ".join(nrp))[:160] if nrp else ""), "acct", dry, refs=owners)
    elif acct < 2 and not nrp:
        _m_notify.push_clear("acct")


def check_pods(a, st):
    from . import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import util as _m_util  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import model as _m_task_model  # Local import breaks orchestration cycle; patches stay on the defining module.
    if a.fake_util:
        lines = Path(a.fake_util).read_text().splitlines()
        mine = {m.group(2): None for m in map(_m_state.FLAG.match, lines) if m}      # fake input: trust the file
        code = 4 if mine else 0
    else:
        mine = _m_cluster.my_pods()
        if not mine:
            return
        try:
            gpu_long_pass(a, st, mine)                                    # the 3 h GPU average NRP enforces; independent of the 10-min strikes
        except Exception as e:                                            # never let it stop the rest of the utilization pass
            _m_state.log("gpu-long error: %s: %s" % (type(e).__name__, str(e)[:150]))
            _m_notify.push("the 3 h GPU check failed (%s: %s); GPU pods are only checked on 10-min samples" % (type(e).__name__, str(e)[:80]),
                 "gpu-long-error", a.dry_run)
        r = subprocess.run(["nrp-util-check", "-n", _m_state.NS, "--min-age", "300"] + sorted(mine),
                           capture_output=True, text=True, timeout=300)
        lines, code = r.stdout.splitlines(), r.returncode
        if code == 2:
            st["errors"] += 1
            _m_state.log("util-check error: " + r.stdout.strip()[:150])
            if st["errors"] >= 6:
                _m_notify.push("nrp-util-check has failed %d passes in a row, pod utilization is unchecked: %s" % (st["errors"], r.stdout.strip()[:100]),
                     "util-error", a.dry_run)
            return
        st["errors"] = 0
        _m_notify.push_clear("util-error")
        if code in (0, 5):
            st["strikes"].clear()
            acct_alarm(st, lines, [], a.dry_run, mine)
            return
    flagged = [(m.group(1), m.group(2), l) for l in lines for m in [_m_state.FLAG.match(l)] if m and m.group(2) in mine]
    if a.dry_run:
        print("[dry-run] nrp-util-check flagged %d of your pods" % len(flagged))
    bad = [f for f in flagged if f[0] in ("LOW", "STUCK")]
    for pod in [p for p in st["strikes"] if p not in {f[1] for f in bad}]:
        del st["strikes"][pod]                                               # not flagged this pass: reset
    acct_alarm(st, lines, bad, a.dry_run, mine)
    launched = 0
    for kind, pod, line in flagged:
        strike = 2 if st["strikes"].get(pod) else 1
        gap = 10**9 if kind == "FAILED" else (_m_state.STRIKE_GAP_S if strike == 2 else _m_state.POD_DEDUPE_S)
        if _m_state.now() - st["pods"].get(pod, 0) < gap:
            continue
        if kind == "FAILED":
            if not a.dry_run:
                st["pods"][pod] = _m_state.now()
            _m_notify.notify("pod %s FAILED (not deleted; read its logs, delete the Job when done)" % pod, st, None, a.dry_run,
                   ref=_m_wake.owner_of_job(st, mine.get(pod)) or "-")
            continue
        owner = mine.get(pod)
        tk = _m_state.task_of_job(owner) if owner else None
        if tk:                                                            # a task's pod: the task's fix agent handles it
            if not a.dry_run:
                st["pods"][pod] = _m_state.now()
                _m_util.task_pod_flag(st, tk[0], tk[1], pod, kind, line)
            else:
                print("[dry-run] pod %s belongs to task %s: %s" % (pod, tk[0], line[:120]))
            continue
        if kind == "LOW" and not ("[NRP violation]" in line and strike == 2):
            if not a.dry_run:                                             # strike 1 / lab rule: record the resize, silent
                st["pods"][pod] = _m_state.now()
                if "[NRP violation]" in line:
                    st["strikes"][pod] = {"n": 1, "t": _m_state.now(), "owner": owner}
                record_resize(st, pod, owner, line, "OVERSIZED: " + _m_task_model.resize_advice(line))
            else:
                print("[dry-run] pod %s strike %d: record resize %s" % (pod, strike, _m_task_model.resize_advice(line)))
            continue
        if launched >= _m_state.MAX_POD_AGENTS:
            break
        launched += 1
        cmd = _m_agents.agent_cmd("pod", _m_agents.pod_allowed(pod, owner))
        if a.dry_run:
            print("[dry-run] would launch pod-check agent for %s (owner job: %s, strike %d)\n[dry-run]   cwd=%s\n[dry-run]   %s"
                  % (pod, owner, strike, _m_state.WORK / "pod_check", " ".join(repr(c) if " " in c or "(" in c else c for c in cmd)))
            continue
        if not _m_agents.agents_available():                                        # no runner has usage left: the pod stays flagged for the next pass
            _m_state.log("pod-check %s waits: %s" % (pod, _m_agents.unavailable_text()))
            continue
        st["pods"][pod] = _m_state.now()
        _m_state.save(st)
        _m_state.log("pod-check start %s (strike %d): %s" % (pod, strike, line[:160]))
        cmd.spec["ledger_task"] = "pod:" + pod
        res = _m_agents.run_agent(cmd, _m_agents.pod_prompt(pod, line, owner, strike), _m_state.WORK / "pod_check")
        _m_state.log("pod-check %s: %s" % (pod, res[:300]))
        verdict = res.split(":")[0].split()[0] if res.strip() else ""
        st["strikes"].pop(pod, None)
        if verdict in ("OVERSIZED", "DELETED"):
            record_resize(st, pod, owner, line, res)
        if verdict not in ("DELETED", "NOTFOUND"):
            _m_notify.push("pod %s (%s) was not deleted at strike 2/STUCK, check by hand: %s" % (pod, "[NRP violation]" if "[NRP violation]" in line else kind, res[:160]),
                 "pod:%s" % pod, refs=[_m_wake.owner_of_job(st, owner)] if _m_wake.owner_of_job(st, owner) else [])
        else:
            _m_notify.notify("pod-check %s: %s" % (pod, res[:200]), ref=_m_wake.owner_of_job(st, owner) or "-")


def _gpu_low(lines, mine, min_age_s):
    """[(pod, lowest GPU %% or None when no DCGM series, age_s, line)] for LOW lines of our pods at least `min_age_s` old that carry a GPU
    number under the floor nrp-util-check applied (or no DCGM series). CPU/memory-only lines are ignored (they stay with the 10-min strikes)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    out = []
    for l in lines:
        m = _m_state.FLAG.match(l)
        if not m or m.group(1) != "LOW" or m.group(2) not in mine:
            continue
        am = _m_state.AGE_RE.search(l)
        age_s = int(am.group(1)) * 60 if am else 0
        pcts = [float(x) for x in _m_state.GPU_PCT_RE.findall(l)]
        no_dcgm = "no DCGM series" in l
        if age_s < min_age_s or not (pcts or no_dcgm):
            continue
        out.append((m.group(2), None if no_dcgm or not pcts else min(pcts), age_s, l))
    return out


def gpu_long_actions(warn_lines, enforce_lines, mine):
    """[(pod, "enforce"|"warn", pct, age_s, line)] from two `nrp-util-check --frac <gpu_floor>` runs:
    enforce: the GPU_ENFORCE_WINDOW_MIN (90 min) mean is under NRP's floor and the pod is at least that old (DCGM numbers only);
    warn: the GPU_WARN_WINDOW_MIN (1 h) mean is under the floor (or there is no DCGM series) and the pod is at least that old.
    The lowest GPU of a multi-GPU pod decides. A pod without a DCGM series is warned, never enforced."""
    from . import config as _m_config  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    floor = 100 * _m_config.gpu_floor()
    out = [(pod, "enforce", pct, age_s, l) for pod, pct, age_s, l in _gpu_low(enforce_lines, mine, _m_state.GPU_ENFORCE_WINDOW_MIN * 60)
           if pct is not None and pct < floor]
    done = {o[0] for o in out}
    out += [(pod, "warn", pct, age_s, l) for pod, pct, age_s, l in _gpu_low(warn_lines, mine, _m_state.GPU_WARN_WINDOW_MIN * 60)
            if pod not in done and (pct is None or pct < floor)]
    return out


def gpu_long_pass(a, st, mine):
    """NRP's GPU rule is a ~3 h average above 40 %. The 10-min strikes reset whenever one sample is fine, so a Job that alternates GPU and
    CPU phases (RT-Sort: detect on the GPU, merge on the CPU) passed every check while its 3 h mean sat at 36 % (NRP warning 2026-11-15).
    This pass reads long windows directly: a 1 h mean under NRP's floor wakes the owning chat; a 90-min mean under it
    saves the logs and deletes the Job itself, so NRP never has to; a task's stage then fails as class util with rule gpu (the fixer
    must restructure, e.g. run levels in parallel or move CPU phases off the GPU pod, never resubmit unchanged)."""
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import config as _m_config  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import pass_ as _m_task_pass_  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not mine:
        return
    def check(window):
        r = subprocess.run(["nrp-util-check", "-n", _m_state.NS, "--min-age", str(window * 60), "--window", str(window), "--frac", str(_m_config.gpu_floor())]
                           + sorted(mine), capture_output=True, text=True, timeout=300)
        if r.returncode == 2:
            raise RuntimeError("nrp-util-check exit 2: " + r.stdout.strip()[:120])
        return r.stdout.splitlines()
    warn_lines, enforce_lines = check(_m_state.GPU_WARN_WINDOW_MIN), check(_m_state.GPU_ENFORCE_WINDOW_MIN)
    seen = st.setdefault("gpu_long", {})
    for pod in [p for p in seen if p not in mine]:
        del seen[pod]
    for pod, action, pct, age_s, line in gpu_long_actions(warn_lines, enforce_lines, mine):
        owner = mine.get(pod)
        tk = _m_state.task_of_job(owner) if owner else None
        refs = [_m_wake.owner_of_job(st, owner)] if owner and _m_wake.owner_of_job(st, owner) else []
        pct_s = "?" if pct is None else "%.0f%%" % pct
        if action == "warn":
            if _m_state.now() - seen.get(pod, {}).get("warned", 0) < _m_state.GPU_WARN_DEDUPE_S:
                continue
            if a.dry_run:
                print("[dry-run] gpu-long WARN %s %s over %d min" % (pod, pct_s, _m_state.GPU_WARN_WINDOW_MIN))
                continue
            seen.setdefault(pod, {})["warned"] = _m_state.now()
            _m_state.log("gpu-long WARN %s: %s" % (pod, line[:200]))
            text = ("URGENT, ACT NOW: GPU pod %s (Job %s) averaged only %s GPU over the last %d min, under NRP's %d%% floor. This is a cluster "
                 "policy violation in progress: NRP deletes idle GPU pods, records a strike, and three strikes get the account suspended (the "
                 "whole lab loses NRP). STOP THIS JOB NOW: save what you need from its logs, then delete it (`nrp-task delete JOB` for a task, "
                 "else `kubectl -n %s delete job JOB`). Do not wait for it to finish, do not wait for more data, do not just report. Then work "
                 "out why the GPU sits idle (serial work, CPU phases, data loading, too small a batch) and change the design before any "
                 "resubmit: parallel items per pod, CPU phases in a CPU Job, or a CPU-only request. Never resubmit it unchanged. You have about "
                 "30 minutes: if the Job still runs at the %d-min mark, the monitor deletes it, keeping only the pod log."
                 % (pod, owner or "-", pct_s, _m_state.GPU_WARN_WINDOW_MIN, round(100 * _m_config.gpu_floor()), _m_state.NS, _m_state.GPU_ENFORCE_WINDOW_MIN))
            woke = None
            if tk and _m_wake.wake_target(_m_state.task_load(tk[0]) or {"name": tk[0]}):  # task_txn maps a None result to True, so test the target first
                woke = _m_state.task_txn(tk[0], lambda t, x=text: _m_wake.queue_task_webhook(t, "gpu_warning", summary=x) or False)
            if not woke:                                                  # no chat to wake (not a task, or no wake target): the owner, short
                _m_notify.push("URGENT: GPU pod %s at %s GPU over %d min, under NRP's %d%% floor (strike risk). Stop the Job now and fix the design; "
                     "the monitor deletes it at %d min." % (pod, pct_s, _m_state.GPU_WARN_WINDOW_MIN, round(100 * _m_config.gpu_floor()), _m_state.GPU_ENFORCE_WINDOW_MIN),
                     "gpu-warn:%s" % pod, refs=refs)
            if tk:
                _m_state.task_txn(tk[0], lambda t, l=line: (t.setdefault("util", []).append("%s [gpu-3h warn] %s" % (_m_state.iso(), l[:200])), t["util"].__delitem__(slice(None, -10))))
            continue
        # enforce
        if seen.get(pod, {}).get("deleted"):
            continue
        if a.dry_run:
            print("[dry-run] gpu-long ENFORCE %s %s: would delete Job %s" % (pod, pct_s, owner))
            continue
        why = "GPU %s over the last %d min, under NRP's %d%% floor" % (pct_s, _m_state.GPU_ENFORCE_WINDOW_MIN, round(100 * _m_config.gpu_floor()))
        if tk:
            n, sid = tk
            t = _m_state.task_load(n)
            stg = _m_state.tstage(t, sid)
            try:
                _m_task_pass_.save_task_logs(t, stg, "deleted by the monitor: " + why)
            except Exception as e:  # noqa: BLE001 - logs are best effort; the GPU must be freed regardless
                _m_state.log("gpu-long %s: log save failed: %s" % (pod, str(e)[:120]))
            _m_state.task_txn(n, lambda t: _m_state.tstage(t, sid).update(util_deleted="%s (rule gpu, %d-min window): %s" % (why, _m_state.GPU_ENFORCE_WINDOW_MIN, line[:200])))
        target = ["job", owner] if owner else ["pod", pod]
        rc = _m_cluster.kubectl("-n", _m_state.NS, "delete", *target, "--wait=false").returncode
        seen.setdefault(pod, {})["deleted"] = _m_state.now()
        _m_state.log("gpu-long ENFORCE %s (%s %s) rc=%s: %s" % (pod, target[0], target[1], rc, line[:200]))
        if tk and rc == 0:
            _m_ladder.task_fail(tk[0], tk[1], "util", "util:gpu-3h", "deleted by the monitor for NRP GPU utilization (rule gpu, %d-min window)" % _m_state.GPU_ENFORCE_WINDOW_MIN + ": "
                      + why + ". Do not resubmit unchanged: restructure so the GPU stays busy (parallel levels/items per pod, CPU phases "
                      "in a CPU Job), or move the work to a CPU request.", extra={"rule": "gpu", "pod": pod})
        _m_notify.push("deleted %s %s: %s (%s). %s" % (target[0], target[1], why, pod,
             "Its task stage failed as util/gpu; the fixer must restructure before any resubmit." if tk else "Not a registered task: restructure before resubmitting."),
             "gpu-enforce:%s" % pod, refs=refs)


def record_resize(st, pod, owner, flag_line, verdict):
    """Resize advice goes to resize.log and, when the owner Job is registered, to its resume notes (the follow-up reads them)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    entry = "%s %s (job %s): %s | flag: %s" % (_m_state.iso(), pod, owner or "-", " ".join(verdict.split()), " ".join(flag_line.split()))
    with open(_m_state.RESIZE_LOG, "a") as f:
        f.write(entry + "\n")
    rec = st["jobs"].get(owner or "")
    resume = rec and rec.get("resume")
    if resume and Path(resume).resolve().is_relative_to(_m_state.RESUME_DIR.resolve()):
        try:
            with open(resume, "a") as f:
                f.write("\n\nMONITOR RESIZE NOTE (%s): %s\nReport this resize in your one line; whoever resubmits must use it.\n"
                        % (_m_state.iso(), " ".join(verdict.split())))
        except OSError as e:
            _m_state.log("resize note to %s failed: %s" % (resume, str(e)[:80]))


def check_jobs(a, st):
    from . import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    fake = set(filter(None, (a.fake_finished or "").split(",")))
    for job, rec in sorted(st["jobs"].items()):
        if rec.get("status") != "watching":
            continue
        s = "ok" if job in fake else _m_cluster.job_state(job, rec.get("ns", _m_state.NS))
        if s == "missing" and _m_state.now() - rec.get("added", 0) < _m_state.JOB_GRACE_S:
            continue
        if s not in ("ok", "FAILED", "missing"):
            continue
        status = {"ok": "succeeded", "FAILED": "FAILED", "missing": "no longer in the cluster (deleted or TTL)"}[s]
        resume = rec.get("resume")
        if a.dry_run:
            print("[dry-run] job %s finished (%s); %s" % (job, status, "would launch follow-up agent with %s" % resume
                  if resume else "would notify only (no resume file)"))
            continue
        if resume and not _m_agents.agents_available():                    # no runner has usage left: stay "watching", try next pass
            _m_state.log("job %s finished (%s); follow-up waits: %s" % (job, status, _m_agents.unavailable_text()))
            continue
        rec["status"], rec["handled"], rec["result"] = "handled", _m_state.now(), s       # mark first: exactly once
        _m_state.save(st)
        label = rec.get("label") or job
        if label.lower().startswith("superseded"):
            _m_notify.digest("event", "job %s %s (superseded registration, no follow-up)" % (job, status), "job:" + job)
            continue
        if not resume:
            _m_state.log("job %s finished (%s), no resume file" % (job, status))
            _m_notify.notify("job %s %s" % (label, status), st, None, ref="job:" + job)
            continue
        try:
            text = Path(resume).expanduser().read_text()
            if len(text.encode()) > _m_state.RESUME_MAX:                  # old registrations: never feed an agent a huge LOG.md
                text = text.encode()[:_m_state.RESUME_MAX].decode(errors="ignore") + "\n[... truncated by nrp-monitor: resume file over 20 KB]\n"
        except Exception as e:
            _m_state.log("job %s finished (%s) but resume file unreadable: %s" % (job, status, str(e)[:80]))
            _m_notify.notify("job %s %s; resume file unreadable" % (label, status), st, None, ref="job:" + job)
            continue
        k = "kubectl -n %s" % rec.get("ns", _m_state.NS)
        allowed = _m_agents.kube_read_allow(k) + ["Read(/%s/**)" % (_m_state.WORK / "followup"), "Bash(nrp-util-check:*)",
                   "Bash(nrp-s3-read ls:*)", "Bash(nrp-s3-read cat:*)"]              # read-only S3 helper
        triage_allowed = list(allowed)
        au = rec.get("authorize")
        if au:
            triage_allowed.append("Read(/%s/**)" % str(_m_state.APPROVED).rstrip("/"))
            allowed += _m_agents.auth_allowed(k, au["root"], rec.get("ns", _m_state.NS), au["dir"])
        prompt = _m_agents.job_prompt(job, rec, status, text)
        res = tiered_job_followup(job, rec, prompt, allowed, triage_allowed)
        if _m_agents.is_unavailable(res):                                  # the last runner ran out of usage mid-ladder: nothing was handled
            rec["status"] = "watching"
            rec.pop("handled", None)
            rec.pop("result", None)
            _m_state.save(st)
            _m_state.log("job %s follow-up deferred: %s" % (job, res))
            continue
        # An agent may register the SAME job name. Preserve that new generation;
        # otherwise the pass's stale "handled" record overwrites its retry.
        with _m_state.state_lock():
            disk_rec = _m_state.load()["jobs"].get(job, {})
            if disk_rec.get("added", 0) > rec.get("added", 0):
                st["jobs"][job] = disk_rec
        _m_state.log("followup %s: %s" % (job, res[:300]))
        if followup_solved(res):
            _m_notify.notify("job %s %s: %s" % (label, status, res[:300]), ref="job:" + job)
        else:
            _m_notify.push("NRP monitor (working with %s): job %s needs you: %s" % (_m_state.OWNER_NAME, label, res[:200]),
                 "job:%s:%d" % (job, int(rec["handled"])), refs=["job:" + job])


def followup_solved(result):
    # Fail closed on free-form text, timeouts, and budget/permission errors.
    return bool(re.match(r"^(DONE|RESUBMITTED)\b", result))


def tiered_job_followup(job, rec, prompt, allowed, triage_allowed=None):
    """The follow-up ladder from agents.json (default: one read-only triage, then at most two repairs). No agent waits on jobs."""
    from . import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    policy = ("\nFOLLOW-UP POLICY (takes precedence over older resume instructions):\n"
              "Inspect current state before any action: a prior agent may have partially acted. "
              "Do not duplicate a submission or reset an attempt budget. Never poll or wait. "
              "Respect registered job-attempt caps and stop on repeated identical job failures. "
              "For retries, register with --continue-from BEFORE deleting/applying so refusal cannot "
              "launch an unauthorized attempt. On success, verify the next stage is registered. "
              "Final line must be DONE: <verified result>, RESUBMITTED: <registered job>, "
              "or ESCALATE: <evidence, actions already taken, remaining problem>. "
              "Do not send notifications yourself.\n")
    triage = ("\nYou are the inexpensive READ-ONLY Haiku triage agent. This overrides all authorization "
              "and next-stage instructions above. Only inspect status, logs and outputs. "
              "NEVER register retries, edit files, delete Jobs or submit work. "
              "Use DONE only when every requested step is already complete and verified. "
              "If any mutation or next-stage launch is needed, return ESCALATE with the evidence "
              "and next action. Escalate code bugs or ambiguity promptly.\n")
    ladder = _m_agents.agent_cfg()["followup_ladder"]
    n_repairs = ladder.count("repair")
    history, res, repair_no = [], "no follow-up step ran", 0
    for step in ladder:
        if step == "triage":
            _m_state.log("followup start %s: triage" % job)
            cmd = _m_agents.agent_cmd("triage", triage_allowed if triage_allowed is not None else [])
            cmd.spec["ledger_task"] = job
            res = _m_agents.run_agent(cmd, prompt + policy + triage, _m_state.WORK / "followup")
            _m_notify.digest("followup-triage", res, job)
            history.append("Triage: " + res)
        else:
            repair_no += 1
            au = rec.get("authorize")
            cmd = _m_agents.agent_cmd("repair_auth" if au else "repair", allowed)
            repair = ("\nYou are repair attempt %d/%d. Diagnose and resolve the remaining problem "
                      "within existing approval. Read current registrations and outputs before acting. "
                      "Previous attempts (including partial actions):\n%s\n" %
                      (repair_no, n_repairs, "\n".join(history)))
            _m_state.log("followup repair %s: %d/%d" % (job, repair_no, n_repairs))
            cmd.spec["ledger_task"] = job
            res = _m_agents.run_agent(cmd, prompt + policy + repair, _m_state.WORK / "followup")
            _m_notify.digest("followup-repair", "attempt %d: %s" % (repair_no, res), job)
            history.append("Repair %d: %s" % (repair_no, res))
        if _m_agents.is_unavailable(res) or followup_solved(res):
            return res
    return "STOPPED after %s: %s" % (" and ".join(x for x in ("triage" if "triage" in ladder else "",
                                    "%d repair attempt%s" % (n_repairs, "" if n_repairs == 1 else "s") if n_repairs else "") if x), res)


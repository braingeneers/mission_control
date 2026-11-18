"""NRP monitor continuation (mechanical extraction; R3a)."""
import json


def person_resolution_context(t):
    # Older state already stores resume notes in attempts. New resumes also cover a task with no failure.
    resumes = t.get("resume_notes", [])
    first = min((x["ts"] for x in resumes), default=float("inf"))
    entries = [(x.get("ts", 0), x.get("fix", "")) for x in t.get("attempts", [])
               if x.get("by") == "person" and x.get("ts", 0) < first]
    entries += [(x["ts"], x["note"]) for x in resumes]
    notes = [note for _, note in sorted(entries, key=lambda x: x[0]) if note]
    if not notes:
        return ""
    return ("\nLatest person/coordinator resume and skip notes (chronological; newest wins):\n"
            + "\n".join(notes) + "\nThese notes supersede the original brief's artifact locations. "
            "Verify and report the replacement run/artifacts they name.\n")


def continue_prompt(t, h, go, held):
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    od = t["on_done"]
    d = _m_plans.plan_dir(od["plan"])
    tpl = (_m_state.TPL / "continue_agent.md").read_text()
    rep = {"name": t["name"], "plan": od["plan"], "step": od["from_step"], "goal": t["goal"], "origin": _m_wake.origin_plain(t.get("origin")),
           "approval": h["approval"], "approved_through": h["approved_through"], "stops": ", ".join(h["stops"]) or "none",
           "may_touch": ", ".join(h["may_touch"]) or "(not set: only the outputs this plan names)",
           "go": ", ".join(go) or "NONE (do not register anything)",
           "held": "\n".join("  - step %s: %s" % x for x in held) or "  (none)",
           "plan_file": str(d / "plan.md"), "files": str(d / "files"), "work": str(d / "work"), "dir": str(_m_state.task_dir(t["name"])),
           "stages": "\n".join("  - %s job=%s outputs=%s" % (s["id"], s["job"], ", ".join(s["done_s3"])) for s in t["stages"]),
           "notes": t.get("notes") or "(none)", "clone": (t.get("code") or {}).get("clone", "(no code clone)")}
    for k, v in rep.items():
        tpl = tpl.replace("{%s}" % k, v)
    return (tpl.replace("{handoff}", _m_wake.handoff_prompt(t)) + _m_decisions.failure_context(t) + person_resolution_context(t)
            + "\nSave a separate result note for this task: " + str(d / "work" / ("step-" + od["from_step"] + "-" + t["name"] + "-result.md"))
            + "\nFollowup (do this in this same agent): " + t.get("followup", "")
            + "\nPostcheck: " + json.dumps(t.get("postcheck_result"))
            + "\nStage outputs: " + json.dumps({s["id"]: s.get("outputs", {}) for s in t["stages"]})
            + "\nScoped helpers: nrp-task postcheck (rerun the exact declared read-only checker). Read saved logs and notes in the task directory.")


def close_continuation(n, status, line):
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plan_wakes as _m_plan_wakes  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = _m_state.task_load(n)
    od = t["on_done"]
    reg = (t.get("continuation") or {}).get("registered") or []
    if status == "CONTINUED" and not reg:
        status, line = "WAITING", "agent said CONTINUED but registered no task: " + line
    _m_state.task_txn(n, lambda t: t["continuation"].update(state="closed", status=status, line=line[:400], closed=_m_state.now()))
    if _m_plans.plan_state(od["plan"])["status"] == "closed":
        _m_plans.plan_txn(od["plan"], lambda st: _m_plans.pev(st, "closed plan: task %s continuation returned %s: %s" % (n, status, line)))
        return
    msg = "step %s (task %s): %s %s" % (od["from_step"], n, status, line[:300])
    if status == "CONTINUED":
        _m_plans.plan_set(od["plan"], "running", msg)
        _m_notify.digest("plan-continued", "plan %s %s -> started %s" % (od["plan"], msg, ", ".join(reg)), n)
    elif status == "WAITING":
        _m_plans.plan_set(od["plan"], "waiting", msg, reason=line[:400])
        _m_notify.digest("plan-wait", "plan %s %s" % (od["plan"], msg), n)
    else:                                                               # NOT-DONE, STOPPED, FAILED
        _m_plans.plan_set(od["plan"], "waiting", msg, reason="%s: %s" % (status, line[:380]))
        _m_notify.digest("plan-stop", "plan %s %s" % (od["plan"], msg), n)
    if status in ("NOT-DONE", "STOPPED", "FAILED"):
        def reason_wake(cur):
            summary = "Continuation %s: %s" % (status, line)
            found = False
            for owner in [cur] + _m_plan_wakes.step_siblings(cur, include_cancelled=True):
                queued = [event for event in owner.get("webhook_outbox", []) if event.get("event_type") == "done"]
                for event in queued:
                    event["summary"] = summary
                    found = True
                if queued and owner["name"] != cur["name"]:
                    _m_state.task_write(owner)  # already inside the global task transaction lock
            if not found:
                _m_wake.queue_task_webhook(cur, "done", summary=summary)
        _m_state.task_txn(n, reason_wake)
    else:
        h = _m_plans.plan_header(od["plan"]) or {}
        _, held = _m_plans.next_steps(h, od["from_step"])
        if any(step in h.get("stops", []) for step, _ in held):
            def stop_wake(cur):
                siblings = _m_plan_wakes.step_siblings(cur, include_cancelled=True)
                if any(other["status"] != "done" or (other.get("continuation") or {}).get("state") != "closed" for other in siblings):
                    return
                registered = max(other.get("created", 0) for other in [cur] + siblings)
                wake_times = {r.get("event_id"): r["ts"] for r in _m_decisions.cost_rows() if r["kind"] == "coordinator_wake"}
                if any(other.get("stop_event_id") and wake_times.get(other["stop_event_id"], 0) >= registered
                       for other in [cur] + siblings):
                    return
                group = _m_plan_wakes.task_group(cur, h)
                if _m_plan_wakes.completion_policy(cur) == "group" and _m_plan_wakes.group_ready(h, group, _m_plan_wakes.group_members(od["plan"], group, h)):
                    return  # the group summary carries this planned stop in the same pass
                summary = "Planned stop reached: " + msg
                queued = [(owner, event) for owner in [cur] + siblings for event in owner.get("webhook_outbox", [])
                          if event.get("event_type") == "done"]
                if queued:
                    owner, event = queued[-1]
                    event["summary"] = summary
                    cur["stop_event_id"] = event["event_id"]
                    if owner["name"] != cur["name"]:
                        _m_state.task_write(owner)
                else:
                    event = _m_wake.queue_task_webhook(cur, "done", summary=summary)
                    if event:
                        cur["stop_event_id"] = event
            _m_state.task_txn(n, stop_wake)
    extra = ""
    with open(_m_plans.plan_dir(od["plan"]) / "results.md", "a") as f:
        f.write("- %s step %s, task %s: %s %s%s\n" % (_m_state.iso(), od["from_step"], n, status, line, extra))


def continue_task(n, a):
    from . import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plan_wakes as _m_plan_wakes  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import task_agents as _m_task_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = _m_state.task_load(n)
    od = t["on_done"]
    if _m_plans.plan_state(od["plan"])["status"] == "closed":
        if not a.dry_run:
            _m_plan_wakes.skip_closed_continuation(n)
        return
    h = _m_plans.plan_header(od["plan"])
    if not h:
        _m_state.task_txn(n, lambda t: t.update(continuation={"state": "closed", "status": "FAILED", "line": "no plan snapshot", "closed": _m_state.now()}))
        _m_notify.digest("plan-stop", "task %s finished but plan %s has no snapshot" % (n, od["plan"]), n)
        return
    go, held = _m_plans.next_steps(h, od["from_step"])
    if a.dry_run:
        print("[dry-run] plan %s: task %s (step %s) done; auto-continue %s; may start %s; held %s"
              % (od["plan"], n, od["from_step"], "on" if _m_plans.on_done_enabled() else "OFF", go or "nothing", held or "nothing"))
        return
    if not _m_plans.on_done_enabled():
        _m_state.task_txn(n, lambda t: t.update(continuation={"state": "closed", "status": "OFF", "closed": _m_state.now()}))
        why = "auto-continue is off; with it on, an agent would check 'done when' for step %s and %s" % (
            od["from_step"], ("start step(s) %s" % ", ".join(go)) if go else "start nothing")
        _m_plans.plan_set(od["plan"], "waiting", "step %s (task %s) done; %s" % (od["from_step"], n, why), reason=why)
        _m_notify.digest("plan-off", "plan %s: step %s done (task %s); %s" % (od["plan"], od["from_step"], n, why), n)
        return

    if not _m_agents.agents_available():                                          # stays unclaimed; the next pass tries again
        _m_state.log("plan %s: continue agent for task %s waits: %s" % (od["plan"], n, _m_agents.unavailable_text()))
        return

    def claim(t):
        if t.get("continuation") or _m_plans.plan_state(od["plan"])["status"] == "closed":
            return False
        t["continuation"] = {"state": "running", "started": _m_state.now(), "go": go, "registered": []}
    if not _m_state.task_txn(n, claim):
        return
    _m_state.PASS["continued"] = _m_state.PASS.get("continued", 0) + 1
    _m_state.log("plan %s: continue agent for task %s (step %s; may start %s; held %s)" % (od["plan"], n, od["from_step"], go, held))
    line, den = _m_task_agents.run_task_agent(n, continue_prompt(t, h, go, held), a, kind="continue")
    if _m_agents.is_unavailable(line):                                            # ran out of usage mid-call: release the claim, retry next pass
        _m_state.task_txn(n, lambda t: t.pop("continuation", None))
        return
    rep = _m_state.task_load(n).get("report") or {}
    status = rep.get("status") if rep.get("status") in ("CONTINUED", "WAITING", "NOT-DONE", "STOPPED") else "FAILED"
    if status == "FAILED" and den:
        line = "the continue agent was denied %d tool call(s) (monitor fault): %s" % (len(den), line)
    close_continuation(n, status, rep.get("line") or line)


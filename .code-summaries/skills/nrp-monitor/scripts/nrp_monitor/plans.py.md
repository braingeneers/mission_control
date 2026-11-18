# plans.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.plans`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Core data structures, parser, and state manager for multi-step plan run blocks (run blocks), evaluating approval bounds, next-step dependencies, and step task registration. Imported by continuation, plan_commands, plan_wakes, ladder, nrp_task; not run as a CLI directly.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.continuation` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.notify` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.plan_commands` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.plan_wakes` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.registry` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_agents` — import consumer hint; not a proven runtime call.
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imports state, notify, task.registry, wake.
- **Shared data:** Reads and writes files in <state>/plans/<id>/.

## Dependencies
None

## Classes
None

## Functions
### `on_done_enabled()`
> Checks whether the global auto-continuation feature flag exists.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:9`
### `plan_dir(pid)`
> Returns filesystem path to state directory for a specific plan ID.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:146 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:155 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:168 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:169 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:224 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:344 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:346 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:347 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:362 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:363 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:365 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:366 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:14`
### `split_list(v)`
> Helper parsing comma-delimited or bracketed string lists into clean string arrays.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:65 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:67 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:68 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:90 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:19`
### `plan_section(text, pid)`
> Extracts the markdown section tagged with plan ID comment from a document.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:209 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:26`
### `parse_run_block(section)`
> Parses and validates key-value configuration from a markdown run code block.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:212 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:49`
### `step_pos(h, s)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:141 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:254 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:260 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:307 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:136`
### `approved_pos(h)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:260 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:307 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:140`
### `plan_header(pid)`
> Reads cached plan header dictionary from header.json.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:300 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:330 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:354 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:144`
### `plan_state(pid)`
> Reads or initializes plan execution state dictionary from state.json.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:166 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:250 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:303 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:314 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:153`
### `plan_txn(pid, fn)`
> Executes state modification callback within global state lock and persists state.json.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:187 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:194 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:242 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:162`
### `pev(st, msg)`
> Appends timestamped event string to plan recent events circular buffer.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:182 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:186 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:196 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:235 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:239 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:242 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:172`
### `plan_set(pid, status, msg, reason=None)`
> Updates plan lifecycle status and reason with event logging.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:178`
### `ledger_add(pid, step, task, by, parent)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:191`
### `plan_sync(path, pid, reopen=False)`
> Copy plan `pid` from `path` into plans/<pid>/ (session side: launchd cannot read ~/Desktop). Returns the header.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:297 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:200`
### `next_steps(h, from_step, ledger=None, parent=None)`
> Calculates which subsequent plan steps are eligible to run immediately versus held for approval/stops.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:356 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:246`
### `resolve_plan_path(path, raw, src_file)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:297 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:269`
### `check_on_done(od, raw, src_file, by, parent)`
> Validates a task on_done plan specification against plan header approval and bounds.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:288`
### `plan_gpu_cover(od)`
> Determines whether a plan dated owner approval covers GPU resource usage for a task stage.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:325`
### `tool_next_add(n, t, rest)`
> Implements nrp-task next-add: validates and registers next plan task from a continue agent.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:335`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Flag <state>/on_done.enabled: enables or disables auto-continuation feature. |
| Plan run block keys: plan, approval, steps, approved_through, stop_for_owner, may_touch, next, templates, groups, wake, retries, fallback, fallback_hours. |

## Data Shapes
- Plan header dict (header.json): {plan: str, approval: str, steps: [str], approved_through: str, stops: [str], may_touch: [str], templates: [str], next: {step: [step]}, groups: {group: [step]}, wake: str, ...}.
- Plan state dict (state.json): {status: str, since: float, reason: str, ledger: {step: [{task: str, by: str, t: float}]}, events: [str], ...}.

## Notes
- Parses run blocks out of markdown plan files using regex, verifying syntax, step existence, and topological consistency.
- Enforces that tasks can only advance to steps within the owner approved_through boundary and outside stop_for_owner stops.
- Tracks multi-task fan-outs per step in ledger, allowing sessions to add tasks while preventing unauthorized double runs.
- Isolates plan template files into <state>/plans/<id>/files/ so launchd agents do not access Desktop paths.

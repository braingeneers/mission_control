# plans.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.plans`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Parses and validates approved plan run blocks, snapshots plan text/templates, tracks ledger and step bounds, and gates continuation registration. plan_txn delegates locked load/modify/write to state.json_txn while retaining defaults and its historical callback return behavior.

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
- **Shared data:** **Shared data:** Imports state, notify, task.registry, wake.
- **Shared data:** **Shared data:** Reads and writes files in <state>/plans/<id>/.

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
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:146 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:155 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:168 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:169 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:225 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:345 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:347 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:348 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:363 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:364 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:366 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:367 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:14`
### `split_list(v)`
> Helper parsing comma-delimited or bracketed string lists into clean string arrays.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:65 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:67 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:68 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:90 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:19`
### `plan_section(text, pid)`
> The part of a plan file that belongs to plan `pid`: the heading carrying `<!-- plan:pid -->` down to the next heading of the same or higher level (code fences skipped). A file whose only run block names pid is used whole.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:210 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:26`
### `parse_run_block(section)`
> The machine-read run header: a ```run fenced block of `key: value` lines (# starts a comment).
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:213 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:49`
### `step_pos(h, s)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:141 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:255 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:261 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:308 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:136`
### `approved_pos(h)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:261 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:308 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:140`
### `plan_header(pid)`
> Reads cached plan header dictionary from header.json.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:301 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:331 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:355 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:144`
### `plan_state(pid)`
> Reads or initializes plan execution state dictionary from state.json.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:170 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:251 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:304 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:315 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:153`
### `plan_txn(pid, fn)`
> Executes state modification callback within global state lock and persists state.json.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:188 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:195 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:243 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:162`
### `pev(st, msg)`
> Appends timestamped event string to plan recent events circular buffer.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:183 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:187 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:197 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:236 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:240 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plans.py:243 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:173`
### `plan_set(pid, status, msg, reason=None)`
> Updates plan lifecycle status and reason with event logging.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:179`
### `ledger_add(pid, step, task, by, parent)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:192`
### `plan_sync(path, pid, reopen=False)`
> Copy plan `pid` from `path` into plans/<pid>/ (session side: launchd cannot read ~/Desktop). Returns the header.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:298 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:201`
### `next_steps(h, from_step, ledger=None, parent=None)`
> (go, held): steps after `from_step` the continue agent may start, and [(step, why)] for those it may not. `parent` = the task whose continue agent is registering: tasks it already registered for a step do not hold that step, so one step can have several tasks (per-cell fan-outs); a step started by anyone else is still held.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:357 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:247`
### `resolve_plan_path(path, raw, src_file)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plans.py:298 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:270`
### `check_on_done(od, raw, src_file, by, parent)`
> Validates a task on_done plan specification against plan header approval and bounds.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:289`
### `plan_gpu_cover(od)`
> Why a GPU stage of this plan task needs no gpu_ok_until: the plan's approval (with its date) covers GPU stages of its approved steps (owner decision 2026-11-06). None when the task is not a plan step or the approval line has no ISO date.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:326`
### `tool_next_add(n, t, rest)`
> `nrp-task next-add FILE`: the continue agent registers the next plan step. Every gate is checked here, not trusted to the prompt.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plans.py:336`

## Config / CLI
None

## Data Shapes
- Plan header dict (header.json): {plan: str, approval: str, steps: [str], approved_through: str, stops: [str], may_touch: [str], templates: [str], next: {step: [step]}, groups: {group: [step]}, wake: str, ...}.
- Plan state dict (state.json): {status: str, since: float, reason: str, ledger: {step: [{task: str, by: str, t: float}]}, events: [str], ...}.

## Notes
- Parses run blocks out of markdown plan files using regex, verifying syntax, step existence, and topological consistency.
- Enforces that tasks can only advance to steps within the owner approved_through boundary and outside stop_for_owner stops.
- Tracks multi-task fan-outs per step in ledger, allowing sessions to add tasks while preventing unauthorized double runs.
- Isolates plan template files into <state>/plans/<id>/files/ so launchd agents do not access Desktop paths.

# task_commands.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.task_commands`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Implements CLI command handlers for querying, controlling, and updating NRP tasks (task list, watch, code, stage, show, resume, needs-owner, handoff, cancel, origin, and util restart). Invoked via nrp-monitor subcommands by human operators or agent coordinators.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli_args` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Uses:** `config` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `ladder` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `nrp_task` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plan_commands` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `stage_jobs` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `model` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `tier0` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `util` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** **Shared data:** Invoked by CLI command router in `nrp_monitor.cli`.
- **Shared data:** **Shared data:** Uses `nrp_monitor.state` for persistence, `nrp_monitor.wake` for origin and handoff management, `nrp_monitor.tier0` for node exclusion, `nrp_monitor.util` for utilization restart, `nrp_monitor.decisions` for fingerprinting and recording decisions, and `nrp_monitor.ladder` for owner escalation.
- **Shared data:** Stage submission, resource snapshots/propagation or saved task diagnostics now resolve through stage_jobs; see call sites for the applicable operation.

## Dependencies
None

## Classes
None

## Functions
### `cmd_task_list(a)`
> Prints tabular summary of all known tasks with status, stage states, retry counts, reason, and origin chat title.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:22`
### `cmd_task_watch(a)`
> Set one task to watch mode only when no monitor pass is running.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:34`
### `cmd_task_code(a)`
> `task code NAME [--pkg-dir D] [--extra-pkg-dir D ...] [--replace]`: declare the code dirs `nrp-task reship` packs for a task registered without them (for example finetune/ from another repo). Relative = inside the task's clone (added to its sparse checkout), absolute = another checkout.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:50`
### `cmd_task_stage(a)`
> `task stage NAME STAGE --resumable`: mark a stage of an already registered task as resumable (re-running it skips finished items), so Tier 0 may resubmit it once with 2x deadline after a timeout. Same effect as `resumable: true` in TASK.json at `task add`.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:83`
### `cmd_task_show(a)`
> Prints comprehensive diagnostic status report of a task including stages, failures, agent runs, handoff status, and decisions.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:115`
### `cmd_task_resume(a)`
> After the owner decides: clear NEEDS_OWNER; the failed stage is resubmitted next pass (or --skip it), budgets restart.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:170`
### `cmd_task_needs_owner(a)`
> `task needs-owner NAME --reason TEXT`: what the task's coordinator chat runs when the owner is truly needed. Sets NEEDS_OWNER and sends the one DM (the same path as every other stop). Nothing else tells the owner about a task that is WITH_COORDINATOR.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:218`
### `cmd_task_handoff(a)`
> `task handoff NAME FILE`: attach the handoff to a task registered without one (the registering agent writes it after the monitor is started). Same checks as the `handoff` field of `task add`; a missing or empty file is an error here. The Registrar is written once: a task that has a handoff keeps it.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:238`
### `cmd_task_cancel(a)`
> Cancels a task using the state transition machine without deleting task artifacts.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:271`
### `cmd_origin(a)`
> Metadata-only: record (or show) which chat owns a task/chain/legacy job. Same locks as the runner; no state, approval, submission or ownership changes. Refuses to overwrite an existing origin without --replace; --evidence is required.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:279`
### `cmd_util_restart(a)`
> Restarts a stage job with new CPU/memory requests via `utilization_restart` without consuming retry budgets.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:343`

## Config / CLI
None

## Data Shapes
- Task dictionary: mapping containing `name` (str), `status` (str), `mode` (str), `namespace` (str), `stages` (list of dicts), `attempts` (list of dicts), `origin` (dict), `handoff` (dict), etc.

## Notes
- Acquires non-blocking flock on `_m_state.LOCK` in `cmd_task_watch` and `cmd_util_restart` to prevent races with active monitor passes.
- Performs task state mutations atomically using `_m_state.task_txn(name, mutator)`.
- Uses lazy local imports (`_m_task_model`, `_m_nrp_task`) to break cyclic import dependencies.

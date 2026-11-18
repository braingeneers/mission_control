# task_commands.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.task_commands`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Implements CLI command handlers for querying, controlling, and updating NRP tasks (task list, watch, code, stage, show, resume, needs-owner, handoff, cancel, origin, and util restart). Invoked via nrp-monitor subcommands by human operators or agent coordinators.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Uses:** `config` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `ladder` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `nrp_task` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plan_commands` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `model` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `tier0` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `util` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Invoked by CLI command router in `nrp_monitor.cli`.
- **Shared data:** Uses `nrp_monitor.state` for persistence, `nrp_monitor.wake` for origin and handoff management, `nrp_monitor.tier0` for node exclusion, `nrp_monitor.util` for utilization restart, `nrp_monitor.decisions` for fingerprinting and recording decisions, and `nrp_monitor.ladder` for owner escalation.

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
> Sets task execution mode to 'watch' under state lock, disabling automatic fixer agent retries.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:34`
### `cmd_task_code(a)`
> Configures and verifies code packaging directories (`pkg_dir` and `extra_pkg_dirs`) for task code reshipment.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:50`
### `cmd_task_stage(a)`
> Marks a task stage as resumable and/or appends excluded nodes to the stage manifest node affinity.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:83`
### `cmd_task_show(a)`
> Prints comprehensive diagnostic status report of a task including stages, failures, agent runs, handoff status, and decisions.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:115`
### `cmd_task_resume(a)`
> Resumes a task from NEEDS_OWNER, WITH_COORDINATOR, or blocked status; clears queue holds and marks failed stages for resubmission or skipping.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:170`
### `cmd_task_needs_owner(a)`
> Transitions task to NEEDS_OWNER status with required reason, triggering a single direct Slack message to the task owner.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:218`
### `cmd_task_handoff(a)`
> Attaches a handoff markdown file to a registered task lacking one, enforcing Registrar heading rules.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:238`
### `cmd_task_cancel(a)`
> Cancels a task using the state transition machine without deleting task artifacts.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:271`
### `cmd_origin(a)`
> Displays or updates owning chat metadata for a task or job, recording evidence and audit history.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:279`
### `cmd_util_restart(a)`
> Restarts a stage job with new CPU/memory requests via `utilization_restart` without consuming retry budgets.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_commands.py:343`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env `NRP_MONITOR_REQUIRE_HANDOFF`: if set, refuses `cmd_task_handoff` if the handoff document is thin. |
| Env `CLAUDE_CODE_SESSION_ID`: fallback identifier for `by` attribute in `cmd_origin`. |
| Env `CODEX_THREAD_ID`: fallback identifier for `by` attribute in `cmd_origin`. |
| CLI flags `--pkg-dir`, `--extra-pkg-dir`, `--replace`: configure code directories in `cmd_task_code`. |
| CLI flags `--resumable`, `--exclude-node`: mark stages resumable or exclude faulty nodes in `cmd_task_stage`. |
| CLI flags `--skip`, `--decide`, `--note`, `--retries`, `--gpu-ok-until`: resume options in `cmd_task_resume`. |
| CLI flag `--reason`: mandatory justification in `cmd_task_needs_owner`. |
| CLI flags `--evidence`, `--chat`, `--harness`, `--link`, `--title`, `--assistant`, `--collaborator`, `--note`, `--replace`: specify origin chat metadata in `cmd_origin`. |
| CLI flags `--cpu`, `--mem`: resource overrides in `cmd_util_restart`. |

## Data Shapes
- Task dictionary: mapping containing `name` (str), `status` (str), `mode` (str), `namespace` (str), `stages` (list of dicts), `attempts` (list of dicts), `origin` (dict), `handoff` (dict), etc.

## Notes
- Acquires non-blocking flock on `_m_state.LOCK` in `cmd_task_watch` and `cmd_util_restart` to prevent races with active monitor passes.
- Performs task state mutations atomically using `_m_state.task_txn(name, mutator)`.
- Uses lazy local imports (`_m_task_model`, `_m_nrp_task`) to break cyclic import dependencies.

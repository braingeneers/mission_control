# cli.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.cli`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Monitor entry point and handlers for the pass, legacy Job registration, status and logs. main builds the parser from cli_args and dispatches its selected handler; no parser definitions live here.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli_args` — import consumer hint; not a proven runtime call.
- **Uses:** `agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `cli_args` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `legacy` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plan_wakes` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `red_alert` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `s3` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `pass_` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `util` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** **Shared data:** Imports nearly all nrp_monitor submodules: agents, cluster, decisions, legacy, notify, nrp_task, plan_commands, plan_wakes, red_alert, s3, setup, state, task_commands, util, wake.
- **Shared data:** **Shared data:** Invokes run_pass orchestrating S3 prepass, red alert checks, task processing, plan continuations, and legacy pod/job checks.

## Dependencies
None

## Classes
None

## Functions
### `cmd_status(a)`
> Checks and displays monitor heartbeat freshness, active tasks/jobs, coordinator waits, and runner quota state.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:22`
### `save_merged(st)`
> Save jobs.json, keeping registrations that `add` wrote while this (possibly long) pass ran.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli.py:109 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:55`
### `cmd_run(a)`
> Runs a single monitor pass with snapshot caching and guarantees cleanup of S3 pass cache.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:66`
### `cmd_run_pass(a)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli.py:68 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:73`
### `run_pass(a)`
> Executes the pass pipeline under lock: S3 prepass, red alert, tasks, continuations, webhooks, and legacy checks.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli.py:75 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:78`
### `cmd_add(a)`
> Registers a legacy Kubernetes Job to watch, supporting auto-resume notes and authorized repair delegation.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:118`
### `snapshot_code(src, adir)`
> Copy a code folder (no data/weights/git) to approved/<task>/code and code.orig, so a launchd agent (which cannot read Desktop) can fix and rebuild a ConfigMap; the diff is kept in PATCH.diff for a person to merge. Refuses > 30 MB.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli.py:169 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:181`
### `cmd_list(a)`
> Displays all registered legacy jobs and their current status.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:202`
### `cmd_log(a)`
> Prints the last N lines of the monitor log.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:212`
### `main()`
> Configures argparse subparsers and dispatches CLI commands.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:218`

## Config / CLI
None

## Data Shapes
- CLI argument namespace parsed by argparse.ArgumentParser.
- Registration record in jobs.json: {'added': float, 'ns': str, 'label': str, 'resume': str?, 'status': 'watching'|'handled', 'origin': dict?, 'authorize': dict?}.
- Code snapshot: Directory tree under approved/<task>/code capped at 30 MB (CODE_SNAPSHOT_MAX).

## Notes
- Acquires non-blocking file lock on <state>/monitor.lock to ensure only one monitor pass runs at a time.
- Writes periodic heartbeats to <state>/heartbeat via _m_state.write_heartbeat.
- Snapshots code directories for authorized jobs into approved/<task>/code to isolate from local Desktop file changes.

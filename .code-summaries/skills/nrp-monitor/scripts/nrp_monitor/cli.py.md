# cli.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.cli`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Main entry point and CLI command dispatcher for nrp-monitor, providing commands for monitor loop execution (run), task/plan management, legacy job registration, status checks, and setup. Run via CLI nrp-monitor <command> or cron/launchd daemon.

## Connections
- **Uses:** `agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `legacy` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `nrp_task` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plan_commands` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plan_wakes` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `red_alert` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `s3` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `setup` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `pass_` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `task_commands` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `util` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imports nearly all nrp_monitor submodules: agents, cluster, decisions, legacy, notify, nrp_task, plan_commands, plan_wakes, red_alert, s3, setup, state, task_commands, util, wake.
- **Shared data:** Invokes run_pass orchestrating S3 prepass, red alert checks, task processing, plan continuations, and legacy pod/job checks.

## Dependencies
None

## Classes
None

## Functions
### `cmd_status(a)`
> Checks and displays monitor heartbeat freshness, active tasks/jobs, coordinator waits, and runner quota state.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:29`
### `save_merged(st)`
> Save jobs.json, keeping registrations that `add` wrote while this (possibly long) pass ran.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli.py:116 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:62`
### `cmd_run(a)`
> Runs a single monitor pass with snapshot caching and guarantees cleanup of S3 pass cache.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:73`
### `cmd_run_pass(a)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli.py:75 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:80`
### `run_pass(a)`
> Executes the pass pipeline under lock: S3 prepass, red alert, tasks, continuations, webhooks, and legacy checks.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli.py:82 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:85`
### `cmd_add(a)`
> Registers a legacy Kubernetes Job to watch, supporting auto-resume notes and authorized repair delegation.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:125`
### `snapshot_code(src, adir)`
> Copies user code directory to task approved folder excluding large artifacts and git directories.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli.py:176 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:188`
### `cmd_list(a)`
> Displays all registered legacy jobs and their current status.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:209`
### `cmd_log(a)`
> Prints the last N lines of the monitor log.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:219`
### `main()`
> Configures argparse subparsers and dispatches CLI commands.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:225`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| CLI flags: run (--dry-run, --fake-util, --fake-finished, --tasks-only), status (--quiet), add (--resume, --label, -n, --authorize, --max-attempts, --manifest, --code-dir, --continue-from), digest (--hours). |
| Env NRP_MONITOR_NS: Kubernetes namespace (defaults to state.NS). |

## Data Shapes
- CLI argument namespace parsed by argparse.ArgumentParser.
- Registration record in jobs.json: {'added': float, 'ns': str, 'label': str, 'resume': str?, 'status': 'watching'|'handled', 'origin': dict?, 'authorize': dict?}.
- Code snapshot: Directory tree under approved/<task>/code capped at 30 MB (CODE_SNAPSHOT_MAX).

## Notes
- Acquires non-blocking file lock on <state>/monitor.lock to ensure only one monitor pass runs at a time.
- Writes periodic heartbeats to <state>/heartbeat via _m_state.write_heartbeat.
- Snapshots code directories for authorized jobs into approved/<task>/code to isolate from local Desktop file changes.

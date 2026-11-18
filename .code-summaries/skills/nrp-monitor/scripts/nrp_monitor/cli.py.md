# cli.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.cli`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Main CLI command handlers and pass execution controller for nrp-monitor. Coordinates single monitor passes (run), status reporting (status), legacy job watching (add, list), and log inspection (log). In cmd_run, conditionally activates the shadow.isolated_pass context manager when --shadow is specified. Executed via CLI (main) or imported by package modules.

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
- **Uses:** `isolated_pass` from `skills.nrp-monitor.scripts.nrp_monitor.shadow` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `pass_` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `util` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imports agents, cluster, legacy, notify, plan_wakes, red_alert, s3, state, task.pass_, util, wake, and cli_args.
- **Shared data:** Conditionally imports `isolated_pass` from `.shadow` when `a.shadow` is true.

## Dependencies
None

## Classes
None

## Functions
### `cmd_status(a)`
> Checks and displays monitor heartbeat freshness, active tasks, running stage Jobs, legacy jobs, owner-needed tasks, coordinator waits, and runner quota state.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:22`
### `save_merged(st)`
> Save jobs.json, keeping registrations that add wrote while this (possibly long) pass ran.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli.py:113 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:55`
### `cmd_run(a)`
> Runs a single monitor pass, entering shadow.isolated_pass if a.shadow is set, and guarantees cleanup of S3 pass cache.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:66`
### `cmd_run_pass(a)`
> Wraps run_pass within cluster.pass_snapshot context so each namespace's Jobs and pods are queried once per pass.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli.py:71 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/cli.py:72 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:77`
### `run_pass(a)`
> Executes the monitor pass pipeline under file lock: S3 prepass, red alert, tasks, continuations, webhooks, and legacy checks.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli.py:79 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:82`
### `cmd_add(a)`
> Registers a legacy Kubernetes Job to watch, supporting auto-resume notes and authorized repair delegation.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:122`
### `snapshot_code(src, adir)`
> Copy a code folder (no data/weights/git) to approved/<task>/code and code.orig, so a launchd agent (which cannot read Desktop) can fix and rebuild a ConfigMap; the diff is kept in PATCH.diff for a person to merge. Refuses > 30 MB.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli.py:173 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:185`
### `cmd_list(a)`
> Displays all registered legacy jobs and their current status from jobs.json.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:206`
### `cmd_log(a)`
> Prints the last N lines of the monitor log.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:216`
### `main()`
> Configures argparse subparsers via cli_args.monitor_parser and dispatches CLI commands.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli.py:222`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| CLI flags: `--shadow`, `--dry-run`, `--tasks-only`, `--quiet`, `-n`. |
| Lock file `<state>/monitor.lock` (LOCK). |
| Constants `RESUME_MAX` (256 KB) and `CODE_SNAPSHOT_MAX` (30 MB). |

## Data Shapes
- Registration record in `jobs.json`: `{'added': float, 'ns': str, 'label': str, 'resume': str, 'status': str, 'origin': dict, 'authorize': dict}`.
- Heartbeat status string written to `<state>/heartbeat` via `_m_state.write_heartbeat`.

## Notes
- Acquires non-blocking file lock on `<state>/monitor.lock` via `fcntl.flock` to ensure only one monitor pass runs at a time.
- Executes pass pipeline under `pass_snapshot`: S3 prepass, admission red alert check, task processing, plan continuations, task webhooks, legacy pod/job checks, and orphan cleanup.
- Guarantees `_m_state.S3_PASS` cache is cleared in `cmd_run` finally block.
- Conditionally enters `shadow.isolated_pass()` context manager when `--shadow` flag is active.

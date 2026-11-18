# cli_args.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/cli_args.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.cli_args`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Argparse definition and command dispatch configuration module for nrp-monitor and nrp-task. Builds the complete command tree for run, costs, wake-review, decide, task, plan, tool, digest, add, list, origin, log, status, setup, and agents. Imported by cli.py and nrp_task.py.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Uses:** `cli` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `nrp_task` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plan_commands` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `setup` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `task_commands` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imports handlers from cli, decisions, nrp_task, notify, plan_commands, setup, state, task_commands, wake, and task.registry.

## Dependencies
None

## Classes
None

## Functions
### `monitor_parser()`
> Constructs the root argparse.ArgumentParser and all subparsers for the nrp-monitor CLI suite.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:5`
### `origin_edit_args(o)`
> Configures shared origin tracking flags (--chat, --link, --harness, --session, --evidence, etc.) on a parser.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:129 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:134 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:164`
### `resource_args(parser, quantities=True)`
> Adds --stage, --cpu, --mem options to resource management subparsers.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:197 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:46 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:180`
### `tool_parser(command)`
> Scoped nrp-task options; manual commands retain their existing positional syntax.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:187`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| CLI commands and flags for nrp-monitor: `run` (--shadow, --dry-run, --fake-util, --fake-finished, --tasks-only), `costs`, `wake-review`, `decide`, `task` (add, list, show, resize, restart, watch, code, stage, resume, needs-owner, handoff, cancel), `plan` (sync, close, needs-owner, resume, list, show), `tool`, `digest`, `add`, `list`, `origin`, `log`, `status`, `setup`, `agents`. |

## Data Shapes
- Returns configured `argparse.ArgumentParser` instances populated with subcommands, defaults, and option flags.

## Notes
- Defers submodule imports inside parser factory functions to avoid circular import issues during startup.

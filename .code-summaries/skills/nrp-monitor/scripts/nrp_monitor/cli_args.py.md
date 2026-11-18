# cli_args.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/cli_args.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.cli_args`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Owns argparse registration for nrp-monitor and the scoped nrp-task option parsers. monitor_parser binds handlers with set_defaults; origin_edit_args and resource_args share repeated options. Tool command authorization and positional dispatch remain in nrp_task.

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
- **Shared data:** cli.main calls monitor_parser; nrp_task.cmd_tool calls tool_parser.
- **Shared data:** Handlers remain in cli, task_commands, plan_commands, decisions, notify, setup and task.registry.

## Dependencies
None

## Classes
None

## Functions
### `monitor_parser()`
> Build monitor command tree with handlers and existing defaults.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:5`
### `origin_edit_args(o)`
> Register shared origin editing options for task and general origin commands.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:128 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:133 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:163`
### `resource_args(parser, quantities=True)`
> Register stage selection and, when enabled, CPU/memory quantities.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:196 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:45 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:179`
### `tool_parser(command)`
> Build the scoped decide or resource parser without changing tool authorization.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cli_args.py:186`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Registers existing monitor commands and defaults, including task, plan, origin, tool, setup and agents. |
| Scoped tool restart/resize accept resource options; monitor task restart retains stage-only options. |

## Data Shapes
- Returns argparse.ArgumentParser; monitor namespaces carry f for dispatch.

## Notes
- Handler imports are deferred until parser construction to avoid eager cycles.

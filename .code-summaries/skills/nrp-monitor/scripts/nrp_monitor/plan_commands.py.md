# plan_commands.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/plan_commands.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.plan_commands`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
CLI subcommands for managing multi-step execution plans (nrp-monitor plan ...): sync, list, show, close, needs-owner, and resume. Run via CLI nrp-monitor plan <subcommand>.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.notify` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.plan_wakes` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_commands` — import consumer hint; not a proven runtime call.
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plan_wakes` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plans` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imports plans, state, notify, plan_wakes.
- **Shared data:** Manipulates plan directories in <state>/plans/<id>/.

## Dependencies
None

## Classes
None

## Functions
### `cmd_plan_needs_owner(a)`
> Flags a plan as waiting on human owner input, records reason, and pushes a Slack DM alert.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_commands.py:6`
### `cmd_plan_resume(a)`
> Clears owner wait on a plan, resuming automated continuation and resetting activity timers.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_commands.py:36`
### `cmd_plan_sync(a)`
> Parses and synchronizes plan definition and approval from markdown file into monitor state directory.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_commands.py:56`
### `cmd_plan_close(a)`
> Closes a finished plan, verifying no live tasks or continuations remain unless forced.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_commands.py:69`
### `plan_names()`
> Lists all known plan identifiers stored in the plans state directory.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plan_commands.py:114 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_commands.py:94`
### `plan_line(pid)`
> Renders a formatted single-line status summary for a plan.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plan_commands.py:117 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plan_commands.py:128 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_commands.py:99`
### `cmd_plan_list(a)`
> Displays listing of all registered plans, approval bounds, and auto-continue status.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_commands.py:111`
### `cmd_plan_show(a)`
> Outputs comprehensive plan details including groups, wake policies, results paths, and event logs.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_commands.py:123`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Plan reference format: PATH#PLAN_ID pointing to markdown plan file and its plan section. |
| Env session IDs: reads CLAUDE_CODE_SESSION_ID or CODEX_THREAD_ID to record which session requested owner action. |

## Data Shapes
- Plan header dict loaded from <state>/plans/<id>/header.json.
- Plan state dict loaded from <state>/plans/<id>/state.json containing ledger, status, reason, owner_wait, and events.

## Notes
- cmd_plan_close requires --force if there are live tasks or running continuations for that plan.
- cmd_plan_needs_owner transitions plan to waiting, records reason, and sends an owner push notification.
- cmd_plan_resume clears owner wait state, re-arms idle check-in timers, and transitions status to running.

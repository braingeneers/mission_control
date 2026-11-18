# model.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/task/model.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.task.model`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Defines task lifecycle state transition rules and machine (`transition`, `can`, `TRANSITIONS`), valid status sets (`LIVE`, `HELD`, `TERMINAL`), and resource resizing heuristics.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.legacy` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.stage_jobs` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_commands` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.tier0` — import consumer hint; not a proven runtime call.
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imported and invoked by `task_commands.py`, `pass_.py`, `util.py`, and `tier0.py` to perform all task state mutations.

## Dependencies
None

## Classes
### IllegalTransition(Exception)
> unclear — see source
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/model.py:22`
**Kind:** class. **Instantiated by:** skills/nrp-monitor/scripts/nrp_monitor/task/model.py:34 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None

## Functions
### `can(t, event)`
> Checks whether a transition event is valid from the task's current status.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/model.py:26`
### `transition(t, event, why=None, **fields)`
> Transitions task to new status according to state machine rules, updates extra fields, and logs event message.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/model.py:30`
### `resize_advice(line)`
> Parses resource flag strings to compute recommended memory shrink, CPU adjust, or GPU bundle advice.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/model.py:44`

## Config / CLI
None

## Data Shapes
- Task dictionary: requires `status` string field matching one of `LIVE`, `HELD`, or `TERMINAL`.

## Notes
- Status transitions are strictly validated against `TRANSITIONS` matrix; invalid moves raise `IllegalTransition`.
- Releasing a hold automatically purges unhandled escalation wake events from `webhook_outbox`.

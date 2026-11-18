# plan_wakes.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.plan_wakes`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Manages group wake coalescing, plan completion wake policies, terminal step wake generation, and idle plan fallback check-ins. Imported by cli, continuation, ladder, state; not run as a CLI directly.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.continuation` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.plan_commands` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.state` — import consumer hint; not a proven runtime call.
- **Uses:** `continuation` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plan_commands` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plans` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imports decisions, notify, plan_commands, plans, state, wake, continuation.
- **Shared data:** Invokes continuation.continue_task and wake.queue_task_webhook.

## Dependencies
None

## Classes
None

## Functions
### `step_mates(t)`
> Returns list of sibling task dictionaries executing the same plan step.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:5`
### `task_group(t, h)`
> Identifies which plan group a task belongs to based on task metadata or plan header.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:25 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:33 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:17`
### `completion_policy(t)`
> Resolves effective completion notification policy (task, group, digest) for a task.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:125 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:277 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:283 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:65 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:22`
### `group_members(pid, group, h)`
> Collects all task instances associated with a specified plan group.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:64 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:30`
### `group_ready(h, group, members)`
> Determines whether all declared steps in a group are fully completed and closed.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:65 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:36`
### `process_group_wakes(a)`
> Evaluates ready plan groups and fires a coalesced group completion webhook wake.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:292 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:49`
### `terminal_wake(t)`
> Dispatches terminal webhook wake or suppresses it based on plan completion policy.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:106`
### `step_done_summary(t, sib)`
> Formats descriptive summary of completed step tasks and outcomes for coordinator wake.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:139 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:145`
### `step_siblings(t, include_cancelled=False)`
> The other tasks bound to the same plan step as task `t` (from the plan's ledger), as loaded task dicts; cancelled ones do not count.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:11 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:130 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:275 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:155`
### `continuation_covers(c, t)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:282 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:168`
### `process_plan_fallbacks(a)`
> Sends single backup check-in wake when an active plan sits idle without progress beyond threshold.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:293 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:177`
### `skip_closed_continuation(n)`
> Marks late task completion as closed without launching subsequent steps if plan is closed.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:267 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:246`
### `process_continuations(a, st=None)`
> Main driver advancing finished plan tasks through continuation checks, group wakes, and fallbacks.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py:257`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Plan run block wake policies: task, group, or digest (with group overrides wake_<group>). |
| Constant FALLBACK_SINCE (1794674429, 2026-11-14): epoch timestamp gate preventing alerts on historical plans. |
| Default fallback_hours (3 hours): period of inactivity before idle plan coordinator check-in fires. |

## Data Shapes
- Group members list: list of task dicts belonging to a plan group.
- Fallback period dict: {activity: float, count: int, last: float?} stored in plan state.json.

## Notes
- Coalesces completion notifications: under wake: group, individual task completion wakes are suppressed (wake_avoided) until all group steps finish.
- Idle fallback checks: if an entire plan is idle for more than fallback_hours with all tasks finished, wakes coordinator chat once per idle period.
- Terminal wake handler ensures step completion wakes are emitted only after all sibling tasks in that step have finished.

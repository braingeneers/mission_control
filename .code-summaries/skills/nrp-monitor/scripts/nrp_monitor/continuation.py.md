# continuation.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/continuation.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.continuation`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Orchestrates automated multi-step plan continuations when a plan task finishes, generating continue-agent prompts, evaluating outputs against acceptance criteria, and updating plan state. Imported by plan_wakes and cli; not run directly as a CLI.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.plan_wakes` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Uses:** `agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plan_wakes` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plans` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `task_agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imports agents, decisions, notify, plan_wakes, plans, state, task_agents, wake.
- **Shared data:** Launches task_agents.run_task_agent with kind='continue'.
- **Shared data:** Writes to plan directory results.md.

## Dependencies
None

## Classes
None

## Functions
### `person_resolution_context(t)`
> Extracts chronological resume and skip notes written by coordinators or humans.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/continuation.py:38 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/continuation.py:5`
### `continue_prompt(t, h, go, held)`
> Builds template-based prompt for the continue agent including stage outputs and postcheck results.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/continuation.py:164 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/continuation.py:20`
### `close_continuation(n, status, line)`
> Finalizes continuation state transactionally, sets plan state, queues wake events, and logs to results.md.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/continuation.py:172 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/continuation.py:46`
### `continue_task(n, a)`
> Evaluates plan eligibility, claims task continuation, spawns continue agent, and handles outcome.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/continuation.py:121`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Flag <state>/on_done.enabled: controls whether auto-continuation is enabled. |
| Plan file run block settings: approved_through, stop_for_owner, may_touch. |

## Data Shapes
- Task continuation dict: {'state': 'running'|'closed', 'started': float, 'go': [str], 'registered': [str], 'status': 'CONTINUED'|'WAITING'|'NOT-DONE'|'STOPPED'|'FAILED'|'OFF', 'line': str, 'closed': float}.
- Continuation agent prompt template populated from continue_agent.md.

## Notes
- Appends execution progress and verdicts to plan results.md log.
- Queues webhook wake events on planned stops or failure terminations.
- Releases continuation claim if agent runs out of quota mid-call to enable automatic retry on next pass.

# task_agents.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/task_agents.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.task_agents`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Prompt builder and execution harness for task-level sub-agents (Tier 1 triage judge, Tier 2 fixer, Tier 2.5 deputy, continuation agent), enforcing tool allowlists, manifest validation checkpoints, and handoff logging. Imported by ladder, continuation; not run as a CLI directly.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.continuation` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
- **Uses:** `agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `config` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `ladder` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plans` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `util` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imports config, decisions, ladder, state, wake, agents, notify, plans, util, task.registry.
- **Shared data:** Dispatches agent calls through agents.dispatch_agent.

## Dependencies
None

## Classes
None

## Functions
### `task_prompt(t)`
> Constructs detailed prompt for fixer and deputy agents populated with failure details and history.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_agents.py:6`
### `run_task_agent(n, prompt_text, a, kind='fix')`
> Executes task agent with role-specific allowlists, manifest validation checkpoints, and cost tracking.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task_agents.py:34`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env NRP_TASK: sets active task context for sub-agent environment. |
| Env NRP_MONITOR_AGENT_ROLE: identifies agent role (fix, deputy, triage, continue) for permission gating. |
| Templates used: task_agent.md, continue_agent.md, task_triage.md from state.TPL. |

## Data Shapes
- Agent run record dict: {ts: float, kind: str, runner: str, model: str, usage: dict?, cost: float?, turns: int?, result: str, denials: int, verdict: str?, ...}.
- Tool allowlist: list of strings like [Bash(nrp-task:*), Read(/path/**), Edit(/path/**)].

## Notes
- Checkpoints manifests before agent runs (agent_manifest_checkpoint); validates all manifests structurally after run (validate_agent_manifests) and rejects invalid YAML edits.
- Parses agent output to extract standard verdict lines (RESOLVED, DONE, ESCALATE, STOPPED, NOT-DONE, RESUBMITTED, UTIL_OK).
- Appends agent actions and handoff text to handoff.md in the task directory.
- Logs cost and token usage events to costs.jsonl via decisions.cost_event.

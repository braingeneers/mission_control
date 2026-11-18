# legacy.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/legacy.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.legacy`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Legacy job and pod utilization monitoring loop, handling strike-based pod resizing/deletion, 3-hour GPU policy enforcement, account alarms, and multi-attempt job follow-up agents. Imported by cli; not run as a CLI directly.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.agents` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Uses:** `agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `config` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `ladder` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `model` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `pass_` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `util` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imports agents, cluster, config, ladder, notify, state, util, wake, task.model, task.pass_.
- **Shared data:** Executes nrp-util-check subprocess.
- **Shared data:** Dispatches agents via agents.run_agent.

## Dependencies
None

## Classes
None

## Functions
### `acct_alarm(st, lines, bad, dry, mine=None)`
> Tracks consecutive passes with high violation counts and sends urgent push alert when 3+ pods fail.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/legacy.py:63 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/legacy.py:71 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/legacy.py:7`
### `check_pods(a, st)`
> Runs periodic pod utilization checks across active pods, managing strikes and triggering pod agents.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/legacy.py:27`
### `_gpu_low(lines, mine, min_age_s)`
> [(pod, lowest GPU %% or None when no DCGM series, age_s, line)] for LOW lines of our pods at least `min_age_s` old that carry a GPU number under the floor nrp-util-check applied (or no DCGM series). CPU/memory-only lines are ignored (they stay with the 10-min strikes).
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/legacy.py:157 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/legacy.py:160 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/legacy.py:130`
### `gpu_long_actions(warn_lines, enforce_lines, mine)`
> Filters pod utilization check lines to identify pods violating 60-min warning or 90-min enforcement GPU floors.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/legacy.py:190 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/legacy.py:149`
### `gpu_long_pass(a, st, mine)`
> Monitors long-window GPU utilization averages and deletes offending Jobs before NRP administrative action.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/legacy.py:44 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/legacy.py:165`
### `record_resize(st, pod, owner, flag_line, verdict)`
> Resize advice goes to resize.log and, when the owner Job is registered, to its resume notes (the follow-up reads them).
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/legacy.py:122 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/legacy.py:98 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/legacy.py:250`
### `check_jobs(a, st)`
> Watches legacy registered Jobs, detects completion/failure, and triggers tiered follow-up agents.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/legacy.py:267`
### `followup_solved(result)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/legacy.py:332 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/legacy.py:388 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/legacy.py:339`
### `tiered_job_followup(job, rec, prompt, allowed, triage_allowed=None)`
> Executes triage and repair ladder steps for completed or failed legacy Jobs.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/legacy.py:317 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/legacy.py:344`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Constant GPU_WARN_WINDOW_MIN (60 min) and GPU_ENFORCE_WINDOW_MIN (90 min) for GPU utilization averaging. |
| Constant RESUME_MAX (20 KB): maximum resume notes file size for follow-up agents. |
| Constant JOB_GRACE_S: grace period before missing jobs are declared gone. |

## Data Shapes
- Account alarm inputs: nrp-util-check output lines and parsed strike flags.
- gpu_long_actions output: [(pod, 'enforce'|'warn', pct, age_s, line)].
- Legacy jobs state dict in jobs.json: {job_name: {'status': 'watching'|'handled', 'result': str?, 'added': float, ...}}.

## Notes
- Enforces strike system: strike 1 records resize recommendation; strike 2 launches pod-check agent to delete/resize.
- Enforces NRP 3-hour GPU average rule: warns at 60 min below floor; automatically deletes Job at 90 min to protect account.
- Triggers account alarm push notification if 3+ pods violate NRP utilization bands across 2 consecutive passes.

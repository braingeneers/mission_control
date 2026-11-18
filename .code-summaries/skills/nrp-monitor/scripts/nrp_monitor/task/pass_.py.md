# pass_.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Implements core task pass execution loop (`process_tasks`, `process_task`, `advance_task`, `do_submit`), orchestrating stage submissions, dependency tracking, failure classification, postchecks, and completion handling.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.decisions` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.legacy` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.tier0` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.timeouts` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
- **Uses:** `agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `continuation` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `ladder` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `red_alert` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `s3` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `sizing` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `model` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `task_agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `tier0` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `util` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Central coordinator for tasks: calls `nrp_monitor.cluster` for Kubernetes operations, `nrp_monitor.s3` for existence checks, `nrp_monitor.tier0` for heuristic fixes, `nrp_monitor.ladder` for failure escalation, and `nrp_monitor.task_agents` for LLM fixer/followup agents.

## Dependencies
None

## Classes
None

## Functions
### `save_task_logs(t, s, reason)`
> Fetches and saves container logs and Kubernetes describe outputs to task log files, extracting key-value outputs on success.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:181 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:10`
### `run_postcheck(t)`
> Executes optional local validation command after all stages complete to verify outputs.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:350 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:40`
### `pod_started(ns, job)`
> Queries Kubernetes pods to find earliest container start timestamp for a Job.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:55`
### `classify(t, s, logtxt)`
> Classifies Job failures into failure classes (`resources`, `infra`, `code`, `timeout`) and signatures using pod conditions, exit codes, and log inspection.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:73`
### `do_submit(n, sid, reason, by)`
> Validates manifest and retry budgets, excludes bad nodes, applies Job via kubectl, and updates stage status.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:297 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:338 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:123`
### `s3_gate(s)`
> Checks stage `after_s3` dependencies, returning any S3 URIs that do not yet exist.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:276 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:323 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:235`
### `note_waiting(n, sid, missing)`
> Records list of missing S3 dependencies on stage object and logs state event if changed.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:324 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:241`
### `advance_task(n, jobs, a)`
> Evaluates task stage progression, submits ready stages, invokes Tier 0/ladder failure handling, and processes completion.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:464 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:254`
### `recover_held_completion(n, jobs)`
> Checks if a held or failed task's Job actually completed successfully with valid S3 outputs and recovers it.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:462 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:386`
### `process_tasks(a, st)`
> Iterates over all active and held tasks, executing task monitoring passes within a cluster pass snapshot.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:413`
### `process_task(n, a)`
> Wraps single task pass execution with manifest validation, exception tracking, and coordinator escalation.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:424 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:431`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env `NRP_MONITOR_S3_ENDPOINT`: endpoint URL for S3 operations. |
| Constant `_m_state.BLOCK_ESCALATE_S`: duration threshold before escalating blocked submits to coordinator/owner. |
| Constant `_m_state.TASK_EXCEPTION_LIMIT`: consecutive exception threshold before escalating unhandled task pass crashes. |

## Data Shapes
- Manifest JSON/YAML documents: Kubernetes Job objects.
- Postcheck result dict: `{"ok": bool, "rc": int, "output": str}`.
- Stage dictionary: `{"id": str, "job": str, "state": str, "manifest": str, "after": list, "after_s3": list, "done_s3": list, "attempt": int, "outputs": dict, ...}`.

## Notes
- Saves up to 120 KB of container logs, Job descriptions, and pod descriptions to disk on failure or completion.
- Implements account RED ALERT and quota hold behaviors, blocking submissions until dry-runs accept.
- Injects cluster-wide bad-node exclusions into submitted manifest copies.

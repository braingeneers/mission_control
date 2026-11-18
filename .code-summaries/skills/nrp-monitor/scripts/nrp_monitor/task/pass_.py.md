# pass_.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Orchestrates each task pass: stage dependencies and S3 gates, failure classification, completion and postcheck handling, held completion recovery and repeated exception escalation. Submissions and diagnostics delegate to stage_jobs; snapshots are used for observation while action guards stay fresh.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.shadow` — import consumer hint; not a proven runtime call.
- **Uses:** `agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `continuation` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `ladder` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `red_alert` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `s3` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `stage_jobs` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `model` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `task_agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `tier0` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `util` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** **Shared data:** Central coordinator for tasks: calls `nrp_monitor.cluster` for Kubernetes operations, `nrp_monitor.s3` for existence checks, `nrp_monitor.tier0` for heuristic fixes, `nrp_monitor.ladder` for failure escalation, and `nrp_monitor.task_agents` for LLM fixer/followup agents.

## Dependencies
None

## Classes
None

## Functions
### `run_postcheck(t)`
> Executes optional local validation command after all stages complete to verify outputs.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:210 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:9`
### `pod_started(ns, job)`
> Earliest container start of the Job's pods (None if no container ever ran).
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:24`
### `classify(t, s, logtxt)`
> (class, signature, detail) from Job conditions, pod status, exit code and the log tail. No model.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:42`
### `s3_gate(s)`
> URIs in the stage's `after_s3` that do not (yet) exist. An unreadable answer counts as missing: the stage just waits.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:136 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:183 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:94`
### `note_waiting(n, sid, missing)`
> Record what a pending stage waits on (shown by `task show`); only writes when it changes.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:184 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:100`
### `advance_task(n, jobs, a)`
> Evaluates task stage progression, submits ready stages, invokes Tier 0/ladder failure handling, and processes completion.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:324 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:113`
### `recover_held_completion(n, jobs)`
> Checks if a held or failed task's Job actually completed successfully with valid S3 outputs and recovers it.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:322 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:246`
### `process_tasks(a, st)`
> Iterates over all active and held tasks, executing task monitoring passes within a cluster pass snapshot.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:273`
### `process_task(n, a)`
> Wraps single task pass execution with manifest validation, exception tracking, and coordinator escalation.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:284 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py:291`

## Config / CLI
None

## Data Shapes
- Manifest JSON/YAML documents: Kubernetes Job objects.
- Postcheck result dict: `{"ok": bool, "rc": int, "output": str}`.
- Stage dictionary: `{"id": str, "job": str, "state": str, "manifest": str, "after": list, "after_s3": list, "done_s3": list, "attempt": int, "outputs": dict, ...}`.

## Notes
- Saves up to 120 KB of container logs, Job descriptions, and pod descriptions to disk on failure or completion.
- Implements account RED ALERT and quota hold behaviors, blocking submissions until dry-runs accept.
- Injects cluster-wide bad-node exclusions into submitted manifest copies.

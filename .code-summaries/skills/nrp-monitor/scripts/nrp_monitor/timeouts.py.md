# timeouts.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/timeouts.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.timeouts`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Manages active deadline extensions, queue time crediting, and Tier 0 timeout recovery for running NRP jobs. Checks if log activity is progressing and resubmits resumable stages with doubled deadlines upon expiration.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `stage_jobs` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Shared data:** **Shared data:** Called by `deadline_watch` during task monitoring loop in `nrp_monitor.task.pass_`.
- **Shared data:** **Shared data:** Uses `nrp_monitor.cluster.kubectl` for patching jobs and fetching logs/pods, and `nrp_monitor.task.pass_.do_submit` to resubmit timed-out stages.
- **Shared data:** Stage submission, resource snapshots/propagation or saved task diagnostics now resolve through stage_jobs; see call sites for the applicable operation.

## Dependencies
None

## Classes
None

## Functions
### `patch_deadline(ns, job, secs)`
> Executes merge patch via kubectl on a Kubernetes Job to update its `activeDeadlineSeconds`.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:75 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:11`
### `log_signature(ns, job)`
> Hash of the Job's last log lines: it changes between two passes only when the pod is still writing.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:59 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:16`
### `pod_waiting_error(ns, job)`
> A pod stuck on an error (image pull, bad config) is not queueing: its deadline is not extended.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:71 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:23`
### `deadline_watch(n, s, info)`
> Tier 0 for one running stage whose Job is Running or Pending. activeDeadlineSeconds counts from the Job's start, Pending time included, so: (1) once the pod has started after a long queue, credit the queue time (deadline = original + queue wait); (2) a pod that is still Pending near its deadline is kept alive (deadline = elapsed + original), a limited number of times, unless it is stuck on an error; (3) a pod that is still progressing near its d…
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:34`
### `stage_resumable(s)`
> True only when the stage says so (`resumable: true` in TASK.json) or its manifest passes an explicit skip-existing/resume flag. Nothing is inferred beyond that: a stage that restarts from scratch must not be resubmitted blindly.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:110 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:92`
### `tier0_timeout(n, f)`
> A stage died of DeadlineExceeded while running. If it resumes by skipping finished items, resubmit it once with 2x deadline (the task's manifest copy is edited); otherwise (or when that was already done) False: the failure enters the ladder at Tier 1.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:103`

## Config / CLI
None

## Data Shapes
- Stage `dl` dictionary: `{"orig": int, "credit": int, "exts": int, "pend": int, "sig": str, "capped": bool, "stalled": bool, "resubmits": int, "patch_fail": int}`.

## Notes
- Invokes `kubectl patch job` to dynamically extend `activeDeadlineSeconds` in Kubernetes.
- Determines job progress by hashing the last 20 log lines across monitor passes.

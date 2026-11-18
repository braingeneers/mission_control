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
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `pass_` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Shared data:** Called by `deadline_watch` during task monitoring loop in `nrp_monitor.task.pass_`.
- **Shared data:** Uses `nrp_monitor.cluster.kubectl` for patching jobs and fetching logs/pods, and `nrp_monitor.task.pass_.do_submit` to resubmit timed-out stages.

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
> Computes SHA-1 hash of the last 20 log lines of a Job to detect whether log output is progressing.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:59 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:16`
### `pod_waiting_error(ns, job)`
> Inspects pod container statuses for waiting reasons like ImagePullBackOff or CreateContainerError.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:71 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:23`
### `deadline_watch(n, s, info)`
> Tracks active deadline for running/pending stages, credits queue wait time, extends pending pods, and extends progressing jobs up to max extensions.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:34`
### `stage_resumable(s)`
> Checks if a stage is marked `resumable: true` or contains `--skip-existing`/`--resume` flags in its manifest.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:110 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:92`
### `tier0_timeout(n, f)`
> Handles DeadlineExceeded failures by doubling activeDeadlineSeconds and resubmitting if stage is resumable.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/timeouts.py:103`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| `_m_state.DEADLINE_CREDIT_MIN_S`: minimum pending duration required to credit queue wait time to activeDeadlineSeconds. |
| `_m_state.DEADLINE_EXT_MAX`: maximum number of deadline extensions granted to actively progressing jobs. |
| `_m_state.DEADLINE_PEND_EXT_MAX`: maximum number of extensions for pods waiting in Pending state. |
| `_m_state.DEADLINE_RESUBMITS_MAX`: maximum resubmissions of expired resumable stages at 2x deadline. |

## Data Shapes
- Stage `dl` dictionary: `{"orig": int, "credit": int, "exts": int, "pend": int, "sig": str, "capped": bool, "stalled": bool, "resubmits": int, "patch_fail": int}`.

## Notes
- Invokes `kubectl patch job` to dynamically extend `activeDeadlineSeconds` in Kubernetes.
- Determines job progress by hashing the last 20 log lines across monitor passes.

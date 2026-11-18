# util.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/util.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.util`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Implements cluster utilization observation, waiver enforcement, memory and CPU right-sizing evidence gathering, and utilization restarts for NRP jobs under policy constraints.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cluster` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.legacy` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_agents` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_commands` — import consumer hint; not a proven runtime call.
- **Uses:** `agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `config` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `ladder` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `sizing` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `model` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `pass_` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `task_agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `tier0` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `timeouts` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Called by `advance_task` in `nrp_monitor.task.pass_` and `cmd_util_restart`.
- **Shared data:** Queries Prometheus via `nrp_monitor.cluster.thanos_query` and `nrp_monitor.tier0.thanos_peak_mem`.
- **Shared data:** Uses `nrp_monitor.task_agents` to run LLM triage or fixer agents when necessary.

## Dependencies
None

## Classes
None

## Functions
### `flag_rule(line)`
> Identifies which rule flagged a pod (`gpu`, `nrp`, `lab`, or `unknown`) from nrp-util-check message tokens.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/util.py:145 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:7`
### `waiver_stage(t, w)`
> Finds the stage in a task corresponding to a waiver's Job name.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/util.py:28 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:21`
### `waiver_active(t, w)`
> Verifies if a utilization waiver is currently active and belongs to the running Job submission.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/util.py:37 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:25`
### `active_waiver(t, sid)`
> Retrieves the active utilization waiver for a given stage id if present.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/util.py:146 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:32`
### `util_ok_extract(text)`
> Extracts and cleans evidence text following the last `UTIL_OK:` line in an agent response.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:40`
### `util_waiver_check(t, f, claim)`
> Validates whether a fix agent's waiver claim meets policy (lab floor only, non-GPU, running Job, within waiver budget).
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/util.py:102 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:57`
### `util_waive(n, f, claim, a)`
> Accepts a utilization waiver, clears failure state, and restores stage to running without consuming retries.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:94`
### `task_pod_flag(st, n, sid, pod, kind, line)`
> Processes incoming pod utilization flag, differentiating between STUCK infra failures, lab waivers, NRP band violations, and low-utilization evidence.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:138`
### `process_util_event(n, a)`
> Coordinates agent triage and review for pending utilization events on running tasks.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:174`
### `util_nrp_review(n, t, event, context, numbers, a)`
> Runs fixer agent or wakes coordinator chat when a task drops below NRP's 20% utilization floor.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:210`
### `memory_low_evidence(t, s, flagged_pod, working_set_only=False)`
> Aggregates memory usage evidence from Thanos metrics, pod status, and OOM history to calculate right-sized memory requirements.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/util.py:154 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/util.py:419 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:246`
### `check_orphans(a, st)`
> Scans the Kubernetes namespace for running unmanaged jobs not tied to any known task or watch registration.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:299`
### `utilization_restart(n, sid=None, cpu=None, mem=None, container_resources=None)`
> Replaces a running or pending stage Job with resized CPU/memory requests and limits without registering a failure.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/util.py:445 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:323`
### `utilization_band_action(n, sid, pod, line)`
> Enforces bounded grace period on NRP band violations, deleting violating jobs or resizing and restarting resumable stages.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/util.py:152 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/util.py:193 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:376`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Owner setting `nrp_violation_grace_minutes` (default 30): grace period before safety-stopping violating pods. |
| Policy config `account_block_after_violating_pods` (default 4): offender count threshold triggering immediate safety stop. |
| Policy config `small_pod_exempt`: exempt thresholds `{"cpu": 1, "memory_bytes": 2000000000}`. |
| Policy config `cpu_band`, `memory_band`: utilization acceptance thresholds (e.g. `[0.2, 1.5]`). |
| Constants `_m_config.util_waiver_max()` and `_m_config.util_waiver_hours()`: maximum waivers and waiver duration. |

## Data Shapes
- Evidence dict from `memory_low_evidence`: `{"peaks_gi": dict, "ages_seconds": dict, "request_gi": float, "limit_gi": float, "oom_limits_gi": list, "true_peak_gi": float, "need_gi": float, "right_gi": int, "spread": float, "suggested_verdict": str, "ramp_up": bool, ...}`.

## Notes
- Utilization flags are treated as judge events or warnings rather than task failures.
- Distinguishes between NRP account-level violations and lab-specific utilization rules.
- `utilization_restart` deletes and replaces running Kubernetes Jobs without consuming retry budget.

# tier0.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.tier0`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Implements Tier 0 deterministic heuristic automated fixes (node exclusion, memory OOM bumping, lost pod resubmission) and queue monitoring for NRP jobs without invoking LLM agents.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.registry` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_commands` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
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
- **Shared data:** Called by `advance_task` in `nrp_monitor.task.pass_` and `process_task`.
- **Shared data:** Uses `nrp_monitor.cluster` for Thanos and Kubernetes API calls, `nrp_monitor.sizing` for memory conversions, and `nrp_monitor.task.registry` for manifest reading/writing.

## Dependencies
None

## Classes
None

## Functions
### `thanos_peak_mem(ns, job, container, since_ts, per_pod=False)`
> Queries Prometheus/Thanos for peak container working set memory bytes since given timestamp, optionally grouped by pod.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/tier0.py:59 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:10`
### `vanished_nodes(t, s)`
> Queries Thanos for historical node placement of vanished pods matching a job pattern.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/tier0.py:109 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:31`
### `tier0_oom(t, s, f)`
> Calculates updated memory limits and requests scaled by 1.3x observed peak (or 2x limit) up to configured GiB cap.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:38`
### `node_fault_of(t, s, f)`
> Inspects pod status, conditions, and log tail for matching known Kubernetes node fault patterns or vanished pods.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/tier0.py:133 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:80`
### `exclude_node(doc, node)`
> Mutates Kubernetes Job pod affinity to add a NotIn hostname constraint for the specified bad node.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:115`
### `tier0_node(t, s, f)`
> Evaluates node faults, records bad nodes in cluster tracking, and generates updated manifest with excluded node.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/tier0.py:189 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:132`
### `tier0_lost(t, s, f)`
> Produces unchanged manifest resubmission rule for pods lost without exit code or traceback.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:149`
### `_oom_matches(t, s, f)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:158`
### `tier0_fix(n, a)`
> Applies matching Tier 0 rules (node, oom, lost) sequentially, resubmitting the stage if successful.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:171`
### `queue_ceiling_seconds(value)`
> Parses human-readable duration strings (s, m, h, d) into float seconds.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/tier0.py:276 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:214`
### `report_long_pending(n, jobs)`
> Safe wrapper around `_report_long_pending` that logs exceptions without raising.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:221`
### `_report_long_pending(n, jobs)`
> Monitors pending jobs, detects unschedulable states, triggers coordinator notifications when queue wait ceiling is exceeded, and clears queue holds when scheduled.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/tier0.py:224 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:229`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Owner setting `tier0_mem_cap_gi`: max memory ceiling for automatic OOM resizing (defaults to `_m_state.OOM_MAX_GI_DEFAULT`). |
| `_m_config.util_policy()['limit_to_request_tolerance']` (default 0.2): allowed tolerance between memory limits and requests. |
| Constant `_m_state.NODE_EXCLUDE_MAX`: maximum bad nodes excluded per stage. |
| Constant `_m_state.OOM_FACTOR`: multiplier applied to observed peak memory on OOM. |
| Constants `_m_state.PENDING_REPORT_S` and `_m_state.PENDING_REREPORT_S`: threshold intervals for pending pod reports. |

## Data Shapes
- Thanos query result: list of dicts with `metric` labels and `value` timestamp-value pairs.
- Kubernetes Job manifest: dict representing Job resource definition with spec, template, affinity, containers, and resources.

## Notes
- Directly queries Prometheus/Thanos for container memory working sets and pod scheduling info.
- Edits stage manifest files in place and restores them if resubmission fails.
- Uses local imports `_m_ladder` and `_m_task_pass_` to break cyclic dependencies.

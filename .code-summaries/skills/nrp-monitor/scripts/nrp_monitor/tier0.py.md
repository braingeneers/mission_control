# tier0.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.tier0`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Implements Tier 0 deterministic heuristic automated fixes (node exclusion, memory OOM bumping, lost pod resubmission) and queue monitoring for NRP jobs without invoking LLM agents.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.stage_jobs` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.registry` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_commands` — import consumer hint; not a proven runtime call.
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `config` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `ladder` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `sizing` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `stage_jobs` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `model` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Shared data:** **Shared data:** Called by `advance_task` in `nrp_monitor.task.pass_` and `process_task`.
- **Shared data:** **Shared data:** Uses `nrp_monitor.cluster` for Thanos and Kubernetes API calls, `nrp_monitor.sizing` for memory conversions, and `nrp_monitor.task.registry` for manifest reading/writing.
- **Shared data:** Stage submission, resource snapshots/propagation or saved task diagnostics now resolve through stage_jobs; see call sites for the applicable operation.

## Dependencies
None

## Classes
None

## Functions
### `vanished_nodes(t, s)`
> Queries Thanos for historical node placement of vanished pods matching a job pattern.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/tier0.py:88 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:12`
### `tier0_oom(t, s, f)`
> (manifest doc, reason, record) raising the OOMKilled container's memory to observed peak x1.3, or None to leave it to the agents.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:19`
### `node_fault_of(t, s, f)`
> (node, evidence) of a pod of this stage's Job that hit a known node fault, else None. Pod status and conditions plus the saved log tail.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/tier0.py:112 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:59`
### `exclude_node(doc, node)`
> Add `kubernetes.io/hostname NotIn [node]` to every required node-affinity term of the Job's pod spec (idempotent).
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:94`
### `tier0_node(t, s, f)`
> Evaluates node faults, records bad nodes in cluster tracking, and generates updated manifest with excluded node.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/tier0.py:168 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:111`
### `tier0_lost(t, s, f)`
> (unchanged manifest doc, reason, record) for a lost pod; do_submit applies the shared bad-node list and the stage's budget.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:128`
### `_oom_matches(t, s, f)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:137`
### `tier0_fix(n, a)`
> True when a Tier 0 rule edited the manifest and resubmitted the failed stage. Never raises, never starts a model; False hands the failure to handle_failure unchanged (watch-only tasks, repeats, anything over a cap, no rule matched).
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:150`
### `queue_ceiling_seconds(value)`
> Parses human-readable duration strings (s, m, h, d) into float seconds.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/tier0.py:255 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:193`
### `report_long_pending(n, jobs)`
> Record bounded Pending reports and ask the coordinator before a long queue wait continues. Never raises.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:200`
### `_report_long_pending(n, jobs)`
> Monitors pending jobs, detects unschedulable states, triggers coordinator notifications when queue wait ceiling is exceeded, and clears queue holds when scheduled.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/tier0.py:203 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/tier0.py:208`

## Config / CLI
None

## Data Shapes
- Thanos query result: list of dicts with `metric` labels and `value` timestamp-value pairs.
- Kubernetes Job manifest: dict representing Job resource definition with spec, template, affinity, containers, and resources.

## Notes
- Directly queries Prometheus/Thanos for container memory working sets and pod scheduling info.
- Edits stage manifest files in place and restores them if resubmission fails.
- Uses local imports `_m_ladder` and `_m_task_pass_` to break cyclic dependencies.

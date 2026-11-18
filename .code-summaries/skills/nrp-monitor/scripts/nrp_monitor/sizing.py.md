# sizing.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.sizing`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Owns memory/CPU evidence and sizing primitives: Thanos working-set and CPU-rate peaks, saved cgroup peak extraction and single-container legacy fallback, memory-low evidence with OOM floors, quantity parsing and CPU request sizing. Also checks whether required node restrictions match any schedulable node. Manifest resource snapshots and propagation now live in stage_jobs.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.stage_jobs` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.tier0` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Shared data:** util calls memory_low_evidence, thanos_peak_mem, thanos_peak_cpu and cpu_request. tier0 calls memory quantity, saved-peak fallback and Thanos helpers. stage_jobs uses quantity parsing and zero_node_reason.
- **Shared data:** Reads task logs through state.task_dir and cluster Thanos/pod/node reads; memory_low_evidence updates stage memory evidence through task_txn.

## Dependencies
None

## Classes
None

## Functions
### `cpu_quantity(value)`
> Parses Kubernetes CPU strings (e.g. 500m, 2) into float core counts.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:8`
### `true_memory_peak(text, container=None)`
> Read the helper's JSON lines. RSS fallback is evidence, not a cgroup true peak.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/sizing.py:43 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:18`
### `saved_memory_peak(t, s, container=None, all_attempts=False)`
> Finds maximum true memory peak recorded across historical attempt log files for a stage.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/sizing.py:205 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/sizing.py:207 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:36`
### `mem_bytes(q)`
> Bytes of a Kubernetes memory quantity ('512Mi', '4Gi', '2G', '123456'); None when not understood.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/sizing.py:149 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/sizing.py:150 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/sizing.py:167 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/sizing.py:173 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:52`
### `mem_text(b)`
> Formats integer byte count as clean Gi or Mi Kubernetes memory string.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:64`
### `zero_node_reason(doc)`
> Required selectors are AND; affinity terms are OR. Read errors fail open.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:69`
### `thanos_peak_mem(ns, job, container, since_ts, per_pod=False)`
> Peak working-set bytes of the Job's pods (one container) since `since_ts`, from NRP's Prometheus; None when unavailable.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/sizing.py:158 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:118`
### `memory_low_evidence(t, s, flagged_pod, working_set_only=False)`
> Aggregates memory usage evidence from Thanos metrics, pod status, and OOM history to calculate right-sized memory requirements.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:140`
### `thanos_peak_cpu(ns, job, container, since_ts)`
> Whole-life peak CPU rate for one Job container; None without samples.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:190`
### `cpu_request(peak, small)`
> Utilization sizing: 1.5 times peak, rounded up to millicores, with policy floor.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:197`
### `container_memory_peak(t, s, container, single=False, all_attempts=False)`
> Saved cgroup peak, allowing unnamed legacy evidence only for a single container.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/sizing.py:159 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:203`

## Config / CLI
None

## Data Shapes
- resource_values return: list of {name: container_name, requests: {cpu: str, memory: str}, limits: {cpu: str, memory: str}}.
- NRP_MEMORY_PEAK JSON log payload: {bytes: int, source: cgroup_v1|cgroup_v2, container: str}.

## Notes
- True memory peaks: extracts kernel cgroup peaks rather than RSS to ensure reclaimable page cache is accounted for accurately.
- Propagates increased CPU/memory allocations from failed/resized stages to unfinished sibling stages within the same resource_group.
- Zero-node detector: evaluates pod nodeSelector and requiredDuringSchedulingIgnoredDuringExecution affinity against live cluster nodes to catch unfulfillable scheduling constraints before submission.

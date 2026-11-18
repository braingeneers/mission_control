# sizing.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.sizing`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Resource sizing calculator, true cgroup memory peak extractor, resource propagation engine, and node affinity/selector feasibility validator. Imported by ladder, state, task_pass, task_commands; not run as a CLI directly.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.tier0` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Shared data:** Imports cluster, state, task.registry.
- **Shared data:** Reads saved logs in <task>/logs/.

## Dependencies
None

## Classes
None

## Functions
### `cpu_quantity(value)`
> Parses Kubernetes CPU strings (e.g. 500m, 2) into float core counts.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:6`
### `resource_values(doc)`
> Extracts container CPU and memory requests and limits from a pod/Job manifest.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/sizing.py:20 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:12`
### `resource_template(doc)`
> Constructs normalized list of container resource specs and images from manifest.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:19`
### `true_memory_peak(text, container=None)`
> Parses true cgroup memory peak bytes from container stdout log lines.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/sizing.py:52 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:27`
### `saved_memory_peak(t, s, container=None, all_attempts=False)`
> Finds maximum true memory peak recorded across historical attempt log files for a stage.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:45`
### `propagate_resources(t, source)`
> Updates resource requests/limits in unfinished sibling stage manifests within a resource group.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:59`
### `mem_bytes(q)`
> Converts Kubernetes memory quantity string into integer bytes.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:100`
### `mem_text(b)`
> Formats integer byte count as clean Gi or Mi Kubernetes memory string.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:112`
### `zero_node_reason(doc)`
> Verifies whether any active cluster node can satisfy the pod nodeSelector and affinity requirements.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/sizing.py:117`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Memory units supported: Ki, Mi, Gi, Ti, k, K, M, G, T, or plain bytes. |
| Peak memory regex: parses NRP_MEMORY_PEAK <json> lines output by workload containers. |

## Data Shapes
- resource_values return: list of {name: container_name, requests: {cpu: str, memory: str}, limits: {cpu: str, memory: str}}.
- NRP_MEMORY_PEAK JSON log payload: {bytes: int, source: cgroup_v1|cgroup_v2, container: str}.

## Notes
- True memory peaks: extracts kernel cgroup peaks rather than RSS to ensure reclaimable page cache is accounted for accurately.
- Propagates increased CPU/memory allocations from failed/resized stages to unfinished sibling stages within the same resource_group.
- Zero-node detector: evaluates pod nodeSelector and requiredDuringSchedulingIgnoredDuringExecution affinity against live cluster nodes to catch unfulfillable scheduling constraints before submission.

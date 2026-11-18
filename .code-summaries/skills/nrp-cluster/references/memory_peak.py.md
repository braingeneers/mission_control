# memory_peak.py

**Path:** `skills/nrp-cluster/references/memory_peak.py`
**Module:** `skills.nrp-cluster.references.memory_peak`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Process wrapper script that executes an arbitrary child command, measures cgroup v1/v2 memory peak usage upon exit, preserves exit status, and records memory metrics into a done JSON file.

## Connections
- **Shared data:** Used in Kubernetes / NRP cluster job pods to capture empirical memory consumption.

## Dependencies
None

## Classes
None

## Functions
### `measure()`
> Inspects cgroup hierarchy and getrusage to obtain peak memory in bytes.
> **Called by:** skills/nrp-cluster/references/memory_peak.py:51 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-cluster/references/memory_peak.py:17`
### `main()`
> Executes child command via subprocess, measures memory, updates marker file, and exits with command exit code.
> **Called by:** skills/nrp-cluster/references/memory_peak.py:69 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-cluster/references/memory_peak.py:41`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| `--container NAME`: Optional container name label. |
| `--done-json PATH`: Path to target success marker JSON file to update. |

## Data Shapes
- Input: Command line arguments following `--` delimiter.
- Output: Updates JSON marker file with memory peak bytes, timestamp, and exit code.

## Notes
- Inspects `/proc/self/cgroup` and `/sys/fs/cgroup` for `memory.peak` (cgroup v2) or `memory.max_usage_in_bytes` (cgroup v1).
- Falls back to Python `resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss`.

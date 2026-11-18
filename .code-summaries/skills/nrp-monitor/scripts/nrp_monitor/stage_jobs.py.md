# stage_jobs.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/stage_jobs.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.stage_jobs`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Owns stage Job submission and replacement, resource snapshots and manifest propagation, saved diagnostics and diagnostics-before-delete. do_submit enforces retry, manifest, GPU, admission and fresh Job-state guards. utilization_restart edits resource requests/limits and queues budget-free replacement; propagate_resources raises compatible sibling resources from successful attempt evidence.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.decisions` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.legacy` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.shadow` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_commands` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.tier0` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.timeouts` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `ladder` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `red_alert` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `sizing` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `model` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `tier0` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Called by task pass, ladder, tier0, timeouts, decisions, nrp_task, task_commands, util and legacy.
- **Shared data:** Uses sizing for quantities and node feasibility, task.registry for manifest parsing/validation/writing, cluster for fresh guards and apply/delete.

## Dependencies
None

## Classes
None

## Functions
### `save_task_logs(t, s, reason)`
> Fetches and saves container logs and Kubernetes describe outputs to task log files, extracting key-value outputs on success.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/stage_jobs.py:262 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/stage_jobs.py:11`
### `do_submit(n, sid, reason, by)`
> Submit a stage's manifest. A failed stage = a retry (budgets enforced here, whoever asks). Returns (ok, message).
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/stage_jobs.py:41`
### `utilization_restart(n, sid=None, cpu=None, mem=None, container_resources=None)`
> Explicit replacement, without a failure or retry. Delete only a registered stage Job.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/stage_jobs.py:152`
### `resource_values(doc)`
> Extract container CPU/memory request and limit snapshots for retry evidence.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/stage_jobs.py:131 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/stage_jobs.py:210 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/stage_jobs.py:202`
### `resource_template(doc)`
> Pair resource snapshots with container names and images for compatible propagation.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/stage_jobs.py:132 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/stage_jobs.py:209`
### `propagate_resources(t, source)`
> Explicit resource_group asserts compatible templates; only raise CPU/memory in files.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/stage_jobs.py:217`
### `delete_stage_job(t, s, reason)`
> Save stage diagnostics before deleting its registered Job; return raw kubectl result.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/stage_jobs.py:184 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/stage_jobs.py:99 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/stage_jobs.py:259`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Uses state retry budgets, GPU dates and admission holds; no new CLI or policy settings. |

## Data Shapes
- Inputs: task/stage dictionaries and Kubernetes Job manifests. Resource snapshots are lists of container name plus requests/limits; templates add image.
- Outputs: submit/restart (ok, message), raw kubectl deletion result, bounded saved log text and outputs.json.

## Notes
- Fresh single-Job guards and diagnostics ordering retained. Uses deferred imports to avoid eager orchestration cycles.

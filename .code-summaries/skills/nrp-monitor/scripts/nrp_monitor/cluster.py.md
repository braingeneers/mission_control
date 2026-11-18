# cluster.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.cluster`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Kubernetes cluster query interface, kubectl subprocess wrapper, node health tracker, and namespace-wide pod utilization inspector. Imported by cli, ladder, legacy, red_alert, and s3; not run directly as a CLI.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.legacy` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.notify` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.red_alert` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.s3` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.shadow` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.sizing` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.stage_jobs` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.registry` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.tier0` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.timeouts` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `red_alert` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `util` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** **Shared data:** Calls kubectl CLI binary and nrp-util-check subprocess.
- **Shared data:** **Shared data:** Queries Thanos API over HTTP for cluster metrics.
- **Shared data:** **Shared data:** Imports state, notify, red_alert, util, wake, task.registry.

## Dependencies
None

## Classes
None

## Functions
### `pass_snapshot()`
> Context manager providing pass-scoped caching of Kubernetes pod/job queries.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:20`
### `_cached(key, read)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cluster.py:314 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/cluster.py:66 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:29`
### `kubectl(*args, timeout=120)`
> The only way the monitor runs kubectl. A call that changes a namespace drops that namespace from the pass snapshot.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cluster.py:107 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/cluster.py:123 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/cluster.py:150 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/cluster.py:309 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/cluster.py:49 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/cluster.py:71 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:37`
### `my_pods()`
> {name: owner_job_or_None} for the owner's pods that are Running, Pending or Failed (by annotation).
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:45`
### `jobs_in(ns)`
> {job: {state, start, deadline, ours}} for namespace `ns` (fetch_jobs), read once per pass. Raises RuntimeError like fetch_jobs.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:64`
### `job_state(name, ns)`
> 'ok' \| 'FAILED' \| 'running' \| 'pending' \| 'missing' \| 'error'
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:69`
### `job_complete(succeeded, completions, active, complete_cond)`
> A Job is finished successfully only when ALL its completions succeeded. `status.succeeded >= 1` is NOT that: an Indexed Job (pv3 --parallel N, completions=N) has succeeded >= 1 as soon as its first shard exits, while the other shards still run; treating that as success made the monitor check a root marker too early and delete the Job's pods (finch-feature-followup, 2026-11-06). Complete=True is authoritative; else succeeded >= spec.completions; …
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cluster.py:76 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/cluster.py:99 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:83`
### `classify_job(j)`
> Determines job status (ok, FAILED, running, pending) accounting for Indexed Job multi-shard completions.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cluster.py:113 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:95`
### `fetch_jobs(ns)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cluster.py:66 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:106`
### `apply_manifest(ns, path)`
> 'ok' \| 'blocked' \| error text. Server dry-run first.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:119`
### `pod_gpu_request(p)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cluster.py:174 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:134`
### `namespace_offenders(ns)`
> Every Running pod in `ns`, whoever launched it (no annotation filter), through nrp-util-check: the pods outside NRP's bands (rule nrp or gpu; a lab-floor-only flag is not counted by NRP's webhook) or stuck. Returns a list of dicts: pod, owner (Job or other ownerReference), username (nrp.ai/username annotation, may be ""), service_account, ours (annotation == our owner annotation), usage ({cpu\|mem\|gpu: use/request/pct}) and line (nrp-util-check…
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cluster.py:221 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/cluster.py:260 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:144`
### `offender_text(o)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cluster.py:201 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/cluster.py:203 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:181`
### `block_wake_text(n, stage, job, refusal, offenders, err)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cluster.py:226 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:189`
### `block_episode(n)`
> First block of a pending submit: run the namespace-wide check once, save it on t["pending"], write a digest line and wake the coordinator chat once (the task stays `blocked`, so the monitor goes on re-applying when the offenders clear). Later calls in the same episode do nothing. A failed check is logged and still produces the one wake, carrying the raw refusal.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cluster.py:253 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:209`
### `block_should_reapply(n)`
> True when the pending submit should be applied again this pass. Pods outside the bands explain the block: no re-apply until a re-check (at most every BLOCK_RECHECK_S) finds the set changed (or empty). No offenders or a failed check: the block is unexplained, so it goes on being applied each pass, as before, with the 6 h escalation as the fallback.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:247`
### `thanos_query(expr)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:277`
### `bad_nodes()`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cluster.py:304 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:287`
### `record_bad_node(node, why, fault=None)`
> Records faulty node in bad-nodes.json with 24-hour exclusion window.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:292`
### `bad_node_lines()`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:302`
### `job_pods(ns, job)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cluster.py:321 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:307`
### `pending_reason(t, s)`
> One line saying why the scheduler has not started a Pending Job: its PodScheduled message, plus the node restrictions in our own manifest (for example a GPU allow-list) when it reports nodes excluded by affinity/selector.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/cluster.py:317`

## Config / CLI
None

## Data Shapes
- my_pods return: {pod_name: owner_job_name_or_None} for Running/Pending/Failed user pods.
- fetch_jobs / jobs_in return: {job_name: {'state': 'ok'|'FAILED'|'running'|'pending', 'start': float?, 'deadline': int?, 'ours': bool}}.
- namespace_offenders return: list of dicts {'pod': str, 'owner': str, 'username': str, 'service_account': str, 'ours': bool, 'usage': dict, 'line': str}.
- bad_nodes return: {node_name: {'last_fault': float, 'expires': float, 'reason': str, 'fault': str?}}.

## Notes
- Implements pass-level caching (SNAPSHOT) for read-only kubectl calls, cleared automatically on mutating commands.
- Classifies Kubernetes Job completion strictly requiring all completions to succeed (job_complete), preventing premature cleanup of Indexed Jobs.
- Maintains bad node exclusion list in <state>/bad-nodes.json with 24-hour expiration.

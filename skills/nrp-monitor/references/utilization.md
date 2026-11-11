# Utilization

## The numbers

The shared numbers are the `nrp-cluster` skill's own (`references/utilization-policy.json`, section "Resource sizing and
utilization"): GPU utilization above 40% of the request on GPU jobs, limits within 20% of requests, at most 400 concurrent
jobs. The monitor checks the GPU floor and the job cap. The 20% limit rule is documented only: nothing here checks it.

`nrp-util-check --policy` prints the effective policy and says which keys come from the shared file and which from a local
override. A built-in copy of the shared file is the fallback (a test checks they are equal).

## Optional: local rules

A person or lab may add stricter rules without touching the shared file: `<state dir>/utilization-policy.local.json`
(default `~/.local/state/nrp-monitor/`; set `NRP_UTIL_POLICY_LOCAL` for another path). It is read after the shared file.
A key that is in neither file means that check is off, so with no local file only the GPU floor and the job cap apply.

| Key | Effect |
| --- | --- |
| `lab_floor` | flag CPU, memory or GPU used under this fraction of the request |
| `cpu_band`, `memory_band` | flag use outside `[low, high]` times the request |
| `small_pod_exempt` (`cpu`, `memory_bytes`) | pods at or below both skip the two bands (the floor still applies) |
| `account_block_after_violating_pods` | the summary counts the account's pods outside the bands and says when it passes this |
| `max_concurrent_jobs`, `gpu_floor`, `limit_to_request_tolerance` | may only be stricter than the shared value: a lower job cap or tolerance, a higher GPU floor |

A value that would loosen a shared number is ignored with a one-line warning. Example (the owner of the original machine uses
exactly this; copy `scripts/templates/utilization-policy.local.json.example`):

```json
{"max_concurrent_jobs": 40, "lab_floor": 0.4, "cpu_band": [0.2, 2.0], "memory_band": [0.2, 1.5],
 "small_pod_exempt": {"cpu": 1, "memory_bytes": 2000000000}, "account_block_after_violating_pods": 4}
```

About `small_pod_exempt`: NRP's policy page says only that its CPU and memory restrictions "do not apply to pods requesting 1 CPU core and 2GB memory". It does not say Gi, and does not say smaller requests are exempt. A pod requesting `2Gi` is 2,147,483,648 bytes, which is above the 2,000,000,000 in the example, so it would not count as exempt. If your NRP Violations page shows 1 CPU / 2Gi pods are not counted, set `memory_bytes` to 2147483648.

## The checker

`nrp-util-check PREFIX...` reads NRP's own metrics (thanos): requests from `kube_pod_container_resource_requests`, CPU from
`container_cpu_usage_seconds_total`, memory working set, GPU from `DCGM_FI_DEV_GPU_UTIL`, averaged over the last 10
minutes; kubectl only for pod state. One line per flagged pod plus a summary (it counts the account's violating pods only when the local rules ask for that).

Each flagged line ends `[tag] rule=R`: `gpu` (any GPU flag), `nrp` (a CPU or memory band that NRP counts as a violation)
or `lab` (only the lab floor flagged it; NRP does not count it). The monitor reads that token (an older line without it is
read from its tag).

## Running task observations

A LOW or HIGH utilization flag is an observation for the triage judge. It never fails a healthy running stage or
holds a task by itself. The judge returns only `CLOSE: reason` or `ESCALATE: diagnosis`; the fixer makes every change.
The roles use the runners chosen in each user's `agents.json`, including a single subscribed runner for both roles.

For memory LOW (NRP band: 20–150% of request), wait until each flagged pod is past ramp-up: 25% of the stage's
measured runtime, or 30 minutes when no measured history is available. A stage can record measured history as
`measured_runtime_seconds` in TASK.json; do not substitute its deadline for measured runtime.
Use each pod's whole-life Thanos peak, including earlier attempts, rather than the 10-minute mean. Set
`need = max(highest stage pod peak, every recorded OOMKilled attempt's limit)` and `right = ceil(need * 1.25)` Gi.
Requests at or below `1.2 * right` are sized correctly. Larger requests go to the fixer to update the manifest for
retries and later runs. Leave running work to finish unless more than two measured hours remain AND the stage is
resumable; the fixer may then delete and resubmit at the right size. If max/median peaks exceed 3 and low pods stayed
below 20% of request throughout their completed lives, ask the fixer to split inputs into size groups with separate memory.
Missing peaks or incomparable pods need explicit review, not a blind shrink.

Both roles receive per-pod peaks and ages, request and limit, OOM history, need, right size, spread and the script's
suggested verdict. The judge may disagree with the suggestion but must cite the numbers. It cannot edit files or run
state-changing task commands. Invalid replies escalate. The fixer alone edits manifests, resubmits or splits inputs.

Worked example: big-s requests 12Gi. A 1.2Gi mean at 17 minutes is ramp-up, so no event. Whole-life peaks of
4.5–7.7Gi and a recorded OOM at 6Gi give need 7.7Gi and right 10Gi. Since 12 <= 1.2*10, the request is sized correctly.
The peak range is only about 1.7x (max/median cannot exceed that range), so there is no split.

For legacy chains and standalone registrations, the existing strike handling remains separate.

## Historical util failure waivers

A healthy, I/O-bound Job can sit under the lab floor for hours; deleting it would lose work. The util fix agent may then end
with `UTIL_OK: <one paragraph of evidence>` (the Job is still running and progressing, the flag is utilization only, a
resubmit would lose work or break the task notes). **The script decides, not the agent.** It accepts the waiver only if all
hold:

1. the failure class is `util`;
2. the flag's rule is `lab`: never an NRP-band flag (those count toward NRP's account limit, so a waiver could cost a strike),
   never a GPU flag, and not a GPU stage; no recent flag on the task's pods came from an NRP band;
3. the Job exists and is Running when the script checks (the agent's claim is not used);
4. the task has used fewer than `util_waiver_max` waivers (default 3; `config.json` key or `NRP_MONITOR_UTIL_WAIVER_MAX`;
   0 turns waivers off).

If any check fails, nothing changes: the owner gets the usual stop, with the refusal reason in it and in the task's events.
When accepted, the failure is cleared, the stage goes back to running, no retry is used, nobody is messaged, and a record
`{job, pod, reason (at most 400 characters), at, until}` is kept on the task. `until` is now plus `util_waiver_hours` (default
6; `config.json` key or `NRP_MONITOR_UTIL_WAIVER_HOURS`). For that long, or until the Job ends or is resubmitted, the lab-floor
flag of that Job is not recorded again; NRP-band and GPU flags are never suppressed, and the account alarm is not affected. A
`util-waived` digest line and a task event record it, `task show NAME` lists the waivers (active or ended), and when the task
has a handoff a Fix log entry says so. After `until`, a Job that is still running and flagged again goes through the fix agent
again and may be waived again until the cap; then the owner is asked.

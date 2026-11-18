# util.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/util.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.util`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Routes utilization observations, lab-only waivers, reviews and bounded NRP band actions. Evidence and CPU sizing delegate to sizing; replacement and diagnostics-before-delete delegate to stage_jobs. Fresh job_state guards for waiver acceptance remain here.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cluster` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.legacy` — import consumer hint; not a proven runtime call.
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
- **Uses:** `stage_jobs` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `task_agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `timeouts` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** **Shared data:** Called by `advance_task` in `nrp_monitor.task.pass_` and `cmd_util_restart`.
- **Shared data:** **Shared data:** Queries Prometheus via `nrp_monitor.cluster.thanos_query` and `nrp_monitor.tier0.thanos_peak_mem`.
- **Shared data:** **Shared data:** Uses `nrp_monitor.task_agents` to run LLM triage or fixer agents when necessary.

## Dependencies
None

## Classes
None

## Functions
### `flag_rule(line)`
> Which rule flagged a pod: `gpu`, `nrp` (a CPU/memory band NRP counts) or `lab` (the lab floor only), from the `rule=` token that nrp-util-check ends its line with; a line without one (an older nrp-util-check) is read from its tag. `unknown` when neither says.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/util.py:146 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:8`
### `waiver_stage(t, w)`
> Finds the stage in a task corresponding to a waiver's Job name.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/util.py:29 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:22`
### `waiver_active(t, w)`
> A util waiver holds while it has not run out and the very Job it was given for still runs (a resubmit or a finished Job ends it).
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/util.py:38 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:26`
### `active_waiver(t, sid)`
> The live util waiver of stage `sid`'s Job, or None. Reads only what `util_waivers` holds, so a task written before waivers existed has none.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/util.py:147 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:33`
### `util_ok_extract(text)`
> The evidence text after the LAST `UTIL_OK:` line of a fix agent's answer (that line and the lines after it up to a blank line, HANDOFF_ENTRY or FOR_OWNER), whitespace collapsed, at most 400 characters; None when the answer has no such line.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:41`
### `util_waiver_check(t, f, claim)`
> (ok, why): whether the script accepts the fix agent's UTIL_OK. The script decides, never the agent's claim: the failure is class util; the flag came from the lab floor only (not an NRP band, not a GPU flag); the stage is not a GPU stage; the Job exists and is running now; the task still has waivers left.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/util.py:103 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:58`
### `util_waive(n, f, claim, a)`
> Accept the waiver: the stage goes back to running, the failure clears, no retry is used, nobody is messaged. Returns (ok, why).
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:95`
### `task_pod_flag(st, n, sid, pod, kind, line)`
> Utilization is a judge event, never a stage failure. STUCK remains an infrastructure failure.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:139`
### `process_util_event(n, a)`
> Coordinates agent triage and review for pending utilization events on running tasks.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:175`
### `util_nrp_review(n, t, event, context, numbers, a)`
> An NRP-floor observation: the fixer resizes/restarts, or (watch-only, or the fixer left the same Job running) the coordinator chat is woken visibly. Never closed as "no change".
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:211`
### `check_orphans(a, st)`
> the owner's running Jobs that no task, chain or registration covers go to the digest once.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:249`
### `utilization_band_action(n, sid, pod, line)`
> An NRP band flag always has a bounded lifetime, even for watch-only tasks.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/util.py:153 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/util.py:194 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/util.py:275`

## Config / CLI
None

## Data Shapes
- Evidence dict from `memory_low_evidence`: `{"peaks_gi": dict, "ages_seconds": dict, "request_gi": float, "limit_gi": float, "oom_limits_gi": list, "true_peak_gi": float, "need_gi": float, "right_gi": int, "spread": float, "suggested_verdict": str, "ramp_up": bool, ...}`.

## Notes
- Utilization flags are treated as judge events or warnings rather than task failures.
- Distinguishes between NRP account-level violations and lab-specific utilization rules.
- `utilization_restart` deletes and replaces running Kubernetes Jobs without consuming retry budget.

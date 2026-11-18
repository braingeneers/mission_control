# ladder.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.ladder`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Implements the tiered task failure escalation ladder (Tier 0 script rules, Tier 1 triage judge, Tier 2 fixer agent, Tier 2.5 deputy, Tier 3 coordinator chat, owner escalation) and stage observation loop. Imported by cli, legacy, task_pass; not run as a CLI.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.decisions` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.legacy` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.red_alert` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.stage_jobs` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_agents` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_commands` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.tier0` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.wake` — import consumer hint; not a proven runtime call.
- **Uses:** `agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plans` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `s3` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `stage_jobs` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `model` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `pass_` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `task_agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `timeouts` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `util` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** **Shared data:** Imports agents, cluster, decisions, notify, plans, s3, sizing, state, task_agents, timeouts, util, wake, task.model, task.pass_, task.registry.
- **Shared data:** **Shared data:** Invokes task_agents.run_task_agent for triage, fixer, and deputy agents.
- **Shared data:** Stage submission, resource snapshots/propagation or saved task diagnostics now resolve through stage_jobs; see call sites for the applicable operation.

## Dependencies
None

## Classes
None

## Functions
### `deputy_prompt(t, reason)`
> Constructs prompt for the pre-coordinator deputy agent with manifest editing and decision tools.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:166 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:13`
### `terminal_task(n, detail=None)`
> Late failures of done/cancelled tasks are audit-only, including queued work.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:157 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:236 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:268 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:426 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:476 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:54 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:66 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:78 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:31`
### `settled_outcome(n, line, a, kind)`
> Accept DONE/RESOLVED only when recovery passes the existing script checks.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:169 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:436 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:52`
### `task_fail(n, sid, cls, sig, detail, logs=None, extra=None)`
> Transactionally records a stage failure on a task and computes its fingerprint.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:295 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:297 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:305 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:309 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:318 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:76`
### `class_retries(t, f)`
> Every class budget belongs to its stage (a failure on one shard says nothing about the others). The task is guarded by max_retries and by `systemic_failure` (the same code/unknown signature on several stages).
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:373 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:98`
### `systemic_failure(t, f)`
> A reason string when the current code/unknown/outputs failure has the same signature as failures on other stages (one bug hitting the fan-out), else None. Environment failures (infra, resources, queue) never count: dead nodes are not a bug.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:380 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:105`
### `escalate(n, reason, a=None)`
> Escalates task to NEEDS_OWNER and sends a high-priority push notification.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:177 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:200 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:466 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:119`
### `coordinator_summary(t, reason)`
> The short text a Tier 3 wake carries: what happened, and where to look. No logs, no secrets.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:186 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:134`
### `to_coordinator(n, reason, a=None, deputy=True)`
> Tier 3: wake the task's coordinator chat (its webhook; same machinery as the done/failure wakes) with a short summary and pointers. The task goes to WITH_COORDINATOR, not NEEDS_OWNER: the owner is told only if the chat runs `task needs-owner`. With no webhook configured for the task there is nobody to wake, so the owner is told instead (NEEDS_OWNER) and nothing is lost. A wake that cannot be delivered (wake_failed) or an answer that never comes …
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:468 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:151`
### `check_coordinator_waits(a)`
> A WITH_COORDINATOR task whose wake was delivered but never answered for COORD_STALE_S goes to the owner.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:193`
### `triage_verdict(text)`
> (verdict, text) from the LAST verdict line of the judge's answer. Anything else fails closed to ESCALATE.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:203`
### `triage_wanted(t, f)`
> Tier 1 looks at an event when a benign answer is possible: the Job is still alive or finished, or the class is one the script cannot pin down (unknown, slow). A plain terminal failure the rules already classified (OOM, traceback, image pull) goes straight to Tier 2. Util observations always receive a judge before a fixer.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:404 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:211`
### `triage_prompt(t)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:407 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:220`
### `close_failure(n, f, why, kind='Tier 1 triage')`
> Close a triaged event as benign. The script decides, not the verdict: the Job must be alive or done, or the stage's outputs present. Returns (ok, refusal).
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:421 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:69 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:233`
### `observe_task(n, jobs)`
> Monitors running stages against cluster job states, saves logs, verifies S3 outputs, and registers failures.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:266`
### `guard(action)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:338 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:348 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:358 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:365 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:371 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:378 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:383 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:328`
### `postcheck_guard(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:339`
### `recorded_decision(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:344`
### `watch_only(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:349`
### `deadline_rule(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:353`
### `same_signature(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:359`
### `retry_cap(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:366`
### `class_budget(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:372`
### `systemic(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:379`
### `gpu_expired(c)`
> Checks if a stage's GPU request exceeds the owner's daily GPU approval date (`gpu_ok_until`).
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:384`
### `dry_run(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:389`
### `agents_wait(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:395`
### `triage_judge(c)`
> Tier 1 (config `ladder.triage_judge`, default off): a read-only judge, once per failure; 'no fix needed' closes the event.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:401`
### `fixer(c)`
> Tier 2: the fix agent. Anything it leaves unresolved goes to Tier 3, the coordinator chat.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:431`
### `act(c, d)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:487 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:464`
### `handle_failure(n, a)`
> The task escalation ladder (LADDER). Tier 0: script rules (classification in observe_task, deadline rules, `tier0_timeout`). Tier 1: read-only triage, where a benign answer is possible; 'no fix needed' CLOSES the event. Tier 2: the fixer. Tier 3: the task's coordinator chat (`to_coordinator`). The owner is told (NEEDS_OWNER + one DM) only by the chat (`task needs-owner`), or when a person's decision is the only way on (watch-only task, GPU appro…
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:471`

## Config / CLI
None

## Data Shapes
- Ladder pipeline SimpleNamespace: Namespace(n=task_name, a=args, t=task_dict, f=failure_dict).
- Decision tuple: Decision(action, reason) where action is in ('stop', 'coordinator', 'coordinator-only', 'owner').
- Task failure dict: {'stage': str, 'job': str, 'cls': str, 'sig': str, 'detail': str, 'logs': str?, 'ts': float, 'fingerprint': str, ...}.

## Notes
- LADDER sequence executes in strict order: postcheck guard -> recorded decision -> watch-only -> deadline rule -> repeat signature -> retry cap -> class budget -> systemic failure -> GPU expiration -> dry run -> agent wait -> triage judge -> fixer.
- Differentiates between recoverable failures and terminal states; ignores late failures on cancelled/done tasks (terminal_task).
- Tier 3 routes to coordinator chat webhook without notifying the owner unless escalation is explicitly requested.

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
- **Uses:** `sizing` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `model` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `pass_` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `task_agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `timeouts` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `util` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imports agents, cluster, decisions, notify, plans, s3, sizing, state, task_agents, timeouts, util, wake, task.model, task.pass_, task.registry.
- **Shared data:** Invokes task_agents.run_task_agent for triage, fixer, and deputy agents.

## Dependencies
None

## Classes
None

## Functions
### `deputy_prompt(t, reason)`
> Constructs prompt for the pre-coordinator deputy agent with manifest editing and decision tools.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:165 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:13`
### `terminal_task(n, detail=None)`
> Checks if task is already in terminal state (done/cancelled) and audits late failures.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:156 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:235 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:266 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:424 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:474 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:54 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:66 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:77 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:31`
### `settled_outcome(n, line, a, kind)`
> Validates and accepts RESOLVED/DONE verdicts from agents after verification.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:168 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:434 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:52`
### `task_fail(n, sid, cls, sig, detail, logs=None, extra=None)`
> Transactionally records a stage failure on a task and computes its fingerprint.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:293 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:295 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:303 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:307 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:316 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:76`
### `class_retries(t, f)`
> Counts attempts consumed by a specific failure class on a stage.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:371 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:97`
### `systemic_failure(t, f)`
> Detects if identical failure signature has appeared across multiple fan-out stages.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:378 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:104`
### `escalate(n, reason, a=None)`
> Escalates task to NEEDS_OWNER and sends a high-priority push notification.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:176 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:199 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:464 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:118`
### `coordinator_summary(t, reason)`
> The short text a Tier 3 wake carries: what happened, and where to look. No logs, no secrets.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:185 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:133`
### `to_coordinator(n, reason, a=None, deputy=True)`
> Escalates task to Tier 3 WITH_COORDINATOR, optionally running deputy agent first.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:466 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:150`
### `check_coordinator_waits(a)`
> A WITH_COORDINATOR task whose wake was delivered but never answered for COORD_STALE_S goes to the owner.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:192`
### `triage_verdict(text)`
> (verdict, text) from the LAST verdict line of the judge's answer. Anything else fails closed to ESCALATE.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:202`
### `triage_wanted(t, f)`
> Tier 1 looks at an event when a benign answer is possible: the Job is still alive or finished, or the class is one the script cannot pin down (unknown, slow). A plain terminal failure the rules already classified (OOM, traceback, image pull) goes straight to Tier 2. Util observations always receive a judge before a fixer.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:402 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:210`
### `triage_prompt(t)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:405 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:219`
### `close_failure(n, f, why, kind='Tier 1 triage')`
> Close a triaged event as benign. The script decides, not the verdict: the Job must be alive or done, or the stage's outputs present. Returns (ok, refusal).
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:419 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:69 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:232`
### `observe_task(n, jobs)`
> Monitors running stages against cluster job states, saves logs, verifies S3 outputs, and registers failures.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:265`
### `guard(action)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:336 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:346 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:356 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:363 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:369 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:376 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/ladder.py:381 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:326`
### `postcheck_guard(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:337`
### `recorded_decision(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:342`
### `watch_only(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:347`
### `deadline_rule(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:351`
### `same_signature(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:357`
### `retry_cap(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:364`
### `class_budget(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:370`
### `systemic(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:377`
### `gpu_expired(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:382`
### `dry_run(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:387`
### `agents_wait(c)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:393`
### `triage_judge(c)`
> Executes Tier 1 read-only agent to evaluate if failure can be closed as benign without changes.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:399`
### `fixer(c)`
> Executes Tier 2 fixer agent to repair manifests or code and resubmit.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:429`
### `act(c, d)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/ladder.py:485 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:462`
### `handle_failure(n, a)`
> Evaluates failure against LADDER steps and executes resulting action.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/ladder.py:469`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Owner setting deputy_enabled (default True): enables deputy agent before coordinator wake. |
| Owner setting ladder.triage_judge (default False): enables Tier 1 read-only judge before fixer. |
| Class retry budgets and systemic failure thresholds from state.CLASSES. |

## Data Shapes
- Ladder pipeline SimpleNamespace: Namespace(n=task_name, a=args, t=task_dict, f=failure_dict).
- Decision tuple: Decision(action, reason) where action is in ('stop', 'coordinator', 'coordinator-only', 'owner').
- Task failure dict: {'stage': str, 'job': str, 'cls': str, 'sig': str, 'detail': str, 'logs': str?, 'ts': float, 'fingerprint': str, ...}.

## Notes
- LADDER sequence executes in strict order: postcheck guard -> recorded decision -> watch-only -> deadline rule -> repeat signature -> retry cap -> class budget -> systemic failure -> GPU expiration -> dry run -> agent wait -> triage judge -> fixer.
- Differentiates between recoverable failures and terminal states; ignores late failures on cancelled/done tasks (terminal_task).
- Tier 3 routes to coordinator chat webhook without notifying the owner unless escalation is explicitly requested.

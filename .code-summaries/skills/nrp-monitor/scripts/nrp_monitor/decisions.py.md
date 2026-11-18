# decisions.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.decisions`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Manages deterministic failure fingerprinting, coordinator/deputy decision recording and replay, and LLM token/cost tracking ledger. Imported by ladder, task_agents, notify, and cli; exposes CLI subcommands decide, wake-review, and costs.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.agents` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli_args` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.continuation` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.notify` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.plan_wakes` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.stage_jobs` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.registry` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_agents` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_commands` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.tier0` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.timeouts` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.wake` — import consumer hint; not a proven runtime call.
- **Uses:** `ladder` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `s3` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `stage_jobs` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Shared data:** **Shared data:** Imports notify, s3, state, ladder, task.registry, task.pass_.
- **Shared data:** **Shared data:** Writes to <task_dir>/decisions.json and <state>/costs.jsonl.
- **Shared data:** Stage submission, resource snapshots/propagation or saved task diagnostics now resolve through stage_jobs; see call sites for the applicable operation.

## Dependencies
None

## Classes
None

## Functions
### `scaled_retry_cap(stages)`
> Calculates maximum allowable task retry cap scaled to total stage count.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py:13`
### `fingerprint(t, failure)`
> Generates 16-character hexadecimal hash fingerprint for a task failure signature.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/decisions.py:149 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/decisions.py:51 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py:17`
### `failure_context(t)`
> Formats failure fingerprint and recorded decisions for agent prompt injection.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py:49`
### `cost_event(task, kind, tier, outcome, stage=None, runner=None, model=None, result=None, **extra)`
> Appends an agent usage, token count, cost, or wake event row to costs.jsonl.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/decisions.py:176 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/decisions.py:192 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py:55`
### `cost_rows()`
> Reads and parses all historical cost and wake entries from costs.jsonl.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/decisions.py:189 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/decisions.py:196 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py:68`
### `decisions(n)`
> Loads recorded decisions for a specific task from its decisions.json file.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/decisions.py:101 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/decisions.py:150 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/decisions.py:167 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/decisions.py:52 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py:81`
### `postcheck_failure(f)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/decisions.py:146 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/decisions.py:99 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py:85`
### `record_decision(t, fp, action, why, scope='task', max_uses=None, who='coordinator')`
> Validates and persists a coordinator decision for a given failure fingerprint.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/decisions.py:185 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py:89`
### `_decide_escalate(n, t, f, fp, d, a)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py:112`
### `_decide_skip_reuse(n, t, f, fp, d, a)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py:118`
### `_decide_resubmit(n, t, f, fp, d, a)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py:130`
### `apply_decision(n, a)`
> Applies matching recorded decision to resubmit, skip_reuse, or escalate a failed stage.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py:138`
### `cmd_decide(a)`
> CLI handler for recording a decision against a task failure fingerprint.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py:182`
### `cmd_wake_review(a)`
> CLI handler for logging coordinator review reason on a task wake event.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py:188`
### `cmd_costs(a)`
> CLI handler aggregating and displaying agent costs, wake counts, and resolution rates.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/decisions.py:195`

## Config / CLI
None

## Data Shapes
- Decision entry in decisions.json: {'fingerprint': str, 'action': str, 'scope': 'stage'|'task', 'stage': str?, 'max_uses': int?, 'uses': int, 'who': str, 'why': str, 'ts': float}.
- Cost event row: {'ts': float, 'task': str, 'stage': str?, 'kind': str, 'tier': str, 'runner': str?, 'model': str?, 'cost_usd': float?, 'usage': dict?, 'outcome': str, ...}.

## Notes
- Failure fingerprinting normalizes error details, replaces numeric IDs/hashes, and hashes with container image/commands to produce stable 16-hex fingerprints.
- Guards against infinite decision loops using streak tracking against completed stage sets (DECISION_NO_PROGRESS_LIMIT).
- File locking via fcntl.flock ensures atomic appends to <state>/costs.jsonl.

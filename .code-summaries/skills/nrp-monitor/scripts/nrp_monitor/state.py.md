# state.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/state.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.state`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Central state definitions, path constants, failure class specifications, transaction locks, task persistence, and origin metadata schemas. Imported by virtually all nrp_monitor modules; not run as a CLI directly.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.agents` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cluster` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.config` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.continuation` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.decisions` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.legacy` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.notify` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.plan_commands` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.plan_wakes` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.plans` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.red_alert` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.s3` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.setup` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.sizing` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.model` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.registry` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_agents` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_commands` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.tier0` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.timeouts` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.wake` — import consumer hint; not a proven runtime call.
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plan_wakes` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Foundational module imported by all other nrp_monitor submodules.
- **Shared data:** Imports plan_wakes and notify lazily inside functions to avoid circular dependency cycles.

## Dependencies
None

## Classes
### ChainError(Exception)
> unclear — see source
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:277`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None

## Functions
### `default_state_dir()`
> ~/.local/state/nrp-monitor; only when that does not exist yet and a real old nrp-watchdog dir does (install.sh has not migrated it yet) is the old dir used, so a pass never splits its state in two.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/state.py:27 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:19`
### `_owner_cfg()`
> Who this installation works for: <state>/config.json, each key overridable by an environment variable. Keys: nrp_user_annotation (the nrp.ai/username annotation value on your pods, e.g. http://cilogon.org/serverE/users/NNNN), slack_user_id (the Slack user who gets the one DM), owner_label (label value on the monitor's own check Jobs), owner_name (how messages and agent prompts name you), skip_limit_fraction (optional; the share of skipped items …
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/state.py:45 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:30`
### `now()`
> Returns current POSIX timestamp.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/state.py:282 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/state.py:286 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/state.py:479 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:124`
### `log(msg)`
> Appends formatted message to monitor main execution log file.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/state.py:544 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:128`
### `load()`
> Reads legacy jobs.json tracking file.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:134`
### `save(d)`
> Atomically persists legacy jobs.json tracking file.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:148`
### `one_line(s, n)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:176`
### `slack_esc(s)`
> Slack mrkdwn escaping (https://api.slack.com/reference/surfaces/formatting#escaping): & < > only.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:180`
### `iso_at(t)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:228`
### `iso(ts=None)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/state.py:542 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/state.py:694 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:281`
### `ago(ts)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:285`
### `state_lock(timeout=60)`
> Context manager acquiring exclusive advisory lock on monitor state directory.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/state.py:468 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:291`
### `parse_ts(s)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:312`
### `failure_class(cls)`
> Looks up failure class definition, retry budget, and tier handling rules.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:396`
### `task_dir(n)`
> Returns path to state folder for a specific task.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/state.py:451 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/state.py:458 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:445`
### `task_load(n)`
> Loads task.json dictionary from disk for a task.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/state.py:469 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/state.py:554 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:449`
### `task_write(t)`
> Atomically writes task.json with restricted 0600 permissions.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/state.py:481 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:457`
### `task_txn(n, fn)`
> Executes callback inside state lock to safely modify and save task state with terminal wake hooks.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:466`
### `task_names()`
> Lists all task names currently present in the tasks state directory.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/state.py:553 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:485`
### `tev(t, msg)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:541`
### `tstage(t, sid)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:547`
### `task_of_job(job)`
> (task name, stage id) of a live task whose stage runs Job `job`.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:551`
### `norm_sig(s)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:562`
### `today_iso()`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:567`
### `heartbeat_age()`
> Calculates seconds since last monitor heartbeat write.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:685`
### `write_heartbeat(text)`
> Writes current timestamp and status summary to heartbeat file.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/state.py:692`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env NRP_MONITOR_STATE: root directory for monitor state files (defaults to ~/.nrp-monitor). |
| Env NRP_MONITOR_WORK: working directory for agent runs and scratch data (defaults to ~/.nrp-monitor/work). |
| Env NRP_MONITOR_USER_ANNOTATION: pod annotation identifying owner (defaults to config.json or os.environ). |
| Failure class definitions in CLASSES specifying retry budgets and tier rules. |

## Data Shapes
- Task state dict (task.json): {name: str, status: str, stages: [dict], namespace: str, max_retries: int, attempts: [dict], failure: dict?, origin: dict?, on_done: dict?, ...}.
- Origin dict: {title: str, link: str, assistant: str, collaborator: str, harness: t3|claude|codex, session: str, cwd: str, ...}.
- Failure record schema: {stage: str, job: str, cls: str, sig: str, detail: str, fingerprint: str, ...}.

## Notes
- Implements global file locking (state_lock()) using fcntl.flock on <state>/monitor.lock to guarantee multi-process concurrency safety.
- Provides transactional task modification via task_txn(name, callback) which writes via temp file and atomic rename.
- Defines strict limits on code snapshots, handoff document lengths, and retry caps.
- Maintains failure classification rules across 8 failure classes: resources, infra, code, unknown, outputs, util, queue, slow.

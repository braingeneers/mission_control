# shadow.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/shadow.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.shadow`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Isolation and side-effect containment engine for shadow monitor passes. Provides isolated_pass context manager which enforces fail-closed IO via a Python audit hook (sys.addaudithook), monkey-patches mutating subprocesses (kubectl, aws), restricts HTTP requests to Thanos GET endpoints, skips agent dispatch and notifications via GATES, and records all attempted actions and decisions to shadow-actions.jsonl. Imported by cli.py during run --shadow.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Uses:** `agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `stage_jobs` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `pass_` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `task_agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imported by `skills.nrp-monitor.scripts.nrp_monitor.cli` when `--shadow` flag is passed.
- **Shared data:** Patches functions in `agents`, `cluster`, `notify`, `red_alert`, `s3`, `stage_jobs`, `task.pass_`, `task_agents`, and `wake`.

## Dependencies
None

## Classes
None

## Functions
### `record(would_do, **details)`
> Appends an attempted action or observation record to shadow-actions.jsonl within the active isolated directory.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/shadow.py:149 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/shadow.py:170 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/shadow.py:179 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/shadow.py:188 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/shadow.py:196 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/shadow.py:209 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/shadow.py:221 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/shadow.py:225 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/shadow.py:49 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/shadow.py:52 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/shadow.py:67 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/shadow.py:28`
### `_audit(event, args)`
> Python audit hook intercepting open, remove, chmod, spawn, and process creation events, forbidding writes outside the isolated state directory.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/shadow.py:34`
### `_kubectl_verb(argv)`
> Extracts the verb command from a kubectl argument list, ignoring leading namespace flags.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/shadow.py:149 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/shadow.py:150 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/shadow.py:97 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/shadow.py:76`
### `_aws_op(argv)`
> Extracts the operation tuple (e.g., ('s3api', 'head-object')) from aws CLI argument lists.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/shadow.py:99 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/shadow.py:84`
### `_read_command(argv)`
> Verifies whether a command vector is a permitted read-only kubectl or aws command.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/shadow.py:144 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/shadow.py:51 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/shadow.py:92`
### `isolated_pass()`
> Context manager establishing audit hooks, temporary directory overrides, and mock gates to execute a monitor pass in complete isolation.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/cli.py:70 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/shadow.py:123`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Base isolation directory `/private/tmp/claude-501/nrp-shadow`. |
| Requires `NRP_MONITOR_STATE` to reside strictly below isolation base dir. |
| `GATES` table: mock implementations skipping outbound actions for agents, notifications, webhooks, admission probes, and incluster jobs. |
| `state.THANOS_URL`: only allowed HTTP target. |

## Data Shapes
- Writes JSON lines to `<isolated_state>/shadow-actions.jsonl`: `{'would_do': str, 'task': str, 'stage': str, 'time': str, ...details}`.

## Notes
- Registers a global audit hook via `sys.addaudithook(_audit)` to intercept file writes, deletions, directory creations, and unauthorized process spawning outside `_ACTIVE`.
- Resolves file descriptors on macOS (`fcntl.fcntl(dir_fd, 50, ...)`) to properly audit relative `shutil.rmtree` calls.
- Permitted subprocesses are strictly read-only (`kubectl get|describe|logs|top`, `aws s3api head-object`, `aws s3 ls`).
- Intercepts kubectl delete calls in observe_task to capture `mark_done` decisions before suppression.

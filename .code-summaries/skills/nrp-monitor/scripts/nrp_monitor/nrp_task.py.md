# nrp_task.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/nrp_task.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Scoped nrp-task command handler for task agents: validates task identity and role before inspect, reship, commit, submit, delete, plan and report actions. Argparse options come from cli_args; submit/replacement and saved diagnostics delegate to stage_jobs. Existing positional command dispatch stays here.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli_args` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_commands` — import consumer hint; not a proven runtime call.
- **Uses:** `agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `cli_args` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `config` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `ladder` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plans` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `s3` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `stage_jobs` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `pass_` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `registry` from `skills.nrp-monitor.scripts.nrp_monitor.task` — imports (static evidence).
- **Uses:** `task_commands` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `timeouts` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** **Shared data:** Imports s3, config, task_commands, util, cluster, decisions, task_pass, task_registry, plans, timeouts, ladder.
- **Shared data:** **Shared data:** Invoked directly by sub-agent shells as nrp-task.

## Dependencies
None

## Classes
None

## Functions
### `reship_dirs(code)`
> (primary package dir, [extra package dirs]) that `nrp-task reship` packs: everything the task's code declares. Primary = code.pkg_dir, else code.subdir when it is the predictor_v3 folder, else <clone>/predictor_v3. Extras = code.extra_pkg_dirs (relative = inside the clone, absolute = another checkout read in place). Raises ChainError when something declared is missing.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/nrp_task.py:204 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/nrp_task.py:21`
### `cmd_tool(a)`
> Primary command dispatcher for all nrp-task operations (show, logs, describe, util, s3, reship, commit, submit, delete, plan, next-add, report).
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/nrp_task.py:44`

## Config / CLI
None

## Data Shapes
- Code tarball: generated .tgz archive containing package files and extra package directories.
- Report status: string in (RESUBMITTED, STOPPED, DONE, UTIL_OK) for fixers, or (CONTINUED, WAITING, NOT-DONE, STOPPED) for continue agents.
- S3 copy limit: exact object copies bounded to maximum 256 KiB (256 * 1024 bytes).

## Notes
- Role enforcement: if NRP_MONITOR_AGENT_ROLE == triage, mutations are blocked (only show, logs, describe, util, s3 allowed).
- Pre-commit safety check: compiles changed python files using py_compile before creating git commits.
- Code reshipping: re-packs predictor_v3 code and extra packages via codeship.build, uploads tarball to S3, and updates task spec.
- Scoped S3 copy: enforces plan may_touch boundaries and 256 KiB size limits for artifacts copied into task directories.

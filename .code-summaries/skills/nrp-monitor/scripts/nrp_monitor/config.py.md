# config.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/config.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.config`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Configuration loader and environment extractor for NRP monitor policies, GPU floors, concurrent job limits, utilization waivers, and AWS environment settings. Imported across nrp_monitor modules; not run as a CLI.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.legacy` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.s3` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.registry` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_agents` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_commands` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.tier0` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
- **Uses:** `agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imports state and agents.
- **Shared data:** Reads policy defined in sibling tool nrp-util-check.

## Dependencies
None

## Classes
None

## Functions
### `util_policy()`
> Loads effective utilization policy from sibling nrp-util-check or defaults.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/config.py:32 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/config.py:41 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/config.py:6`
### `gpu_floor()`
> Returns effective GPU utilization floor fraction (default 0.40).
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/config.py:29`
### `max_jobs()`
> Computes cap on concurrent unfinished Jobs applying policy and env var overrides.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/config.py:37`
### `_skip_limit()`
> Computes skip fraction threshold for batch task items.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/config.py:64 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/config.py:49`
### `skip_limit_text()`
> Formats skip limit fraction as percentage string.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/config.py:63`
### `util_waiver_max()`
> Returns maximum allowed utilization waivers per task.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/config.py:67`
### `util_waiver_hours()`
> Returns duration in hours for one utilization waiver.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/config.py:82`
### `aws_env()`
> Constructs clean environment dictionary preserving AWS configuration variables.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/config.py:106 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/config.py:96`
### `step_env(s)`
> Constructs step execution environment merging AWS environment with step-specific env.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/config.py:105`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env NRP_MONITOR_MAX_JOBS: overrides max concurrent jobs limit. |
| Env NRP_MONITOR_SKIP_LIMIT_FRACTION: fraction threshold for single-item skips before escalating (default 0.05). |
| Env NRP_MONITOR_UTIL_WAIVER_MAX: maximum utilization waivers allowed per task (default 3). |
| Env NRP_MONITOR_UTIL_WAIVER_HOURS: duration in hours for which a utilization waiver suppresses lab-floor flags (default 6.0). |
| Env AWS credentials/config: AWS_PROFILE, AWS_CONFIG_FILE, AWS_SHARED_CREDENTIALS_FILE, AWS_DEFAULT_REGION. |

## Data Shapes
- util_policy() returns dict of policy values loaded dynamically from sibling nrp-util-check.
- aws_env() and step_env(s) return sanitized environment dicts with injected AWS variables and PATH.

## Notes
- Dynamically loads utilization policy from sibling script ../nrp-util-check via importlib.
- Caches policy in state._UTIL to avoid repeated dynamic imports.
- Uses localized module imports inside functions to avoid circular import cycles with state and agents.

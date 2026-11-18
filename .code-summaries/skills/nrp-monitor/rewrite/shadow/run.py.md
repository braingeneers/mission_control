# run.py

**Path:** `skills/nrp-monitor/rewrite/shadow/run.py`
**Module:** `skills.nrp-monitor.rewrite.shadow.run`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Standalone shadow pass runner and report generator. Clones the live monitor state directory into a disposable /private/tmp location, runs an isolated read-only pass via nrp-monitor run --shadow, records decisions, compares them against installed events via compare.py, and renders markdown comparison reports or multi-run day summaries. Run from CLI directly.

## Connections
- **Uses:** `installed_events` from `skills.nrp-monitor.rewrite.shadow.compare` — imports (static evidence).
- **Uses:** `judge` from `skills.nrp-monitor.rewrite.shadow.compare` — imports (static evidence).
- **Uses:** `shadow_decisions` from `skills.nrp-monitor.rewrite.shadow.compare` — imports (static evidence).
- **Shared data:** Imports `installed_events`, `shadow_decisions`, `judge` from `compare.py`.
- **Shared data:** Executes `scripts/nrp-monitor run --shadow` via subprocess.

## Dependencies
None

## Classes
None

## Functions
### `tasks(root)`
> Loads all task.json records from the given state root directory.
> **Called by:** skills/nrp-monitor/rewrite/shadow/run.py:138 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/rewrite/shadow/run.py:23`
### `refresh(source, dest)`
> Sanitizes and copies state directories and JSON/log files from source to isolated destination, rewriting absolute paths.
> **Called by:** skills/nrp-monitor/rewrite/shadow/run.py:137 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/rewrite/shadow/run.py:27`
### `interval(source)`
> Determines pass interval in seconds from config.json or launchd plist StartInterval.
> **Called by:** skills/nrp-monitor/rewrite/shadow/run.py:136 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/rewrite/shadow/run.py:51`
### `save(path, data)`
> Atomic JSON file writer using temporary file swap.
> **Called by:** skills/nrp-monitor/rewrite/shadow/run.py:162 (named-call hint); skills/nrp-monitor/rewrite/shadow/run.py:75 (named-call hint); skills/nrp-monitor/rewrite/shadow/run.py:78 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/rewrite/shadow/run.py:60`
### `resolve_pending(source)`
> Re-evaluates pending shadow rows in previous results against the latest installed monitor log.
> **Called by:** skills/nrp-monitor/rewrite/shadow/run.py:111 (named-call hint); skills/nrp-monitor/rewrite/shadow/run.py:164 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/rewrite/shadow/run.py:66`
### `render(result)`
> Generates formatted Markdown report summarizing comparison verdicts, routes, provisional actions, and filesystem blocks.
> **Called by:** skills/nrp-monitor/rewrite/shadow/run.py:163 (named-call hint); skills/nrp-monitor/rewrite/shadow/run.py:76 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/rewrite/shadow/run.py:81`
### `main()`
> CLI entry point parsing --report and --day-summary, running isolated shadow passes, and managing results.
> **Called by:** skills/nrp-monitor/rewrite/shadow/run.py:170 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/rewrite/shadow/run.py:103`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| CLI `--report PATH`: path to output markdown report file (must remain below rewrite/shadow/runs/). |
| CLI `--day-summary SINCE`: aggregate persisted runs since local ISO timestamp. |
| Env `NRP_MONITOR_STATE`: set to isolated temporary directory during pass execution. |
| Path `~/.local/state/nrp-monitor`: default source monitor state directory. |
| Path `/private/tmp/claude-501/nrp-shadow`: base directory for isolated pass directories. |

## Data Shapes
- Result JSON (`result-<timestamp>.json`): contains start/deadline timestamps, interval, tasks dict, rows, route counts, provisional events, filesystem block list, and error counts.
- Pending JSON (`pending.json`): list of rows still pending resolution.
- Markdown report: tables of first shadow decision vs installed evidence, verdict counts, route counts, provisional events, and filesystem blocks.

## Notes
- Copies tasks, plans, approved, resume, templates, webhooks while omitting symlinks, git, work, and backup directories.
- Resolves pending decisions across prior passes before executing a new pass.
- Relocates absolute state paths inside JSON/YAML/log files to point to the isolated copy.

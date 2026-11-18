# compare.py

**Path:** `skills/nrp-monitor/rewrite/shadow/compare.py`
**Module:** `skills.nrp-monitor.rewrite.shadow.compare`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Pure decision extraction, action categorization, and delayed comparison module for shadow monitoring. Parses monitor logs and shadow action journals to categorize decisions, associates messages with task stages, identifies first suppressed side effects, and judges shadow verdicts against installed execution events. Imported by rewrite/shadow/run.py.

## Connections
- **Used by:** `skills.nrp-monitor.rewrite.shadow.run` — import consumer hint; not a proven runtime call.
- **Shared data:** Imported by `rewrite/shadow/run.py`.

## Dependencies
None

## Classes
None

## Functions
### `category(message)`
> Classifies a monitor log message string into a canonical decision category (e.g., safety_stop, wait, restart, submit, fix_agent, utilization_review, mark_failed, mark_done, coordinator).
> **Called by:** skills/nrp-monitor/rewrite/shadow/compare.py:50 (named-call hint); skills/nrp-monitor/rewrite/shadow/compare.py:79 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/rewrite/shadow/compare.py:5`
### `stage_for(message, task, context=None)`
> Resolves which stage ID of a task a log message pertains to, matching stage IDs, job names, or falling back to single active stage or context.
> **Called by:** skills/nrp-monitor/rewrite/shadow/compare.py:44 (named-call hint); skills/nrp-monitor/rewrite/shadow/compare.py:80 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/rewrite/shadow/compare.py:27`
### `installed_events(lines, tasks)`
> Parses monitor log lines to extract ordered real decision events for registered tasks.
> **Called by:** skills/nrp-monitor/rewrite/shadow/run.py:152 (named-call hint); skills/nrp-monitor/rewrite/shadow/run.py:72 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/rewrite/shadow/compare.py:35`
### `shadow_decisions(actions, tasks)`
> Extracts the first shadow decision per task/stage from recorded actions, marking events after the first side-effect suppression as provisional.
> **Called by:** skills/nrp-monitor/rewrite/shadow/run.py:149 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/rewrite/shadow/compare.py:64`
### `judge(row, events, now)`
> Compares a shadow decision row against real installed log events within a time window, returning matched, unexplained, pending, or unknown.
> **Called by:** skills/nrp-monitor/rewrite/shadow/run.py:153 (named-call hint); skills/nrp-monitor/rewrite/shadow/run.py:73 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/rewrite/shadow/compare.py:102`

## Config / CLI
None

## Data Shapes
- installed_events return: list of event dicts `[{'time': str, 'task': str, 'stage': str, 'category': str, 'evidence': str}]`.
- shadow_decisions return: `(rows, provisional)` tuple where rows is a list of decision dicts per task stage and provisional lists actions occurring after the first suppressed effect.
- judge return: row dict with `verdict` ('matched', 'unexplained', 'pending', or 'unknown') and `installed` evidence string.

## Notes
- Pure logic; does not compare final state on disk.
- Suppresses subsequent events on a task once a side-effect is blocked (`cut` set) to avoid misattribution.
- Handles in-flight agents at snapshot time as valid matches.

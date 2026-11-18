# notify.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.notify`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Notification router, Slack DM dispatcher, Claude push notification sender, macOS banner fallback, and periodic/daily digest renderer. Imported across nrp_monitor; exposes CLI subcommand digest.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.agents` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cluster` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.continuation` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.decisions` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.legacy` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.plan_commands` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.plan_wakes` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.plans` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.red_alert` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.setup` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.state` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.registry` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_agents` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.tier0` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.timeouts` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.wake` — import consumer hint; not a proven runtime call.
- **Uses:** `agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plan_commands` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plans` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Makes HTTPS calls to Braingeneers Slack gateway.
- **Shared data:** Executes headless claude CLI for push notifications and osascript for desktop banners.
- **Shared data:** Imports state, agents, cluster, decisions, plan_commands, plans, wake.

## Dependencies
None

## Classes
None

## Functions
### `notify(msg, state=None, key=None, dry=False, ref='-')`
> Emits silent notification event logged to digest.log with deduplication.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:10`
### `read_json(p, default)`
> Safely reads and parses JSON file returning fallback default on error.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:110 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/notify.py:134 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:26`
### `write_json(p, d)`
> Atomically writes dictionary to JSON file via temporary file replacement.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:114 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/notify.py:136 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:33`
### `digest(kind, msg, task='-')`
> Appends structured JSON log entry to digest.log.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:120 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/notify.py:23 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:39`
### `slack_dm(text)`
> Sends direct message to configured Slack user via authenticated HTTP request.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:124 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:49`
### `claude_push(msg)`
> Sends proactive mobile push notification via headless Claude PushNotification tool.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:124 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:69`
### `banner(msg, title='NRP: needs you')`
> Displays native macOS desktop banner notification using AppleScript osascript.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:122 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/notify.py:126 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:86`
### `push(msg, key, dry=False, refs=None)`
> Primary interruption alert: sends Slack DM, Claude push, or OS banner with deduplication tracking.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:260 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:95`
### `push_clear(key)`
> Re-arms a push deduplication key once its alarm condition has cleared.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:130`
### `jwt_days_left()`
> Calculates remaining validity days for Braingeneers Slack JWT token.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:235 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:139`
### `needs_owner()`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:194 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:150`
### `coordinating()`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:202 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:160`
### `ref_label(ref)`
> 'task-name · origin title' for digest lines (looked up now, so a backfilled origin also labels old events).
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:234 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:165`
### `render_digest(hours)`
> Formats multi-section markdown summary of recent cluster, task, plan, and node events.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:242 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/notify.py:256 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:175`
### `cmd_digest(a)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:241`
### `daily_digest(a)`
> Generates and saves daily digest markdown file and sends morning reminder if plans wait on owner.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:246`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env NRP_MONITOR_SLACK_URL: endpoint for Braingeneers Slack notification service. |
| Env NRP_MONITOR_SLACK_USER: user ID for direct messages. |
| Env NRP_MONITOR_JWT: path to Braingeneers JWT credentials (default ~/.ssh/braingeneers_jwt_token.json). |
| File <state>/pushed.json: tracks deduplication keys for push alerts. |

## Data Shapes
- Digest log entry in digest.log: JSON line {'t': iso_str, 'kind': str, 'task': str, 'msg': str}.
- Pushed notifications entry in pushed.json: {key: {'t': iso_str, 'msg': str, 'origin': [str]}}.

## Notes
- Two-tier notification philosophy: routine operational events are silent (digest only); push() is the single interruption channel.
- push() attempts Slack DM first, then headless Claude push notification, falling back to macOS osascript banner only if both fail.
- Deduplicates push notifications using unique keys in pushed.json; cleared via push_clear when conditions resolve.

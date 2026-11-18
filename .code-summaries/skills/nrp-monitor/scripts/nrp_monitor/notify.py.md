# notify.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.notify`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Routes silent digest events and one-time owner pushes through Slack, Claude push and banner fallback. Push claims and rearming use state.json_txn; JSON reading and atomic writing retain their existing formats and patch targets. Renders current task/plan state into digest text.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.agents` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli_args` — import consumer hint; not a proven runtime call.
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
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.stage_jobs` — import consumer hint; not a proven runtime call.
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
- **Shared data:** **Shared data:** Makes HTTPS calls to Braingeneers Slack gateway.
- **Shared data:** **Shared data:** Executes headless claude CLI for push notifications and osascript for desktop banners.
- **Shared data:** **Shared data:** Imports state, agents, cluster, decisions, plan_commands, plans, wake.

## Dependencies
None

## Classes
None

## Functions
### `notify(msg, state=None, key=None, dry=False, ref='-')`
> v2 (owner decision 2026-11-05): routine events are SILENT and go to the digest; push() is the one interruption. With key, repeats within NOTIFY_DEDUPE_S are dropped. `ref` names the owning registration for the digest.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:10`
### `read_json(p, default)`
> Safely reads and parses JSON file returning fallback default on error.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:113 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/notify.py:137 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:26`
### `write_json(p, d)`
> Atomically writes dictionary to JSON file via temporary file replacement.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:114 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/notify.py:138 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:33`
### `digest(kind, msg, task='-')`
> Silent record for the digest (`nrp-monitor digest`, daily file, SessionStart line).
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:121 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/notify.py:23 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:39`
### `slack_dm(text)`
> Send `text` (already composed and escaped by slack_text) as the owner's DM.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:125 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:49`
### `claude_push(msg)`
> PushNotification from a headless agent: reaches the owner's phone when a Remote Control session is open.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:125 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:69`
### `banner(msg, title='NRP: needs you')`
> Displays native macOS desktop banner notification using AppleScript osascript.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:123 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/notify.py:127 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:86`
### `push(msg, key, dry=False, refs=None)`
> The ONE interruption: Slack DM to the owner + Claude push; a macOS banner only when both fail. Once per key. `refs` = the registrations the alert is about ('task:NAME', 'chain:NAME', 'job:NAME'); their origin chat is named first in every channel. No refs = a shared/system alert that no single chat owns.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:262 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:95`
### `push_clear(key)`
> Re-arm a push key once its condition has cleared (account alarm, kubectl failing).
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:131`
### `jwt_days_left()`
> Calculates remaining validity days for Braingeneers Slack JWT token.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:237 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:141`
### `needs_owner()`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:196 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:152`
### `coordinating()`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:204 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:162`
### `ref_label(ref)`
> 'task-name · origin title' for digest lines (looked up now, so a backfilled origin also labels old events).
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:236 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:167`
### `render_digest(hours)`
> Formats multi-section markdown summary of recent cluster, task, plan, and node events.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/notify.py:244 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/notify.py:258 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:177`
### `cmd_digest(a)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:243`
### `daily_digest(a)`
> Generates and saves daily digest markdown file and sends morning reminder if plans wait on owner.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/notify.py:248`

## Config / CLI
None

## Data Shapes
- Digest log entry in digest.log: JSON line {'t': iso_str, 'kind': str, 'task': str, 'msg': str}.
- Pushed notifications entry in pushed.json: {key: {'t': iso_str, 'msg': str, 'origin': [str]}}.

## Notes
- Two-tier notification philosophy: routine operational events are silent (digest only); push() is the single interruption channel.
- push() attempts Slack DM first, then headless Claude push notification, falling back to macOS osascript banner only if both fail.
- Deduplicates push notifications using unique keys in pushed.json; cleared via push_clear when conditions resolve.

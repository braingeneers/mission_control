# red_alert.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/red_alert.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.red_alert`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Account-wide RED ALERT monitor that probes NRP admission webhooks via server dry-run jobs and holds all task submissions across namespaces whenever NRP refuses new pods due to low utilization or quota. Imported by cli, cluster; not run directly as a CLI.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cluster` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.stage_jobs` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `ladder` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imports notify, state, cluster, ladder, wake.
- **Shared data:** Calls kubectl and nrp-util-check via cluster.

## Dependencies
None

## Classes
None

## Functions
### `red_alert()`
> Returns the currently active red alert dictionary or empty dict if none active.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/red_alert.py:101 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/red_alert.py:121 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/red_alert.py:99 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/red_alert.py:7`
### `red_alert_enter(ns, msg, source)`
> Enters active RED ALERT state, records refusal details, and logs critical event.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/red_alert.py:118 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/red_alert.py:14`
### `red_probe(ns)`
> Executes server dry-run create of probe job to test NRP admission webhook response.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/red_alert.py:108 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/red_alert.py:31`
### `red_alert_text(cur, n, mine, unknown)`
> Constructs comprehensive alert message detailing low pods and mandatory resizing rules.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/red_alert.py:77 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/red_alert.py:43`
### `red_alert_notify(cur)`
> Identifies offending pods, wakes coordinator chats for owning tasks, and pushes high-priority DM.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/red_alert.py:126 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/red_alert.py:57`
### `process_red_alert(a, st)`
> Main driver run on each pass: tests admission probes, enters/clears alert, and triggers notifications.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/red_alert.py:94`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Constant RED_PROBE_S (600s): interval between dry-run probe tests per namespace. |
| Constant RED_REUSE_S (3600s): reuse window preserving alert ID across flapping refusals. |
| File <state>/red_alert.json: tracks active alert, probe timestamps, and notified owners. |

## Data Shapes
- Red alert state dict: {active: {id: str, since: float, ns: str, source: str, refusal: str, woken: [str], notified: bool, offenders: [str]?}, probed: {ns: float}, last: dict?}.
- Probe job manifest: minimal batch/v1 Job running busybox with true command requesting 100m CPU and 64Mi memory.

## Notes
- All cluster task submissions are held globally while a RED ALERT is active.
- Probes NRP admission using kubectl create --dry-run=server so no actual pods are scheduled.
- When an alert occurs, inspects namespace offenders, maps offending pods to owning tasks, wakes their coordinator chats, and sends an urgent push to Hunter.

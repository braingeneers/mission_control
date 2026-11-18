# dashboard_helpers.py

**Path:** `experiment-dash/dashboard_helpers.py`
**Module:** `experiment-dash.dashboard_helpers`
**Feature Area:** `experiment-dash`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Helper library for the telemetry experiment dashboard, constructing MQTT topic strings and publishing commands (start, end, ping, pause, resume, stop, sched) to Braingeneers IoT devices.

## Connections
- **Used by:** `experiment-dash.experiment-plotly-app` — import consumer hint; not a proven runtime call.
- **Shared data:** Imported by `experiment-dash/experiment-plotly-app.py`.
- **Shared data:** Publishes to MQTT broker consumed by IoT microcontrollers and `logging-s3/log.py`.

## Dependencies
- `braingeneers.iot.messaging` — external or unresolved local import; source import evidence.
- `braingeneers.utils.smart_open_braingeneers` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
### `generate_topic(uuid, device='', cmnd='', message_type='')`
> Constructs standard telemetry MQTT topic string.
> **Called by:** experiment-dash/dashboard_helpers.py:24 (named-call hint); experiment-dash/dashboard_helpers.py:33 (named-call hint). **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:16`
### `send_message(uuid, device, message, cmnd='', message_type='', online=True)`
> Publishes MQTT message via MessageBroker or returns tuple in offline mode.
> **Called by:** experiment-dash/dashboard_helpers.py:126 (named-call hint); experiment-dash/dashboard_helpers.py:47 (named-call hint); experiment-dash/dashboard_helpers.py:52 (named-call hint); experiment-dash/dashboard_helpers.py:57 (named-call hint); experiment-dash/dashboard_helpers.py:62 (named-call hint); experiment-dash/dashboard_helpers.py:67 (named-call hint); experiment-dash/dashboard_helpers.py:72 (named-call hint); experiment-dash/dashboard_helpers.py:82 (named-call hint); experiment-dash/dashboard_helpers.py:96 (named-call hint). **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:22`
### `start(uuid, device, online=True)`
> Sends start run command to target device.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:31`
### `end(uuid, device, online=True)`
> Sends end experiment command to target device.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:44`
### `ping(uuid, device, online=True)`
> Sends ping heartbeat check to target device.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:49`
### `status(uuid, device, online=True)`
> Requests device status update.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:54`
### `pause(uuid, device, seconds, online=True)`
> Send pause command
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:59`
### `resume(uuid, device, online=True)`
> Send resume command
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:64`
### `stop(uuid, device, online=True)`
> Send stop command
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:69`
### `sched_clear(uuid, device, tag, online=True)`
> Clear scheduled tasks
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:74`
### `sched_add(uuid, device, interval, schedule_time, at, command_value, run_once_value, online=True)`
> Transmits cron/interval schedule definition to device.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:84`
### `command(uuid, device, command_value, online=True)`
> Send custom command for a single teammate Args: uuid (str): Experiment UUID device (str): Teammate device command_value (str): JSON string containing command (handles various quote types) online (bool): Whether to send message or return data
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:98`
### `send_to_all_teammates(uuid, teammates, command_func, *args, online=True)`
> Broadcasts command across a list of device IDs.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:129`
### `create_uuid(experiment_type, experiment_name)`
> Create a UUID for an experiment
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:138`
### `check_uuid_format(uuid_string)`
> Validate UUID format
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:143`
### `s3_basepath(UUID)`
> Get S3 base path for experiment type
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/dashboard_helpers.py:148`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Global `ROOT_TOPIC = 'telemetry'` |
| Global `logging_token = 'log'` |

## Data Shapes
- MQTT message: JSON payload containing command name, timestamp, device name, and optional schedules.
- MQTT topic: `telemetry/{uuid}/log/{device}/{cmnd}/{message_type}`.

## Notes
- Initializes global `messaging.MessageBroker` with UUID client ID.
- Provides offline mode returning `(topic, message)` tuples without publishing.

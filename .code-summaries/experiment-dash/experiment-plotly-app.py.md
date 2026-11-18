# experiment-plotly-app.py

**Path:** `experiment-dash/experiment-plotly-app.py`
**Module:** `experiment-dash.experiment-plotly-app`
**Feature Area:** `experiment-dash`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Plotly Dash interactive web application for monitoring and controlling wet lab organoid experiments, device telemetry, status checks, and scheduling.

## Connections
- **Uses:** `*` from `experiment-dash.dashboard_helpers` — imports (static evidence).
- **Shared data:** Imports command helpers from `dashboard_helpers.py`.
- **Shared data:** Uses styles defined in `experiment-dash/assets/style.css`.

## Dependencies
- `dash` — external or unresolved local import; source import evidence.
- `dash.Input` — external or unresolved local import; source import evidence.
- `dash.Output` — external or unresolved local import; source import evidence.
- `dash.State` — external or unresolved local import; source import evidence.
- `dash.dcc` — external or unresolved local import; source import evidence.
- `dash.dependencies.ALL` — external or unresolved local import; source import evidence.
- `dash.html` — external or unresolved local import; source import evidence.
- `requests` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
### `load_json()`
> Loads local experiment state JSON file.
> **Called by:** experiment-dash/experiment-plotly-app.py:77 (named-call hint). **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:40`
### `update_output(n_clicks, value)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `experiment-dash/experiment-plotly-app.py:315`
### `toggle_collapse(n)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:355`
### `populate_device_checklist(value)`
> Populates UI checkboxes for active devices in current experiment.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:370`
### `update_device_states(selected_devices, n_intervals)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:397`
### `update_output(n_clicks, uuid_value)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:429`
### `handle_start_end_button(clicks, selected_devices, uuid_value)`
> Dispatches start/stop commands on button click.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:446`
### `handle_end_button(clicks, selected_devices, uuid_value)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:459`
### `handle_ping_button(clicks, selected_devices, uuid_value)`
> Pings selected lab devices via dashboard helpers.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:473`
### `handle_status_button(clicks, selected_devices, uuid_value)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:487`
### `handle_pause_button(clicks, selected_devices, uuid_value, seconds_value)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:503`
### `handle_resume_button(clicks, selected_devices, uuid_value)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:518`
### `handle_stop_button(clicks, selected_devices, uuid_value)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:532`
### `handle_sched_clear_button(clicks, selected_devices, uuid_value, tag)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:549`
### `handle_sched_add_button(clicks, selected_devices, uuid_value, interval_value, schdule_time_value, at_value, command_value, run_once_value)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:568`
### `handle_command_button(clicks, selected_devices, uuid_value, command_value)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:583`
### `update_time(n)`
> Updates live experiment duration clock in dashboard header.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:595`
### `update_value(selected_value)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `experiment-dash/experiment-plotly-app.py:606`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env `EXPERIMENT_UUID`: Target experiment session UUID. |
| `app.run_server(debug=True, host='0.0.0.0', port=8050)` |

## Data Shapes
- Input: User UI interaction (buttons, inputs, checklist) and JSON device status feeds.
- Output: Dash DOM components, telemetry graphs, and outbound MQTT control commands.

## Notes
- Contains interactive Dash callbacks for device checklists, collapsible panels, and scheduling triggers.

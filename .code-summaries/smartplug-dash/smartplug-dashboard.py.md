# smartplug-dashboard.py

**Path:** `smartplug-dash/smartplug-dashboard.py`
**Module:** `smartplug-dash.smartplug-dashboard`
**Feature Area:** `smartplug-dash`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Streamlit dashboard application for discovering, monitoring, and toggling power state of Tasmota smart plugs connected to the Braingeneers laboratory MQTT network.

## Connections
- **Shared data:** Uses `braingeneers.iot.messaging.MessageBroker` to communicate with smart plug microcontrollers.

## Dependencies
- `braingeneers.iot.*` — external or unresolved local import; source import evidence.
- `braingeneers.iot.messaging` — external or unresolved local import; source import evidence.
- `streamlit` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
### `toggle_smartplugs(action)`
> Publishes MQTT POWER command to toggle a selected smart plug relay.
> **Called by:** smartplug-dash/smartplug-dashboard.py:74 (named-call hint); smartplug-dash/smartplug-dashboard.py:77 (named-call hint); smartplug-dash/smartplug-dashboard.py:80 (named-call hint). **Side effects:** unclear — see source.
**Source:** `smartplug-dash/smartplug-dashboard.py:41`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Run via `streamlit run smartplug-dashboard.py` |
| MQTT Discovery Topic: `smartplug/telemetry/+/stat/RESULT` |
| MQTT Command Topic: `smartplug/telemetry/tasmotas/cmnd/POWER` |

## Data Shapes
- Input: Tasmota MQTT telemetry status JSON payloads (`{"POWER": "ON"}`).
- Output: Streamlit UI switches and MQTT command messages.

## Notes
- Dispatches MQTT broadcast power query on startup to populate active smartplug inventory.
- Maintains device lists and MQTT client in `st.session_state`.

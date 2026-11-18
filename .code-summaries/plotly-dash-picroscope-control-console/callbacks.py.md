# callbacks.py

**Path:** `plotly-dash-picroscope-control-console/callbacks.py`
**Module:** `plotly-dash-picroscope-control-console.callbacks`
**Feature Area:** `plotly-dash-picroscope-control-console`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Defines core Dash UI callbacks and database interactions for the Picroscope console, managing GitHub repository issue creation, MQTT message publishing, and device shadow queries.

## Connections
- **Used by:** `plotly-dash-picroscope-control-console.app` — import consumer hint; not a proven runtime call.
- **Used by:** `plotly-dash-picroscope-control-console.app_elements.experiment_panel` — import consumer hint; not a proven runtime call.
- **Used by:** `plotly-dash-picroscope-control-console.app_elements.imaging_panel` — import consumer hint; not a proven runtime call.
- **Uses:** `*` from `plotly-dash-picroscope-control-console.Experiment_Metadata_SQL` — imports (static evidence).
- **Shared data:** Imported by `plotly-dash-picroscope-control-console/app.py`.
- **Shared data:** Uses `braingeneers.iot.shadows` and `braingeneers.iot.messaging`.

## Dependencies
- `braingeneers.iot.messaging` — external or unresolved local import; source import evidence.
- `braingeneers.iot.shadows` — external or unresolved local import; source import evidence.
- `dash.dependencies.Input` — external or unresolved local import; source import evidence.
- `dash.dependencies.Output` — external or unresolved local import; source import evidence.
- `dash.dependencies.State` — external or unresolved local import; source import evidence.
- `dash.html` — external or unresolved local import; source import evidence.
- `dotenv.load_dotenv` — external or unresolved local import; source import evidence.
- `github.Github` — external or unresolved local import; source import evidence.
- `pytz` — external or unresolved local import; source import evidence.
- `users.PISCOPE_BOT_TOKEN` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
### `get_callbacks(app)`
> Registers all primary control console Dash callbacks onto the Dash application instance.
> **Called by:** plotly-dash-picroscope-control-console/app.py:39 (named-call hint). **Side effects:** unclear — see source.
**Source:** `plotly-dash-picroscope-control-console/callbacks.py:38`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env `SHADOWS_ENDPOINT`: Override URL for Braingeneers shadows API service. |
| Env `SHADOWS_API_KEY`: API key for shadows database access. |
| Import `PISCOPE_BOT_TOKEN`: GitHub bot personal access token for creating issues in `braingeneers/internal`. |

## Data Shapes
- Input: Dash UI events (`Input`, `State`), MQTT sensor events.
- Output: Dash DOM mutations (`Output`), GitHub issue creations, and MQTT commands to microscope hardware.

## Notes
- Initializes `shadows.DatabaseInteractor` and `messaging.MessageBroker`.
- Creates automated GitHub issues on experiment lifecycle changes.

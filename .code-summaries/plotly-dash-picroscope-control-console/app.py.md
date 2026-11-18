# app.py

**Path:** `plotly-dash-picroscope-control-console/app.py`
**Module:** `plotly-dash-picroscope-control-console.app`
**Feature Area:** `plotly-dash-picroscope-control-console`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Main web application server for the Picroscope microscope control console, assembling Dash tabs for experiment controls, imaging parameters, and livestream feeds.

## Connections
- **Uses:** `experiment_panel` from `plotly-dash-picroscope-control-console.app_elements` — imports (static evidence).
- **Uses:** `imaging_panel` from `plotly-dash-picroscope-control-console.app_elements` — imports (static evidence).
- **Uses:** `livestream_panel` from `plotly-dash-picroscope-control-console.app_elements` — imports (static evidence).
- **Uses:** `db_interactor` from `plotly-dash-picroscope-control-console.callbacks` — imports (static evidence).
- **Uses:** `get_callbacks` from `plotly-dash-picroscope-control-console.callbacks` — imports (static evidence).
- **Shared data:** Imports `get_callbacks` from `callbacks.py`.
- **Shared data:** Imports panels from `app_elements/experiment_panel.py`, `imaging_panel.py`, and `livestream_panel.py`.

## Dependencies
- `dash.dcc` — external or unresolved local import; source import evidence.
- `dash.exceptions` — external or unresolved local import; source import evidence.
- `dash.html` — external or unresolved local import; source import evidence.
- `dash_auth` — external or unresolved local import; source import evidence.
- `dash_bootstrap_components` — external or unresolved local import; source import evidence.
- `numpy` — external or unresolved local import; source import evidence.
- `plotly.graph_objects` — external or unresolved local import; source import evidence.
- `plotly.subplots` — external or unresolved local import; source import evidence.
- `users.PISCOPE_BOT_TOKEN` — external or unresolved local import; source import evidence.
- `users.USERNAME_PASSWORD_PAIRS` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
None

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env `BASE_PATH`: Base URL path prefix (default: `/picroscope/`). |
| `app.run_server(debug=True, host='0.0.0.0', port=8050)` |

## Data Shapes
- Input: User interface tab clicks and control adjustments.
- Output: Multi-panel Dash web interface layout.

## Notes
- Uses Dash Bootstrap Components (`dbc.themes.BOOTSTRAP`).
- Registers callbacks across multiple panel modules.

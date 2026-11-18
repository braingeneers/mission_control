# experiment_panel.py

**Path:** `plotly-dash-picroscope-control-console/app_elements/experiment_panel.py`
**Module:** `plotly-dash-picroscope-control-console.app_elements.experiment_panel`
**Feature Area:** `plotly-dash-picroscope-control-console`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Defines the experiment setup and metadata management UI tab layout for the Picroscope console, including forms for researchers, organoid lines, and imaging schedules.

## Connections
- **Used by:** `plotly-dash-picroscope-control-console.app` — import consumer hint; not a proven runtime call.
- **Uses:** `*` from `plotly-dash-picroscope-control-console.callbacks` — imports (static evidence).
- **Shared data:** Imported by `plotly-dash-picroscope-control-console/app.py`.
- **Shared data:** Interacts with `callbacks.py` for database mutations.

## Dependencies
- `dash.dcc` — external or unresolved local import; source import evidence.
- `dash.exceptions` — external or unresolved local import; source import evidence.
- `dash.html` — external or unresolved local import; source import evidence.
- `dash_auth` — external or unresolved local import; source import evidence.
- `dash_bootstrap_components` — external or unresolved local import; source import evidence.
- `numpy` — external or unresolved local import; source import evidence.
- `plotly.graph_objects` — external or unresolved local import; source import evidence.
- `plotly.subplots` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
### `get_callbacks(app)`
> Registers experiment form validation and submission callbacks with Dash app.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `plotly-dash-picroscope-control-console/app_elements/experiment_panel.py:137`

## Config / CLI
None

## Data Shapes
- Dash component layout: `EXPERIMENT_PANEL` (dcc.Tab containing Bootstrap rows, form inputs, dropdowns, buttons).

## Notes
- Includes callbacks for validating experiment parameters and dispatching experiment start signals.

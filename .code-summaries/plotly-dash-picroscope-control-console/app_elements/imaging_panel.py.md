# imaging_panel.py

**Path:** `plotly-dash-picroscope-control-console/app_elements/imaging_panel.py`
**Module:** `plotly-dash-picroscope-control-console.app_elements.imaging_panel`
**Feature Area:** `plotly-dash-picroscope-control-console`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Defines the camera exposure, focus, stage position, and multi-well plate imaging parameter control panel UI tab for the Picroscope console.

## Connections
- **Used by:** `plotly-dash-picroscope-control-console.app` — import consumer hint; not a proven runtime call.
- **Uses:** `db_interactor` from `plotly-dash-picroscope-control-console.callbacks` — imports (static evidence).
- **Shared data:** Imported by `plotly-dash-picroscope-control-console/app.py`.

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
None

## Config / CLI
None

## Data Shapes
- Dash component layout: `IMAGING_PANEL` (dcc.Tab containing camera gain, exposure, illumination, and step sliders).

## Notes
- Provides UI inputs for XY stage movement, Z-stack parameters, and LED illumination channels.

# livestream_panel.py

**Path:** `plotly-dash-picroscope-control-console/app_elements/livestream_panel.py`
**Module:** `plotly-dash-picroscope-control-console.app_elements.livestream_panel`
**Feature Area:** `plotly-dash-picroscope-control-console`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Defines the real-time optical livestream viewer tab for the Picroscope console, embedding video streams and current capture previews from active microscopes.

## Connections
- **Used by:** `plotly-dash-picroscope-control-console.app` — import consumer hint; not a proven runtime call.
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
- Dash component layout: `LIVESTREAM_PANEL` (dcc.Tab embedding HTML video elements and stream reload intervals).

## Notes
- Embeds direct MJPEG or WebRTC video feed from Raspberry Pi / Picroscope device.

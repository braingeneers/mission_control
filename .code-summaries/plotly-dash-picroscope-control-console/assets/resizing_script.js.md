# resizing_script.js

**Path:** `plotly-dash-picroscope-control-console/assets/resizing_script.js`
**Module:** `plotly-dash-picroscope-control-console.assets.resizing_script`
**Feature Area:** `plotly-dash-picroscope-control-console`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Clientside JavaScript callback helper for the Picroscope Dash console, triggering window resize events after a timeout to force responsive Plotly charts to recalculate dimensions.

## Connections
- **Shared data:** Executed clientside in browser by Dash via `window.dash_clientside.clientside.resize`.

## Dependencies
None

## Classes
None

## Functions
### `resize(value)`
> Dispatches synthetic window resize event to trigger Plotly graph auto-scaling.
**Source:** `plotly-dash-picroscope-control-console/assets/resizing_script.js:5`

## Config / CLI
None

## Data Shapes
None

## Notes
- Fires a synthetic `window.resize` event 500ms after tab switching or container resizing.

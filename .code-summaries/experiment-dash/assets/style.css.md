# style.css

**Path:** `experiment-dash/assets/style.css`
**Module:** `experiment-dash.assets.style`
**Feature Area:** `experiment-dash`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Custom stylesheet for the experiment telemetry Plotly Dash application, styling container layout, cards, and hiding Dash debug menus.

## Connections
- **Shared data:** Loaded automatically by Dash for `experiment-dash/experiment-plotly-app.py`.

## Dependencies
None

## Classes
None

## Functions
### `.dash-debug-menu { visibility: hidden !important; }`
> Suppresses default Dash debug banner and toolbar.
**Source:** `experiment-dash/assets/style.css:5`
### `body > div.container`
> Sets standard padding and Arial typography for the experiment dashboard container.
**Source:** `experiment-dash/assets/style.css:13`

## Config / CLI
None

## Data Shapes
None

## Notes
- Hides `.dash-debug-menu` and sets 100px padding on body container.

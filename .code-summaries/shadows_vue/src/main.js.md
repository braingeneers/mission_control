# main.js

**Path:** `shadows_vue/src/main.js`
**Module:** `shadows_vue.src.main`
**Feature Area:** `shadows_vue`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Application bootstrap entry point for the Shadows Vue web client, installing BootstrapVue, VueRouter, VueEllipseProgress, VueLuxon plugins and mounting `App.vue`.

## Connections
- **Shared data:** Imports router from `./router`.
- **Shared data:** Mounts root Vue instance onto `#app` in `public/index.html`.

## Dependencies
None

## Classes
None

## Functions
### `new Vue({ router, render: h => h(App) }).$mount('#app')`
> Creates and mounts root Vue instance.
**Source:** `shadows_vue/src/main.js:40`

## Config / CLI
None

## Data Shapes
None

## Notes
- Imports global Bootstrap CSS, BootstrapVue CSS, and local Tailwind CSS stylesheets.

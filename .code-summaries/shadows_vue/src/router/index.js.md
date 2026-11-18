# index.js

**Path:** `shadows_vue/src/router/index.js`
**Module:** `shadows_vue.src.router.index`
**Feature Area:** `shadows_vue`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Vue Router configuration for the Shadows web application, establishing client routes for Plates, Wells, Experiments, Devices, Search Results, and Auth0 login redirects with navigation guards.

## Connections
- **Shared data:** Imports views from `../views/`.
- **Shared data:** Imports `authGuard` from `../auth/authGuard`.

## Dependencies
None

## Classes
None

## Functions
### `const routes = [...]`
> Array of route configurations mapping URL paths to view components.
**Source:** `shadows_vue/src/router/index.js:13`
### `const router = new VueRouter({ mode: 'history', routes })`
> Configures and exports VueRouter instance.
**Source:** `shadows_vue/src/router/index.js:220`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| `mode: 'history'` |
| `base: process.env.BASE_URL` |

## Data Shapes
- Route definitions mapping paths (`/`, `/plates`, `/wells`, `/experiments`, `/devices`, `/search`) to page view components.

## Notes
- Enforces `authGuard` on protected routes requiring authenticated user session.

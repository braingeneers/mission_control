# auth0-plugin.js

**Path:** `shadows_vue/src/auth/auth0-plugin.js`
**Module:** `shadows_vue.src.auth.auth0-plugin`
**Feature Area:** `shadows_vue`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Vue.js authentication wrapper plugin around `@auth0/auth0-spa-js`, managing user authentication state, login redirect/popup flows, token retrieval, and route guards.

## Connections
- **Shared data:** Imported by `shadows_vue/src/main.js` and `shadows_vue/src/router/index.js`.

## Dependencies
None

## Classes
None

## Functions
### `useAuth0(options)`
> Creates or retrieves singleton Auth0 Vue plugin instance.
**Source:** `shadows_vue/src/auth/auth0-plugin.js:15`
### `loginWithRedirect(options)`
> Redirects browser to Auth0 universal login page.
**Source:** `shadows_vue/src/auth/auth0-plugin.js:45`
### `getIdTokenClaims(options)`
> Fetches decoded claims from current Auth0 ID token.
**Source:** `shadows_vue/src/auth/auth0-plugin.js:65`
### `getTokenSilently(options)`
> Fetches fresh access token in background using iframe or refresh token.
**Source:** `shadows_vue/src/auth/auth0-plugin.js:75`
### `logout(options)`
> Logs user out and clears Auth0 session cookies.
**Source:** `shadows_vue/src/auth/auth0-plugin.js:85`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Options: `domain`, `clientId`, `audience`, `redirectUri`. |

## Data Shapes
- Reactive state: `{ loading: bool, isAuthenticated: bool, user: object, auth0Client: object, popupOpen: bool, error: any }`.

## Notes
- Provides `useAuth0` composable and installs `$auth` prototype onto global Vue instance.

# middlewares.js

**Path:** `strapi-shadows-db/config/middlewares.js`
**Module:** `strapi-shadows-db.config.middlewares`
**Feature Area:** `strapi-shadows-db`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Strapi middleware pipeline array configuring error handling, security headers, CORS, request logging, query parsing, body parsing, and session state.

## Connections
- **Shared data:** Loaded on Strapi server boot to assemble Koa middleware stack.

## Dependencies
None

## Classes
None

## Functions
### `module.exports = [...]`
> Exports Strapi HTTP middleware stack array.
**Source:** `strapi-shadows-db/config/middlewares.js:1`

## Config / CLI
None

## Data Shapes
- Array of middleware identifiers: `strapi::errors`, `strapi::security`, `strapi::cors`, `strapi::logger`, `strapi::query`, `strapi::body`, `strapi::session`, `strapi::favicon`.

## Notes
- Controls HTTP pipeline execution order for all inbound Strapi requests.

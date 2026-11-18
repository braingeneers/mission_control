# index.js

**Path:** `strapi-shadows-db/src/index.js`
**Module:** `strapi-shadows-db.src.index`
**Feature Area:** `strapi-shadows-db`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Strapi application lifecycle root module providing extension lifecycle hooks (`register` and `bootstrap`) called during server startup.

## Connections
- **Shared data:** Invoked by Strapi core during application initialization and boot.

## Dependencies
None

## Classes
None

## Functions
### `register({ strapi })`
> Asynchronous extension hook executed before server initialization.
**Source:** `strapi-shadows-db/src/index.js:10`
### `bootstrap({ strapi })`
> Asynchronous hook executed before server starts listening.
**Source:** `strapi-shadows-db/src/index.js:18`

## Config / CLI
None

## Data Shapes
None

## Notes
- Lifecycle entry point for registering custom Strapi service extensions, hooks, and startup jobs.

# well.js

**Path:** `strapi-shadows-db/src/api/well/controllers/well.js`
**Module:** `strapi-shadows-db.src.api.well.controllers.well`
**Feature Area:** `strapi-shadows-db`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Strapi core controller for the Well content type, handling HTTP requests for individual plate wells (position, media, organoid contents).

## Connections
- **Shared data:** Dispatches to `services/well.js`.
- **Shared data:** Routed via `routes/well.js`.

## Dependencies
None

## Classes
None

## Functions
### `createCoreController('api::well.well')`
> Creates default Strapi CRUD controller for plate wells.
**Source:** `strapi-shadows-db/src/api/well/controllers/well.js:9`

## Config / CLI
None

## Data Shapes
- REST endpoints: `GET /api/wells`, `POST /api/wells`, `GET /api/wells/:id`, `PUT /api/wells/:id`.

## Notes
- Instantiated via `createCoreController('api::well.well')`.

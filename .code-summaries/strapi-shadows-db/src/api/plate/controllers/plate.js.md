# plate.js

**Path:** `strapi-shadows-db/src/api/plate/controllers/plate.js`
**Module:** `strapi-shadows-db.src.api.plate.controllers.plate`
**Feature Area:** `strapi-shadows-db`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Strapi core controller for the Plate content type, handling HTTP requests for multi-well experimental cell culture plates.

## Connections
- **Shared data:** Dispatches to `services/plate.js`.
- **Shared data:** Routed via `routes/plate.js`.

## Dependencies
None

## Classes
None

## Functions
### `createCoreController('api::plate.plate')`
> Creates default Strapi CRUD controller for plates.
**Source:** `strapi-shadows-db/src/api/plate/controllers/plate.js:9`

## Config / CLI
None

## Data Shapes
- REST endpoints: `GET /api/plates`, `POST /api/plates`, `GET /api/plates/:id`, `PUT /api/plates/:id`.

## Notes
- Instantiated via `createCoreController('api::plate.plate')`.

# interaction-thing.js

**Path:** `strapi-shadows-db/src/api/interaction-thing/controllers/interaction-thing.js`
**Module:** `strapi-shadows-db.src.api.interaction-thing.controllers.interaction-thing`
**Feature Area:** `strapi-shadows-db`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Strapi core controller for the Interaction Thing content type, handling CRUD operations for IoT laboratory hardware interaction targets.

## Connections
- **Shared data:** Dispatches to `services/interaction-thing.js`.
- **Shared data:** Routed via `routes/interaction-thing.js`.

## Dependencies
None

## Classes
None

## Functions
### `createCoreController('api::interaction-thing.interaction-thing')`
> Creates default Strapi CRUD controller for interaction things.
**Source:** `strapi-shadows-db/src/api/interaction-thing/controllers/interaction-thing.js:9`

## Config / CLI
None

## Data Shapes
- REST endpoints: `GET /api/interaction-things`, `POST /api/interaction-things`, `GET /api/interaction-things/:id`, `PUT /api/interaction-things/:id`.

## Notes
- Instantiated via `createCoreController('api::interaction-thing.interaction-thing')`.

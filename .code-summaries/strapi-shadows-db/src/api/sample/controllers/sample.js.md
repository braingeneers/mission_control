# sample.js

**Path:** `strapi-shadows-db/src/api/sample/controllers/sample.js`
**Module:** `strapi-shadows-db.src.api.sample.controllers.sample`
**Feature Area:** `strapi-shadows-db`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Strapi core controller for the Sample content type, handling HTTP requests for biological organoid cell samples.

## Connections
- **Shared data:** Dispatches to `services/sample.js`.
- **Shared data:** Routed via `routes/sample.js`.

## Dependencies
None

## Classes
None

## Functions
### `createCoreController('api::sample.sample')`
> Creates default Strapi CRUD controller for biological samples.
**Source:** `strapi-shadows-db/src/api/sample/controllers/sample.js:9`

## Config / CLI
None

## Data Shapes
- REST endpoints: `GET /api/samples`, `POST /api/samples`, `GET /api/samples/:id`, `PUT /api/samples/:id`.

## Notes
- Instantiated via `createCoreController('api::sample.sample')`.

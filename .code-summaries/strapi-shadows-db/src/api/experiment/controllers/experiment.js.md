# experiment.js

**Path:** `strapi-shadows-db/src/api/experiment/controllers/experiment.js`
**Module:** `strapi-shadows-db.src.api.experiment.controllers.experiment`
**Feature Area:** `strapi-shadows-db`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Strapi core controller for the Experiment content type generated via `@strapi/strapi` factories, handling CRUD HTTP requests for laboratory experiments.

## Connections
- **Shared data:** Dispatches to `services/experiment.js`.
- **Shared data:** Routed via `routes/experiment.js`.

## Dependencies
None

## Classes
None

## Functions
### `createCoreController('api::experiment.experiment')`
> Creates default Strapi CRUD controller for experiments.
**Source:** `strapi-shadows-db/src/api/experiment/controllers/experiment.js:9`

## Config / CLI
None

## Data Shapes
- REST endpoints: `GET /api/experiments`, `POST /api/experiments`, `GET /api/experiments/:id`, `PUT /api/experiments/:id`, `DELETE /api/experiments/:id`.

## Notes
- Instantiated via `createCoreController('api::experiment.experiment')`.

# plugins.js

**Path:** `strapi-shadows-db/config/plugins.js`
**Module:** `strapi-shadows-db.config.plugins`
**Feature Area:** `strapi-shadows-db`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Strapi plugin configuration enabling fuzzy search integration across laboratory data models (experiments, plates, samples, and wells).

## Connections
- **Shared data:** Integrates search across Strapi API models consumed by `shadows_vue`.

## Dependencies
None

## Classes
None

## Functions
### `module.exports = ({ env }) => ({ 'fuzzy-search': { ... } })`
> Exports plugin configuration object for fuzzy search.
**Source:** `strapi-shadows-db/config/plugins.js:1`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Configures `fuzzy-search` plugin across content types: `api::experiment.experiment`, `api::plate.plate`, `api::sample.sample`, `api::well.well`. |

## Data Shapes
- Mapping of indexed fields per model (name, description, label, etc.).

## Notes
- Enables fuzzy search indexing so users can search across organoid samples and experimental plates.

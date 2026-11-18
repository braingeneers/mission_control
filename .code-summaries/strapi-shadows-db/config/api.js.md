# api.js

**Path:** `strapi-shadows-db/config/api.js`
**Module:** `strapi-shadows-db.config.api`
**Feature Area:** `strapi-shadows-db`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Strapi REST API pagination and query configuration setting default and maximum record limits to 100 with total count inclusion.

## Connections
- **Shared data:** Configures global REST endpoints in Strapi.

## Dependencies
None

## Classes
None

## Functions
### `module.exports = { rest: { defaultLimit: 100, maxLimit: 100, withCount: true } }`
> Exports default REST API pagination limits.
**Source:** `strapi-shadows-db/config/api.js:1`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| `rest.defaultLimit = 100` |
| `rest.maxLimit = 100` |
| `rest.withCount = true` |

## Data Shapes
None

## Notes
- Ensures API consumers receive total pagination counts and caps batch queries at 100 items.

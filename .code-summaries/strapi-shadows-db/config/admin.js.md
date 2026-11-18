# admin.js

**Path:** `strapi-shadows-db/config/admin.js`
**Module:** `strapi-shadows-db.config.admin`
**Feature Area:** `strapi-shadows-db`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Strapi admin panel authentication configuration loading administrator JWT signing secret and API token salt from environment variables.

## Connections
- **Shared data:** Configures Strapi admin security subsystem.

## Dependencies
None

## Classes
None

## Functions
### `module.exports = ({ env }) => ({ auth: { secret: ... }, apiToken: { salt: ... } })`
> Exports Strapi administrator authentication and token configuration.
**Source:** `strapi-shadows-db/config/admin.js:1`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env `ADMIN_JWT_SECRET`: Secret used to sign admin session JWTs. |
| Env `API_TOKEN_SALT`: Salt used to generate Strapi API tokens. |

## Data Shapes
None

## Notes
- Standard Strapi admin configuration function.

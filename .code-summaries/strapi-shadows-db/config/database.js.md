# database.js

**Path:** `strapi-shadows-db/config/database.js`
**Module:** `strapi-shadows-db.config.database`
**Feature Area:** `strapi-shadows-db`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Strapi database client configuration setting SQLite as the connection engine and resolving database file path from environment variables.

## Connections
- **Shared data:** Initializes database connection for Strapi ORM.

## Dependencies
None

## Classes
None

## Functions
### `module.exports = ({ env }) => ({ connection: { client: 'sqlite', ... } })`
> Exports SQLite database connection parameters.
**Source:** `strapi-shadows-db/config/database.js:3`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env `DATABASE_FILENAME`: Path to SQLite database file (default: `.tmp/data.db`). |

## Data Shapes
None

## Notes
- Configures sqlite client with `useNullAsDefault: true`.

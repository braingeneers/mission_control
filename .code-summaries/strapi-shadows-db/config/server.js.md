# server.js

**Path:** `strapi-shadows-db/config/server.js`
**Module:** `strapi-shadows-db.config.server`
**Feature Area:** `strapi-shadows-db`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Strapi HTTP server configuration defining host, port, external public URL (`https://shadows-db.braingeneers.gi.ucsc.edu/`), proxy trust, and session secret keys.

## Connections
- **Shared data:** Configures core Koa HTTP server for Strapi CMS.

## Dependencies
None

## Classes
None

## Functions
### `module.exports = ({ env }) => ({ host: ..., port: ..., url: ... })`
> Exports server network and security binding configuration.
**Source:** `strapi-shadows-db/config/server.js:1`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env `HOST`: Server bind address (default: `0.0.0.0`). |
| Env `PORT`: Server port (default: `1337`). |
| Env `APP_KEYS`: Array of secret keys for cookie and session signing. |
| Public URL: `https://shadows-db.braingeneers.gi.ucsc.edu/` |
| `proxy: true` |

## Data Shapes
None

## Notes
- Configures public routes to optionally bypass authorization headers.
- Enables proxy header forwarding for deployment behind Kubernetes ingress / Nginx.

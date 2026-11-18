# index.html

**Path:** `nginx-reverse-proxy/static/index.html`
**Module:** `nginx-reverse-proxy.static.index`
**Feature Area:** `nginx-reverse-proxy`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Static landing page served by Nginx reverse proxy presenting user login prompt and redirect button for CILogon OAuth authentication.

## Connections
- **Shared data:** Initiates authentication flow through Nginx reverse proxy to OAuth2-proxy / CILogon.

## Dependencies
None

## Classes
None

## Functions
### `<form action="/auth/cilogon" method="get">`
> Form submitting user to CILogon SSO identity provider.
**Source:** `nginx-reverse-proxy/static/index.html:9`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Form action URL: `/auth/cilogon` |

## Data Shapes
None

## Notes
- Minimal static HTML served when unauthenticated users visit protected Braingeneers services.

# error.html

**Path:** `oauth2-proxy/error.html`
**Module:** `oauth2-proxy.error`
**Feature Area:** `oauth2-proxy`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Custom error template for oauth2-proxy displaying authentication failure explanations, Auth0 role requirements, and Slack #helpdesk troubleshooting guidance.

## Connections
- **Shared data:** Rendered by oauth2-proxy container when user authentication fails or missing required roles.

## Dependencies
None

## Classes
None

## Functions
### `{{ .Message }}`
> Renders dynamic OAuth failure message and request ID token.
**Source:** `oauth2-proxy/error.html:9`

## Config / CLI
None

## Data Shapes
- Template variables: `{{ .Message }}`, `{{ .RequestID }}`.

## Notes
- Instructs users on Auth0 role assignment issues and university credentials vs social login confusion.

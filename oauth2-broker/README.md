# Self-Hosted OIDC Broker

This folder contains the MCP-first OIDC broker artifacts that live in
`mission_control`.

Scope boundary:

- host: `oauth2.braingeneers.gi.ucsc.edu`
- product: `Keycloak`
- upstream human identity provider: `CILogon`
- downstream relying parties: MCP clients only for now
- out of scope:
  - changing the existing web `auth.braingeneers.gi.ucsc.edu` flow
  - replacing Auth0 for ordinary browser-facing services

## Why This Exists

Braingeneers wants MCP clients to authenticate against an authorization server
we control, instead of depending on Auth0-specific third-party app behavior.

This broker gives us:

- one Braingeneers-controlled OAuth/OIDC issuer for MCP
- one CILogon-facing confidential client instead of direct CILogon registration
  for every MCP client
- Dynamic Client Registration support under our control
- reusable infrastructure for future non-MCP workloads, without changing the web
  stack yet

## Service Layout

`docker-compose.yaml` defines two services:

- `oauth2-broker-db`
  - `postgres:16-alpine`
  - persistent data volume: `oauth2-broker-db-data`
- `oauth2-broker`
  - `quay.io/keycloak/keycloak:26.4.6`
  - public host: `https://oauth2.braingeneers.gi.ucsc.edu`
  - internal port: `8080`

The nginx override in
`service-proxy/oauth2.braingeneers.gi.ucsc.edu` disables the existing
`oauth2-proxy` browser-session enforcement for this host.

## Secret Files

Create a Kubernetes secret named `oauth2-broker` that provides:

- `oauth2-broker.env`
- `oauth2-broker-db.env`

Reference templates:

- `oauth2-broker.env.template`
- `oauth2-broker-db.env.template`

The `secret-fetcher` service will place those files at:

- `/secrets/oauth2-broker/oauth2-broker.env`
- `/secrets/oauth2-broker/oauth2-broker-db.env`

## Bootstrap Order

1. Reserve DNS for `oauth2.braingeneers.gi.ucsc.edu`.
2. Create the `oauth2-broker` Kubernetes secret with the env files above.
3. Start:
   - `oauth2-broker-db`
   - `oauth2-broker`
4. Log into Keycloak and create realm `braingeneers-mcp`.
5. Configure Keycloak to broker upstream login to CILogon.
6. Ask CILogon support to add the new Keycloak broker callback:
   - `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers-mcp/broker/cilogon/endpoint`
7. Configure Dynamic Client Registration, PKCE, MCP audience scopes, and realm
   roles as documented in `keycloak-bootstrap.md`.
8. Point `integrated-system-mcp` at the new issuer only after public metadata
   and token issuance are verified end to end.

## First MCP Realm Contract

Initial realm name:

- `braingeneers-mcp`

Initial issuer shape:

- issuer:
  - `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers-mcp`
- JWKS:
  - `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers-mcp/protocol/openid-connect/certs`

Initial protected resource audience for the current service:

- `https://integrated-system-mcp.braingeneers.gi.ucsc.edu/`

Recommended first claim mapping for MCP:

- `MCP_AUTH_ROLE_CLAIM=realm_access.roles`
- `MCP_ALLOWED_ROLES=mcp`

If the first pilot prefers identity-only tokens and YAML IAM, leave Keycloak
role assignment empty and configure:

- `MCP_ALLOWED_ROLES=""`
- `MCP_AUTH_ROLE_CLAIM=""`

## Known Product Constraint

Keycloak is a good fit here because it supports identity brokering and Dynamic
Client Registration, but its current MCP guidance is not perfect:

- Keycloak currently documents full support for the MCP authorization draft
  dated `2025-03-26`
- later MCP auth revisions rely on OAuth Resource Indicators (`resource`
  parameter), which Keycloak does not yet fully support as a broker-issued
  token feature

For the Braingeneers MCP pilot, the practical mitigation is:

- use audience-mapped client scopes for the MCP resource
- validate against real clients early
- be prepared to revisit the broker product if a target client requires stricter
  RFC 8707 behavior than Keycloak currently provides

## Files In This Folder

- `README.md`
  - high-level service and rollout notes
- `oauth2-broker.env.template`
  - Keycloak environment variables expected in the Kubernetes secret
- `oauth2-broker-db.env.template`
  - Postgres environment variables expected in the Kubernetes secret
- `keycloak-bootstrap.md`
  - exact operator bootstrap checklist for the first MCP realm

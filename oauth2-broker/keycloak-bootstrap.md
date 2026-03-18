# Keycloak Bootstrap For MCP

This checklist is the operator-side bootstrap for the first Braingeneers
MCP broker realm.

## 1. Confirm Infrastructure

- DNS for `oauth2.braingeneers.gi.ucsc.edu` points at the `mission_control`
  host
- `oauth2-broker-db` and `oauth2-broker` are running
- `https://oauth2.braingeneers.gi.ucsc.edu` loads the Keycloak UI

## 2. Create The MCP Realm

Create a new realm:

- realm name: `braingeneers-mcp`
- display name: `Braingeneers MCP`

This gives the first issuer:

- `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers-mcp`

## 3. Add The CILogon Identity Provider

Create an OIDC identity provider:

- alias: `cilogon`
- display name: `CILogon`
- discovery/import:
  - use CILogon OIDC discovery if available in the UI
- client authentication:
  - confidential client using the Braingeneers CILogon subscriber credentials

Expected Keycloak callback URL to register with CILogon:

- `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers-mcp/broker/cilogon/endpoint`

Do not repurpose the existing web callback:

- `https://auth.braingeneers.gi.ucsc.edu/oauth2/callback`

The broker callback is separate because web auth remains on the existing
`oauth2-proxy -> Auth0 -> CILogon` path for now.

## 4. Enable MCP-Oriented Client Registration

Enable OIDC Dynamic Client Registration for the realm so generic MCP clients can
create public/native clients without direct CILogon registration.

Target behavior:

- public clients allowed
- PKCE required
- loopback redirect URIs allowed for CLI/native clients
- client registration remains scoped to MCP use, not general-purpose anonymous
  browser apps

Recommended first pass:

- allow anonymous dynamic registration at the realm level
- keep PKCE mandatory for public clients
- keep the allowed grant types narrow
- review Keycloak trusted-host and redirect-uri registration policies before
  exposing the broker publicly

## 5. Create MCP Audience Scopes

Following Keycloak's published MCP guidance, create three optional client
scopes:

- `mcp:tools`
- `mcp:resources`
- `mcp:prompts`

For each scope, add an audience mapper that injects:

- `https://integrated-system-mcp.braingeneers.gi.ucsc.edu/`

This gives broker-issued access tokens the audience expected by the current
integrated-system MCP resource server.

## 6. Decide Coarse MCP Eligibility

Two supported patterns:

1. Keep a coarse realm role:
   - realm role: `mcp`
   - integrated-system runtime:
     - `MCP_ALLOWED_ROLES=mcp`
     - `MCP_AUTH_ROLE_CLAIM=realm_access.roles`

2. Use identity-only tokens plus YAML IAM:
   - no broker role requirement
   - integrated-system runtime:
     - `MCP_ALLOWED_ROLES=""`
     - `MCP_AUTH_ROLE_CLAIM=""`

Recommended first rollout:

- keep the coarse realm role `mcp`
- continue using YAML IAM as the real authorization layer

## 7. Test The Broker Itself

Verify:

- realm discovery:
  - `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers-mcp/.well-known/openid-configuration`
- JWKS:
  - `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers-mcp/protocol/openid-connect/certs`
- browser login reaches CILogon
- a test token contains:
  - issuer from the realm above
  - audience `https://integrated-system-mcp.braingeneers.gi.ucsc.edu/`
  - optional realm role `mcp`

## 8. Switch MCP Runtime Only After Broker Validation

When the broker is ready, set the MCP runtime environment to:

- `MCP_AUTH_ISSUER_URL=https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers-mcp`
- `MCP_AUTH_JWKS_URL=https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers-mcp/protocol/openid-connect/certs`
- `MCP_AUTH_RESOURCE_SERVER_URL=https://integrated-system-mcp.braingeneers.gi.ucsc.edu`
- `MCP_AUTH_AUDIENCE=https://integrated-system-mcp.braingeneers.gi.ucsc.edu/`
- `MCP_AUTH_ROLE_CLAIM=realm_access.roles`
- `MCP_ALLOWED_ROLES=mcp`

Leave the rest of the web stack unchanged.


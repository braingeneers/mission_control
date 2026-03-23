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

- realm name: `braingeneers`
- display name: `Braingeneers`

This gives the first issuer:

- `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers`

## 3. Add The CILogon Identity Provider

Create an OIDC identity provider:

- alias: `cilogon`
- display name: `CILogon`
- discovery/import:
  - use CILogon OIDC discovery if available in the UI
- client authentication:
  - confidential client using the Braingeneers CILogon subscriber credentials

Expected Keycloak callback URL to register with CILogon:

- `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers/broker/cilogon/endpoint`

Do not repurpose the existing web callback:

- `https://auth.braingeneers.gi.ucsc.edu/oauth2/callback`

The broker callback is separate because web auth remains on the existing
`oauth2-proxy -> Auth0 -> CILogon` path for now.

## 4. Create The `braingeneerspy-bridge` Client

Create a Keycloak client for the supported human-user bridge flow:

- client id:
  - `braingeneerspy-bridge`
- client type:
  - public
- client authentication:
  - off
- authorization:
  - off
- standard flow:
  - off
- direct access grants:
  - off
- service accounts:
  - off
- device authorization grant:
  - on
- valid redirect URIs:
  - not required for the device flow path

The `braingeneerspy` bridge bootstrap requests:

- `openid`
- `profile`
- `email`
- `offline_access`
- `mcp:tools`
- `mcp:resources`
- `mcp:prompts`

So the client should be allowed to request those scopes and receive refresh
tokens.

## 5. Optional: Keep DCR For Future Experiments

Dynamic Client Registration is no longer required for the supported
`braingeneerspy` bridge rollout, but you may still keep or pilot it for future
generic-client experiments.

If enabled, treat it as experimental and review:

- anonymous registration exposure
- trusted-host policy implications
- redirect URI policy
- how those choices interact with MCP clients from arbitrary user networks

## 6. Create MCP Audience Scopes

Following Keycloak's published MCP guidance, create three optional client
scopes:

- `mcp:tools`
- `mcp:resources`
- `mcp:prompts`

For each scope, add an audience mapper that injects:

- `https://integrated-system-mcp.braingeneers.gi.ucsc.edu/`

This gives broker-issued access tokens the audience expected by the current
integrated-system MCP resource server.

## 7. Decide Coarse MCP Eligibility

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

## 8. Test The Broker Itself

Verify:

- realm discovery:
  - `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers/.well-known/openid-configuration`
- JWKS:
  - `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers/protocol/openid-connect/certs`
- browser login reaches CILogon
- device flow works for client `braingeneerspy-bridge`
- a test token contains:
  - issuer from the realm above
  - audience `https://integrated-system-mcp.braingeneers.gi.ucsc.edu/`
  - optional realm role `mcp`

## 9. Switch MCP Runtime Only After Broker Validation

When the broker is ready, set the MCP runtime environment to:

- `MCP_AUTH_ISSUER_URL=https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers`
- `MCP_AUTH_JWKS_URL=https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers/protocol/openid-connect/certs`
- `MCP_AUTH_RESOURCE_SERVER_URL=https://integrated-system-mcp.braingeneers.gi.ucsc.edu`
- `MCP_AUTH_AUDIENCE=https://integrated-system-mcp.braingeneers.gi.ucsc.edu/`
- `MCP_AUTH_ROLE_CLAIM=realm_access.roles`
- `MCP_ALLOWED_ROLES=mcp`

Leave the rest of the web stack unchanged.

# Braingeneers MCP Onboarding

This runbook defines the shared deployment and operator workflow for Braingeneers
MCP services.

The platform model is federated:

- each project keeps its own MCP service
- all MCP services reuse the same IAM workflow and ingress pattern

## What Lives Where

Shared operational artifacts in `mission_control`:

- `docker-compose.yaml`
- `service-proxy/mcp-resource-server.template`
- `service-accounts/`
- `iam/groups.yaml`
- `iam/<service>.policy.yaml`
- `iam/policy.template.yaml`

Shared runtime code:

- lives in `braingeneerspy` as importable shared code, not only in compose snippets
- current runtime package: `braingeneers.mcp`

Service-local code:

- tools and resources
- service-specific resource hierarchy
- domain-specific authorization checks

## Standard Compose Pattern

Every MCP service should:

1. Stay behind the shared edge proxy.
2. Disable browser-style `oauth2-proxy` enforcement for the MCP endpoint via a vhost override.
3. Preserve the `Authorization` header to the backend.
4. Mount `./iam` read-only into the container.
5. Set the protected-resource URL and audience explicitly.

Reference environment block:

```yaml
    environment:
      MCP_BASE_URL: "https://your-service.braingeneers.gi.ucsc.edu"
      MCP_STREAMABLE_HTTP_PATH: "/mcp"
      MCP_HEALTH_PATH: "/healthz"
      MCP_AUTH_RESOURCE_SERVER_URL: "https://your-service.braingeneers.gi.ucsc.edu"
      MCP_AUTH_AUDIENCE: "https://your-service.braingeneers.gi.ucsc.edu/"
      MCP_IAM_POLICY_PATH: "/iam/your-service.policy.yaml"
      VIRTUAL_HOST: "your-service.braingeneers.gi.ucsc.edu"
      VIRTUAL_PORT: "8000"
      LETSENCRYPT_HOST: "your-service.braingeneers.gi.ucsc.edu"
      LETSENCRYPT_EMAIL: "braingeneers-admins-group@ucsc.edu"
    volumes:
      - secrets:/secrets
      - ./iam:/iam:ro
```

Use `service-proxy/mcp-resource-server.template` as the hostname-specific proxy override.

## IAM Pattern

Use one service policy file per MCP service:

- `iam/groups.yaml` for reusable principal groups
- `iam/<service>.policy.yaml` for resource grants

The platform rules are:

- deny by default
- coarse token roles are necessary but not sufficient
- explicit grants are still required
- each service may define its own resource hierarchy, but operator workflow should stay familiar

## Supported Human Path

Current supported human-user MCP path:

- `python -m braingeneers.iot.authenticate`
  - bootstraps both:
    - the broad Auth0-backed service-account token
    - the narrower interactive user token for local MCP bridge use from
      Keycloak device flow
- `python -m braingeneers.mcp.bridge`
  - runs a local HTTP bridge that forwards to the real remote MCP service with
    the interactive bearer token
- Codex, Claude Code, and similar tools connect to the local bridge, not
  directly to the public Braingeneers MCP hostname

Current bridge-token issuer:

- issuer:
  - `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers`
- JWKS:
  - `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers/protocol/openid-connect/certs`
- device authorization endpoint:
  - `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers/protocol/openid-connect/auth/device`
- token endpoint:
  - `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers/protocol/openid-connect/token`

This keeps the existing browser-oriented web `Auth0 -> CILogon` stack intact
while removing MCP’s dependency on direct remote client OAuth interoperability
for the first supported human flow.

## Bridge-Issuer Configuration Checklist

Shared across Braingeneers MCP services:

- same local bridge-token issuer host:
  - `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers`
- same bridge client:
  - `braingeneerspy-bridge`
- same public JWKS path on the Keycloak realm
- same coarse role vocabulary in bridge tokens:
  - `mcp`
  - `user` remains reserved for normal web apps and should not grant MCP access

Service-specific per MCP service:

1. Create or reserve one protected-resource audience for the service hostname.
2. Add that audience to the Keycloak client-scope/audience-mapper configuration.
3. Configure the MCP backend with:
   - issuer URL
   - JWKS URL
   - audience
   - resource server URL
4. Grant coarse roles only to principals eligible to use MCP at all.
5. Keep fine-grained authorization in YAML policy, not just token roles.

The self-hosted Keycloak broker under `oauth2.braingeneers.gi.ucsc.edu`
is now the supported issuer for the human-user bridge path.

Direct CILogon pilot notes:

- keep the existing web `Auth0 -> CILogon` path unchanged while piloting MCP-only changes
- the MCP runtime can now disable provider-side coarse role checks by setting `MCP_ALLOWED_ROLES=""`
- the MCP runtime can now disable provider-specific role-claim extraction by setting `MCP_AUTH_ROLE_CLAIM=""`
- in that pilot mode, local YAML IAM remains authoritative and the upstream issuer only needs to provide a stable authenticated identity

## Experimental Self-Hosted Broker Pilot

The first self-hosted broker artifacts now live in:

- `oauth2-broker/README.md`
- `oauth2-broker/keycloak-bootstrap.md`
- `oauth2-broker/cilogon-support-email.template.md`

Current broker choice:

- product: `Keycloak`
- public host: `https://oauth2.braingeneers.gi.ucsc.edu`
- realm name: `braingeneers`

Current broker-to-MCP environment contract:

```yaml
    environment:
      MCP_AUTH_ISSUER_URL: "https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers"
      MCP_AUTH_JWKS_URL: "https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers/protocol/openid-connect/certs"
      MCP_AUTH_RESOURCE_SERVER_URL: "https://integrated-system-mcp.braingeneers.gi.ucsc.edu"
      MCP_AUTH_AUDIENCE: "https://integrated-system-mcp.braingeneers.gi.ucsc.edu/"
      MCP_AUTH_ROLE_CLAIM: "realm_access.roles"
      MCP_ALLOWED_ROLES: "mcp"
```

Identity-only fallback with YAML IAM remains available:

- `MCP_ALLOWED_ROLES=""`
- `MCP_AUTH_ROLE_CLAIM=""`

Current Keycloak caveat:

- Keycloak is a strong fit for DCR plus upstream OIDC brokering, but its current
  MCP guidance still lags newer Resource Indicator requirements
- validate real MCP clients early and keep the legacy Auth0 service-account path
  available for unattended non-MCP callers

## Integrated-System Reference Service

Current reference deployment:

- hostname: `https://integrated-system-mcp.braingeneers.gi.ucsc.edu`
- streamable HTTP path: `/mcp`
- health path: `/healthz`
- proxy override:
  - `service-proxy/integrated-system-mcp.braingeneers.gi.ucsc.edu`
- IAM file:
  - `iam/integrated-system-mcp.policy.yaml`

What remains integrated-system-local:

- MQTT command catalog
- experiment UUID -> device -> command authorization semantics
- biology-resource audit details

## End-to-End Test Plan

Run these checks after deploy:

1. Protected-resource and health discovery
   - `curl -i https://integrated-system-mcp.braingeneers.gi.ucsc.edu/healthz`
   - confirm the response includes the configured audience, resource-server URL, and IAM policy path
2. Reverse-proxy auth behavior
   - `curl -i https://integrated-system-mcp.braingeneers.gi.ucsc.edu/mcp`
   - unauthenticated requests should not be served as an authenticated browser session
3. Authorization-header preservation
   - send a bearer token through the public hostname and verify the backend sees token-based auth rather than stripped headers
4. IAM enforcement
   - confirm a principal with valid coarse role but no YAML grant is denied
   - confirm a principal with the right YAML grant can only reach the UUID and device scope explicitly granted
5. Human-user login
   - if tenant settings support the target MCP client flow, complete a real login through the client and verify tool access
6. Broker validation, when using the self-hosted path
   - `curl -i https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers/.well-known/openid-configuration`
   - confirm the issuer and token endpoints are reachable through the public hostname

## Fallback and Troubleshooting

If generic MCP login is not fully enabled yet, use a token-based fallback path:

- mint or obtain a bearer token for the MCP audience
- call the deployed hostname directly with `Authorization: Bearer <token>`
- verify the backend accepts valid tokens and still denies callers lacking YAML grants

Distinguish failures this way:

- protected-resource metadata failure:
  - the client cannot discover or parse the MCP auth metadata
- reverse-proxy failure:
  - `Authorization` is missing at the backend or browser auth still intercepts `/mcp`
- Auth0 registration failure:
  - the client cannot complete OAuth client registration or is rejected before token issuance
- broker registration failure:
  - the self-hosted broker is reachable, but Keycloak DCR or redirect policy blocks the client before token issuance
- application token-validation failure:
  - the backend receives the token but rejects issuer, audience, signature, or expiry
- application IAM failure:
  - token is valid but the principal lacks the required YAML grant

## Rollout Order

Use this release order for the first platform version:

1. land shared runtime auth and IAM code
2. make `integrated-system-mcp` consume that shared substrate
3. add the shared `mission_control` proxy template, IAM template, and operator docs
4. deploy `integrated-system-mcp` with explicit IAM mount and MCP env variables
5. validate end to end using the checks above
6. only then onboard a second MCP service

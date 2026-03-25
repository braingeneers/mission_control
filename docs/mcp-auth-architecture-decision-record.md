# MCP Authentication Architecture Decision Record

This document records the reasoning that led from the original
`Auth0 -> CILogon` MCP rollout to the current preferred direction:

- keep the existing web stack unchanged for now
- stop requiring generic remote OAuth support in every third-party MCP client
- introduce a Braingeneers-managed local MCP relay path in `braingeneerspy`
- evolve the existing token-issuance flow so it produces user-scoped MCP tokens

This is a thought-process record, not a final implementation runbook.

## Scope Boundary

In scope:

- MCP authentication for Braingeneers services
- MCP client compatibility constraints
- alternatives considered for remote MCP auth
- why each path was kept, deferred, or rejected

Out of scope:

- replacing the existing web-service Auth0 path immediately
- redesigning ordinary browser auth in `mission_control`

The current browser-oriented web path remains:

- `service-proxy -> oauth2-proxy -> Auth0 -> CILogon`

References:

- [`mission_control/README.md`](/home/davidparks21/myprojects/Braingeneers/mission_control/README.md#L259)
- [`integrated-system-modules/mcp_server/AGENTS.md`](/home/davidparks21/myprojects/Braingeneers/integrated-system-modules/mcp_server/AGENTS.md)

## Background

Braingeneers initially stood up MCP as a standards-oriented remote OAuth
resource server:

- MCP backend validates bearer tokens directly
- proxy preserves `Authorization`
- IAM remains local YAML policy

That part is sound and remains valuable.

The trouble was client registration and login for generic MCP clients. We found
that the server side was the easy part; the hard part was getting real clients
such as Codex or Claude Code to complete a standards-compliant remote OAuth flow
against infrastructure we control.

## MCP Specification References

These spec and design references shaped the decision process:

1. MCP Authorization Specification
   - https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
   - Key points:
     - MCP clients act as OAuth clients
     - MCP servers act as resource servers
     - pre-registration is valid
     - Client ID Metadata Documents are preferred
     - Dynamic Client Registration is fallback, not the only answer

2. MCP Blog Post: Evolving OAuth Client Registration in the Model Context Protocol
   - https://blog.modelcontextprotocol.io/posts/client_registration/
   - Key points:
     - DCR has major operational problems in open environments
     - CIMD avoids unbounded client-registration databases
     - CIMD gives one client identity per app instead of one registration per
       user/device instance
     - DCR is still useful for backward compatibility, but CIMD is the forward
       recommendation

Important excerpted themes from the blog:

- DCR creates:
  - unbounded database growth
  - per-instance client confusion
  - unauthenticated write endpoints
  - operational pressure around policy controls such as trusted hosts
- CIMD avoids those operational issues by making the client metadata URL the
  client identifier

## Existing Braingeneers Authentication Pieces

Braingeneers already has a user-facing token bootstrap flow in `braingeneerspy`:

- [`braingeneerspy/src/braingeneers/iot/authenticate.py`](/home/davidparks21/myprojects/Braingeneers/braingeneerspy/src/braingeneers/iot/authenticate.py#L12)
  - opens:
    - `https://service-accounts.braingeneers.gi.ucsc.edu/generate_token`
  - asks the user to paste JSON token output locally
- [`braingeneerspy/src/braingeneers/iot/messaging.py`](/home/davidparks21/myprojects/Braingeneers/braingeneerspy/src/braingeneers/iot/messaging.py#L930)
  - stores the token locally
  - auto-refreshes it later from the same service URL

Today, however, the service that issues those tokens is not user-scoped. It is
an Auth0 client-credentials token generator:

- [`service-accounts/app/token_service.py`](/home/davidparks21/myprojects/Braingeneers/mission_control/service-accounts/app/token_service.py#L25)
  - mints tokens with:
    - `grant_type: client_credentials`
  - for audience:
    - `https://auth.braingeneers.gi.ucsc.edu/`

This means the current flow is convenient, but it is not the right final shape
for per-user MCP authorization and audit because the token itself is not a
user-scoped access token.

## Approaches Considered

### 1. Keep Auth0 As The Remote MCP Authorization Server

Description:

- Use the current Auth0 tenant for MCP
- dedicate one Auth0 API per MCP resource
- let clients authenticate remotely against Auth0/CILogon

Pros:

- reused an already deployed identity platform
- no new broker infrastructure required at first
- matched standard “client gets token, server validates token” MCP flow

Cons:

- Codex was observed to depend on Dynamic Client Registration
- DCR in Auth0 created third-party apps per login attempt
- third-party app handling plus domain-level connection rules were operationally
  awkward
- even after enabling DCR and adjusting the CILogon connection, the hosted login
  still did not cleanly complete for Codex

Why this was not chosen as the long-term path:

- it kept Braingeneers tied to Auth0-specific client-registration behavior
- it did not reduce external dependency complexity
- it did not solve the broader “generic MCP client registration” problem cleanly

### 2. Use CILogon Directly As The MCP Authorization Server

Description:

- remove Auth0 from the MCP path
- have clients authenticate directly against CILogon
- keep local YAML IAM for resource authorization

Pros:

- fewest moving parts in theory
- removes Auth0 dependency from MCP
- CILogon is already the upstream identity source

Cons:

- CILogon client registration is manual/operator mediated
- direct public-client support looked too rigid for arbitrary native clients
- there was no evidence that CILogon would satisfy the MCP registration
  expectations for generic clients without extra broker logic

Why this was not chosen:

- likely workable for tightly controlled clients
- not a good match for “many possible MCP clients” without further brokering

### 3. Self-Host A Braingeneers OIDC Broker For Remote MCP OAuth

Description:

- host a broker under `oauth2.braingeneers.gi.ucsc.edu`
- broker upstream login to CILogon
- let generic MCP clients authenticate against Braingeneers instead of directly
  against CILogon

Pros:

- removes Auth0 from the MCP path
- keeps Braingeneers in control of DCR, PKCE, scopes, and client policies
- reusable later if web auth is migrated off Auth0 too

Cons:

- still depends on what real clients support
- requires broker infrastructure and state
- Keycloak, the initial product considered, exposed a major mismatch:
  - anonymous DCR required `Trusted Hosts`
  - that does not fit arbitrary CLI users connecting from anywhere
- current Keycloak MCP guidance still lags newer Resource Indicator expectations

Why this was not chosen as the primary path:

- the broker itself is manageable
- the client-registration model remained the hard problem
- without CIMD support in the clients we care about, a remote broker still does
  not guarantee good user experience

### 4. Continue Pursuing Dynamic Client Registration For Arbitrary Clients

Description:

- accept DCR as the operational model
- adjust broker policies to permit registrations from users

Pros:

- aligns with current Codex observed behavior
- no manual pre-registration per client app

Cons:

- DCR was the exact operational problem the MCP project blog identified
- Keycloak’s `Trusted Hosts` policy exposed the core issue directly
- allowing anonymous internet-wide registration is an unnecessary and potentially
  unsafe write surface
- per-user IP-based registration is brittle and poor UX

Why this was rejected:

- DCR alone is not a good long-term operational model for Braingeneers
- the trusted-host constraint made that obvious in practice

### 5. Pre-Registered Client Configuration Distributed Through A Braingeneers Web Page

Description:

- Braingeneers hosts a page that authenticated users visit
- the page shows or delivers pre-registered OAuth client configuration
- users copy that into Codex/Claude or another MCP client

Pros:

- avoids open DCR
- could give users one-time onboarding
- does not depend on user IP

Cons:

- only works if the target MCP clients support static/pre-registered client
  configuration
- we did not find documentation showing Codex CLI or Claude Code support that
  path clearly
- still leaves Braingeneers exposed to client-specific configuration UX

Why this was not chosen as the primary path:

- architecturally reasonable
- blocked by uncertain client support

### 6. Braingeneers-Managed Local MCP Relay In `braingeneerspy`

Description:

- users authenticate through a Braingeneers-managed flow, similar to the current
  `python -m braingeneers.iot.authenticate`
- Braingeneers stores a local MCP token in `braingeneerspy`
- a local MCP relay/proxy in `braingeneerspy` presents itself to Codex/Claude as
  a local MCP server
- the relay forwards requests to the real remote MCP server using the locally
  managed bearer token

Pros:

- avoids forcing every third-party MCP client to support Braingeneers’ preferred
  remote OAuth registration model
- fits the existing `braingeneerspy` user workflow
- lets Braingeneers fully control token bootstrap and refresh UX
- works with client surfaces that are already good at talking to local MCP
  servers
- dramatically reduces remote OAuth complexity for end users

Cons:

- this is not “native remote OAuth” inside every third-party client
- requires a Braingeneers-supported local relay command/tool
- the current token service must be redesigned because it currently issues broad
  client-credentials tokens, not user-scoped MCP tokens

Why this is the current leading plan:

- it aligns with infrastructure Braingeneers already controls
- it avoids the worst parts of DCR
- it avoids betting the project on undocumented client capabilities
- it provides a concrete supported path for users today

## Client Compatibility Observations

### Codex

Observed:

- `codex mcp login integrated-system-mcp` failed with:
  - `dynamic client registration is disabled`
  when DCR was disabled

Implication:

- Codex clearly uses DCR today in the tested remote OAuth path

We did not find:

- documented Client ID Metadata Document support
- documented static/pre-registered client configuration for the CLI itself

### Claude Code

Observed from Anthropic docs:

- Claude Code supports OAuth 2.0 for remote MCP servers

We did not find:

- documented Client ID Metadata Document support
- documented static/pre-registered client configuration details

Implication:

- remote native OAuth support exists in some form
- but the registration model needed for a clean Braingeneers deployment remains
  uncertain

## Public MCP Server Examples From Major Organizations

The current ecosystem shows that large organizations are not all solving this
with one universal remote-OAuth pattern.

### Notion

Hosted MCP server:

- `https://mcp.notion.com/mcp`

Observed pattern:

- hosted remote MCP server with OAuth for interactive use
- explicit local bridge recommendation when client compatibility is not good
  enough:
  - `npx -y mcp-remote https://mcp.notion.com/mcp`
- bearer-token auth is not the path they recommend for the hosted server

References:

- https://developers.notion.com/docs/mcp
- https://developers.notion.com/docs/get-started-with-mcp

Why this mattered:

- Notion is effectively acknowledging that a local bridge remains a practical
  solution even for a major public MCP service.

### Stripe

Hosted MCP server:

- `https://mcp.stripe.com`

Observed pattern:

- hosted OAuth-enabled MCP server for interactive clients
- separate local package path for autonomous or non-interactive workflows:
  - `npx -y @stripe/mcp@latest`
- Stripe is not treating remote hosted OAuth as the only viable integration
  model

References:

- https://docs.stripe.com/mcp
- https://docs.stripe.com/building-with-llms

Why this mattered:

- A major vendor explicitly supports a local helper/package path rather than
  insisting that every client consume one hosted OAuth story.

### Slack

Observed pattern:

- Slack’s MCP server is OAuth-oriented
- Slack limits who can use it:
  - marketplace apps
  - internal apps
- Slack leans on OAuth Authorization Server Metadata when the client supports it

References:

- https://docs.slack.dev/ai/slack-mcp-server/
- https://docs.slack.dev/changelog/2026/02/17/slack-mcp/
- https://www.slack.dev/secure-data-connectivity-for-the-modern-ai-era/

Why this mattered:

- Slack is not an example of “any random client from anywhere with no platform
  constraints”
- even large vendors often constrain supported app models

### Cloudflare

Examples:

- `https://graphql.mcp.cloudflare.com/mcp`
- `https://dex.mcp.cloudflare.com/mcp`

Observed pattern:

- multiple public MCP servers
- several authorization patterns:
  - Cloudflare Access as auth provider
  - third-party OAuth provider
  - some public/no-auth examples
  - portal-style flows

References:

- https://developers.cloudflare.com/agents/model-context-protocol/mcp-servers-for-cloudflare/
- https://developers.cloudflare.com/agents/model-context-protocol/authorization/
- https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/mcp-portals/
- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/mcp-servers/linked-apps/

Why this mattered:

- Cloudflare can do more here because it already operates a very rich auth and
  edge platform
- that flexibility should not be mistaken for the baseline capability a small
  lab can easily reproduce

## What The Public Examples Changed In Our Reasoning

These examples changed the decision process in an important way:

- they show that local bridges and local helper packages are normal, not
  embarrassing exceptions
- they show that “public MCP server” does not automatically mean “any generic
  client can authenticate natively with no vendor-specific constraints”
- they show that large organizations often:
  - support only specific client/app classes
  - provide local bridge/helper fallbacks
  - or rely on platform capabilities that are much heavier than what
    Braingeneers needs to reproduce

So the Braingeneers local relay idea is not a retreat from the real world. It is
consistent with patterns already used by major MCP providers.

## Current Preferred Direction

The current preferred direction is:

1. Keep the existing browser-oriented web auth path unchanged for now.
2. Stop requiring direct remote OAuth interoperability as the only supported MCP
   path.
3. Keep the existing broad Auth0 service-account bootstrap path for legacy
   callers, but move interactive helper-user tokens to the self-hosted Keycloak
   broker at `oauth2.braingeneers.gi.ucsc.edu`.
4. Build a local MCP helper in `braingeneerspy`.
5. Have Codex, Claude Code, and similar tools launch that helper as a local
   stdio MCP server.
6. Let the local helper connect to the real remote MCP service over HTTP with
   the bearer token Braingeneers manages.

## Important Constraint On The Final Plan

The current `generate_token` service cannot simply be reused unchanged.

Today it returns a broad Auth0 client-credentials token:

- `grant_type: client_credentials`
- audience:
  - `https://auth.braingeneers.gi.ucsc.edu/`

That is not enough for per-user MCP authorization.

The implemented direction requires:

1. The token returned to `braingeneerspy` is user-scoped.
2. The token includes stable user identity such as `sub`.
3. The token is minted by the Braingeneers-controlled Keycloak broker at
   `https://oauth2.braingeneers.gi.ucsc.edu/realms/braingeneers` for the MCP
   audience `https://integrated-system-mcp.braingeneers.gi.ucsc.edu/`.
4. The remote MCP service should rely on the bearer token claims after
   validation, not on unsafely injected user headers from the local relay.

Important design rule:

- the local relay may forward the bearer token
- the local relay should not be trusted merely because it says “the user is X”
  out of band

If Braingeneers controls both the token issuer and the relay, the relay can work
cleanly. But the security boundary should remain:

- signed token claims are authoritative
- not proxy-added identity strings

## Why This Direction Is Reasonable

This plan accepts an important reality:

- local-client support is much better today than clean, generic, remote MCP OAuth
  interoperability across all client vendors

Instead of fighting that, Braingeneers can:

- use the existing browser bootstrap UX it already understands
- keep identity issuance under its own control
- keep resource authorization in YAML IAM
- expose a stable, supported local MCP client story now

If native remote client registration improves later, Braingeneers can revisit it
without losing the value of the local relay path.

## Current Implementation Shape

The current implementation direction is:

1. Keep `GET /generate_token` unchanged for the broad Auth0-backed
   service-account token.
2. Have `python -m braingeneers.iot.authenticate` bootstrap:
   - the broad Auth0 service-account token from `service-accounts`
   - the interactive helper-user token directly from Keycloak device flow
3. Configure the local helper to refresh the user token against the standard
   Keycloak token endpoint with `grant_type=refresh_token`.
4. Keep `oauth2.braingeneers.gi.ucsc.edu` as the long-lived issuer, JWKS host,
   and future-proof identity hostname.
5. Run `python -m braingeneers.mcp` locally and point external MCP clients at
   that stdio helper instead of at the public remote hostname.

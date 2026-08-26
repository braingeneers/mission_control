---
name: mission-control-services-management
description: Design, deploy, operate, or diagnose Braingeneers services managed by mission_control on braingeneers.gi.ucsc.edu. Use for Compose service wiring, protected HTTPS API diagnosis, proxy and authentication patterns, shared infrastructure, secrets, packaging, and targeted production operations. Do not use for ordinary application development that does not involve Mission Control deployment or service contracts.
---

# Mission Control Services Management

Use this skill for services deployed through the `mission_control` repository on
`braingeneers.gi.ucsc.edu`.

## Non-Negotiable Boundaries

- Never SSH to, log in to, or execute commands on the production server or its
  aliases. Run production diagnosis only through approved HTTPS APIs. Give the
  user or operator exact commands for server-side work and wait for the result.
- Never create, patch, replace, or delete Kubernetes Secrets. Secret mutations
  are operator-owned; provide instructions without performing the mutation.
- Do not run production-style Mission Control services locally unless the user
  explicitly requests a local test.
- Preserve user scope. Diagnosis does not authorize deployment, restart,
  migration, notification delivery, or another external mutation.
- After Compose or proxy changes, run `make test`.

## Choose The Evidence Or Action Surface First

Classify what the user needs before selecting tools or deployment topology:

- **Hosted service data or status:** use the documented HTTPS API from the local
  workstation with the standard service-account JWT. Read
  [references/access-and-auth.md](references/access-and-auth.md).
- **Data Explorer content:** for paths, searches, fresh listings, and downloads,
  use the `data-explorer-cli-access` skill when available. A request to find or
  verify objects is semantic data access even if the user says “on the website.”
  Use `refresh=true` when newly written objects may be hidden by cache.
- **Rendered or interactive UI behavior:** use browser control for layout,
  visible state, navigation, screenshots, or interaction. If the user requests
  both data verification and UI verification, perform and report them
  separately; browser unavailability does not invalidate API evidence.
- **Production host operation:** provide targeted commands for an operator to
  run on `braingeneers.gi.ucsc.edu`; do not run them locally or over SSH.
- **Implementation or configuration change:** inspect the relevant deployment
  and owning-service sources, then choose the service route below.

## Inspect Selectively

Read only sources that can change the decision:

1. Read the applicable `AGENTS.md` files and relevant sections of the repository
   `README.md`.
2. Inspect the matching Compose service, proxy override, script, test, and
   owning-service source. Do not load the entire Compose stack or every proxy
   file when one service is in scope.
3. Load only the references routed below. Use the local Braingeneers wiki when
   available; otherwise use its GitHub source.
4. Confirm access prerequisites only when the task needs them: GI server access,
   Braingeneers GitHub access, NRP namespace access, or registry credentials.

## Choose Deployment Topology When It Matters

Read [references/service-routing.md](references/service-routing.md) before adding
or changing routing:

- `private-web`: browser and standard service-JWT authentication at the shared
  proxy; the backend receives trusted identity headers, not `Authorization`.
- `public-web`: intentionally unauthenticated HTTP behind shared edge TLS.
- `machine-api`: backend validates bearer tokens; proxy preserves
  `Authorization` and clears identity-looking headers.
- `headless`: direct-port or non-HTTP service; no nginx vhost discovery.
- `mcp`: OAuth protected resource; backend validates bearer tokens and IAM.

Do not classify an API as `machine-api` merely because software calls it. The
standard service-account JWT works through the normal `private-web` proxy when
the proxy is intended to authenticate the client.

## Load References By Need

- [access-and-auth.md](references/access-and-auth.md): web/API access, JWT
  discovery and validation, kubeconfig modes, and MCP distinction.
- [service-routing.md](references/service-routing.md): topology, proxy identity
  and authorization behavior, and custom nginx directives.
- [operations.md](references/operations.md): targeted deployment, status,
  verification, troubleshooting, and escalation.
- [packaging.md](references/packaging.md): image ownership, registries,
  Makefiles, Compose boundaries, and shared state volumes.
- [secrets.md](references/secrets.md): `secret-fetcher`, mounted files,
  entrypoint setup, runtime tokens, and operator-owned secret changes.
- [sql-db.md](references/sql-db.md): shared PostgreSQL client and backup
  contract.
- [hosted-llms.md](references/hosted-llms.md): NRP-hosted model access and its
  distinct API-key contract.
- [notifications.md](references/notifications.md): shared Slack and email API,
  caller behavior, Postfix, and provider-specific operations.
- [web-app-style.md](references/web-app-style.md): Braingeneers operations UI
  style and bundled assets, only for new or materially refreshed web UIs.

For MCP services, also inspect `docs/mcp-onboarding.md`,
`oauth2-broker/README.md`, the MCP proxy template, and the wiki MCP architecture.

## Shared Design Defaults

- Keep `mission_control` a thin deployment repository. Service-owned code,
  schedulers, migrations, runtime defaults, and application configuration
  belong in the owning repository and published image.
- Prefer registry-published images and targeted service operations over
  server-local builds or whole-stack restarts.
- Use Compose `depends_on` only for genuine startup prerequisites.
- Use shared `local` for restart-persistent disposable state and `replicated`
  for completed static artifacts that require additive backup. Give each
  service its own subdirectory.
- Use `notification-service` for new outbound Slack or email integrations and
  shared `sql-db` for ordinary relational state; load their references before
  designing either integration.

## Verify And Hand Off

- Match validation to the change and service route. Prefer existing contract
  tests and read-only health/status endpoints.
- For production operations, supply the smallest exact command sequence and
  state the expected evidence. Wait for the operator’s output before claiming
  success.
- Report separately what was verified from source, API responses, browser UI,
  and operator-provided production output.
- Escalate missing GI, GitHub, NRP, registry, identity-provider, or secret-admin
  permissions instead of working around them.

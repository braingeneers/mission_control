# Service Routing

Use this reference when choosing how a service reaches users or clients.

## Branch Decision

Classify the service first:

- `private-web`: HTTP service for lab users; default browser auth through `service-proxy/default`.
- `public-web`: HTTP service intentionally public; host-specific `service-proxy` file with `auth_request off`.
- `headless`: direct TCP/UDP or non-HTTP service, for example MQTT or RustDesk; exposed with `ports:` and not routed by nginx vhost discovery.
- `mcp`: HTTP MCP resource server; shared edge and TLS, no browser auth on MCP traffic, backend validates bearer tokens and IAM.

## Private Web

Expected Compose features:

- `image:` points at a registry-published image.
- `expose:` lists the internal app port.
- `environment:` uses dictionary form, not list `KEY=value` form.
- `VIRTUAL_HOST`, `VIRTUAL_PORT`, `LETSENCRYPT_HOST`, and `LETSENCRYPT_EMAIL` are set.
- The service joins `braingeneers-net`.

Default browser auth comes from `service-proxy/default`, which performs an internal auth request and configures these application-facing identity headers from the authentication response:

- `X-User`
- `X-Email`
- `X-Groups`
- `X-Name`
- `X-Given-Name`
- `X-Family-Name`
- `X-Preferred-Username`
- `X-Subject`

Treat this as a description of the current proxy configuration, not a guarantee that every header is populated. Header values depend on the deployed oauth2-proxy version, identity-provider claims, and authentication method; missing source fields may produce empty or omitted headers. Verify the deployed route before advising an application to depend on a particular field.

On this authenticated path, service-proxy overwrites these names with values from the authentication subrequest and strips `Authorization` before forwarding the request. Trust the identity headers only when the application is reachable solely through this protected proxy path.

### Validated Workflows Identity

The current protected Workflows production route has been inspected end to end. It provides a usable authenticated email in `X-Email`; `X-User` contains an opaque CILogon subject, while `X-Groups`, `X-Name`, `X-Given-Name`, `X-Family-Name`, `X-Preferred-Username`, and `X-Subject` are empty. Workflows uses only `X-Email` for browser attribution and ignores `X-User` as a display identity.

This is authoritative only on the protected private-web route, where nginx overwrites the header from the authentication subrequest. Prod-local and direct local requests do not necessarily have proxy identity headers, so Workflows falls back to the friendly initiator `User`. Do not log identity headers now that the contract has been validated. This finding is specific to the current Workflows deployment; validate the populated fields separately before another service depends on them.

## Public Web

Use only when the service is intentionally public.

Required shape:

- Normal `VIRTUAL_HOST` Compose discovery.
- Host-specific file under `service-proxy/<hostname>`.
- `auth_request off` in that vhost override.
- Matching bind mount in the `service-proxy` service in `docker-compose.yaml`.
- Treat identity-looking request headers as untrusted client input; this route does not provide proxy-authenticated identity.

Example source: `service-proxy/spikelab.braingeneers.gi.ucsc.edu`.

## Custom Proxy Directives

Use host-specific or `_location` files for service-specific nginx needs such as:

- Large body uploads.
- Disabled request or response buffering.
- Long timeouts.
- Websocket upgrade headers.
- Custom access or error logs.

Examples:

- `service-proxy/uploader.braingeneers.gi.ucsc.edu`
- `service-proxy/uploader.braingeneers.gi.ucsc.edu_location`

## Headless Services

Headless services do not use `VIRTUAL_HOST` or `LETSENCRYPT_HOST` unless they also expose a separate web UI.

Expected Compose features:

- Direct `ports:` mappings for the required TCP or UDP ports.
- Service-specific credentials or persistent volumes if needed.
- `braingeneers-net` when the service must talk to other Compose services.
- Secret mounts and `secret-fetcher` dependency if the service needs shared credentials.

Examples:

- MQTT maps ports including `1883`, `8883`, and EMQX dashboard or websocket ports.
- RustDesk maps relay and rendezvous ports and uses secret-mounted RustDesk keys.

Relevant sources. Use a local checkout of `github.com/braingeneers/wiki` when available; otherwise use the GitHub links:

- `docker-compose.yaml`
- `shared/mqtt.md`: https://github.com/braingeneers/wiki/blob/main/shared/mqtt.md
- `shared/rustdesk.md`: https://github.com/braingeneers/wiki/blob/main/shared/rustdesk.md

## MCP Services

MCP services are a separate branch.

Required behavior:

- Stay behind shared `service-proxy` edge and TLS.
- Disable browser-style `oauth2-proxy` enforcement for MCP traffic.
- Preserve the end-to-end `Authorization` header.
- Strip proxy-trusted identity headers so backend authorization relies on token validation.
- Mount `./iam` read-only and use one service-specific IAM policy file.
- Set issuer, JWKS, audience, and resource-server URL explicitly.

Use `service-proxy/mcp-resource-server.template` as the proxy override baseline.

Relevant local sources:

- `docs/mcp-onboarding.md`
- `service-proxy/mcp-resource-server.template`
- `service-proxy/integrated-system-mcp.braingeneers.gi.ucsc.edu`
- Braingeneers wiki `shared/mcp_architecture.md`: https://github.com/braingeneers/wiki/blob/main/shared/mcp_architecture.md

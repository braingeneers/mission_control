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

Default browser auth comes from `service-proxy/default`, which performs an internal auth request and passes proxy-derived identity headers such as `X-Email` and `X-Groups` to the backend.

## Public Web

Use only when the service is intentionally public.

Required shape:

- Normal `VIRTUAL_HOST` Compose discovery.
- Host-specific file under `service-proxy/<hostname>`.
- `auth_request off` in that vhost override.
- Matching bind mount in the `service-proxy` service in `docker-compose.yaml`.

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

Relevant local sources:

- `docker-compose.yaml`
- `../wiki/shared/mqtt.md`
- `../wiki/shared/rustdesk.md`

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
- `../wiki/shared/mcp_architecture.md`

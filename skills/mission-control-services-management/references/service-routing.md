# Service Routing

Use this reference only when adding, changing, or diagnosing how a service is
reached. Accessing an existing service's data does not require redesigning its
route; use `access-and-auth.md` for client access.

## Route Decision

| Route | Authentication owner | Proxy behavior | Typical client |
| --- | --- | --- | --- |
| `private-web` | `oauth2-proxy` | Overwrites identity headers and strips `Authorization` | Browser or standard service JWT |
| `public-web` | None | Intentionally bypasses `auth_request` | Anonymous HTTP client |
| `machine-api` | Backend | Preserves `Authorization` and clears identity headers | Software with backend-specific bearer token |
| `headless` | Service protocol | No nginx vhost discovery | TCP/UDP or non-HTTP client |
| `mcp` | MCP backend | Preserves bearer token and clears identity headers | OAuth MCP client |

Classify by who authenticates the request, not by whether the caller is human or
software. A scripted request using the standard Braingeneers service-account JWT
normally remains `private-web` because `oauth2-proxy` validates that token.

## Private Web

Expected Compose wiring:

- Registry-published `image:` and internal `expose:` port.
- `VIRTUAL_HOST`, `VIRTUAL_PORT`, `LETSENCRYPT_HOST`, and
  `LETSENCRYPT_EMAIL` in dictionary-form `environment:`.
- Membership in `braingeneers-net`.
- Default authentication inherited from `service-proxy/default`.

The protected proxy may supply these application-facing headers:

- `X-User`
- `X-Email`
- `X-Groups`
- `X-Name`
- `X-Given-Name`
- `X-Family-Name`
- `X-Preferred-Username`
- `X-Subject`

Header population depends on the deployed identity provider and route. Trust
these names only when the application is reachable solely through the protected
proxy, which overwrites them. Verify a route before depending on a specific
field and do not log identity headers during diagnosis.

The validated Workflows route supplies a usable `X-Email`; `X-User` is an
opaque CILogon subject and the other configured fields are empty. This finding
is Workflows-specific and must not be generalized to another application.

### Private-Web Proxy Invariants

- Keep every `proxy_set_header` directive at vhost scope. Nginx inherits the
  parent set only when the current location defines none. Adding one to a
  generated `<hostname>_location` silently loses the trusted identity overrides
  and downstream `Authorization` stripping.
- Put service-specific headers such as websocket `Upgrade` and `Connection` at
  vhost scope after including the default policy. Keep `_location` files for
  buffering, timeouts, body limits, and similar non-header directives.
- Inside `location = /_oauth2_proxy_auth`, retain
  `proxy_pass_request_body off` and `proxy_set_header Content-Length ""`.
  Authentication subrequests do not receive the original request body; keeping
  its length makes authenticated POST, PUT, and PATCH requests hang.
- After changing an authenticated vhost or `_location`, inspect it for
  location-level `proxy_set_header` directives and run `make test`.

## Public Web

Use only when the service is intentionally public:

- Keep normal `VIRTUAL_HOST` discovery and shared TLS.
- Add a host-specific `service-proxy/<hostname>` with `auth_request off`.
- Mount that file into `service-proxy` from `docker-compose.yaml`.
- Treat all identity-looking request headers as untrusted client input.

Example: `service-proxy/spikelab.braingeneers.gi.ucsc.edu`.

## Custom Proxy Directives

Use host-specific vhost or `_location` files for a concrete service need such
as body limits, disabled buffering, long timeouts, websocket handling, or custom
logs. Do not add a proxy override merely to document a service.

Examples:

- `service-proxy/uploader.braingeneers.gi.ucsc.edu`
- `service-proxy/uploader.braingeneers.gi.ucsc.edu_location`
- `service-proxy/data-explorer.braingeneers.gi.ucsc.edu_location`

## Machine API

Use this route only when the backend owns bearer-token validation:

- Keep shared edge discovery and TLS.
- Add a host-specific vhost file and matching Compose mount.
- Set `auth_request off`.
- Preserve `Authorization` with
  `proxy_set_header Authorization $http_authorization`.
- Clear every proxy-trusted identity-header name listed above.
- Bound body size and timeouts to the API contract.
- Require backend authentication and authorization on every non-health route.

Do not copy the `notification-service` route: it intentionally uses standard
proxy JWT validation and has no backend bearer-token validator.

## Headless

Headless services use explicit `ports:` when external TCP or UDP access is
required. Do not give them `VIRTUAL_HOST`, `LETSENCRYPT_HOST`, or vhost files
unless they also expose a separate HTTP UI. Join `braingeneers-net` only when
the service needs Compose peer communication, and load `secrets.md` when it
needs shared credentials.

Examples include MQTT and RustDesk. Consult their owning README and wiki page
instead of copying historical Compose wiring.

## MCP

MCP services are OAuth protected resources:

- Stay behind shared edge TLS.
- Disable browser-style `oauth2-proxy` enforcement for MCP traffic.
- Preserve `Authorization` end to end.
- Clear proxy-trusted identity headers.
- Validate issuer, JWKS, audience, and resource-server URL in the backend.
- Mount `./iam` read-only and use a service-specific IAM policy.

Use `service-proxy/mcp-resource-server.template` as the baseline and read
`docs/mcp-onboarding.md`, `oauth2-broker/README.md`, and the wiki MCP
architecture before implementation.

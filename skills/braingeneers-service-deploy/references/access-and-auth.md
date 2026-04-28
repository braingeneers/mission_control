# Access And Auth

Use this reference when the user needs access, kubeconfig, web auth, or token guidance.

## Access Checklist

Before deploying or operating services, verify the user has:

- GI server access to `braingeneers.gi.ucsc.edu`; the wiki permissions page says GI public server accounts require PI approval and a separate request for `braingeneers.gi.ucsc.edu`.
- Braingeneers GitHub access for `mission_control`.
- Braingeneers NRP namespace access if they will use Kubernetes secrets or validate secret availability.
- Docker or registry credentials if they will push images.

Relevant local sources:

- `../wiki/shared/permissions.md`
- `../wiki/shared/onboarding.md`
- `../wiki/shared/prp.md`
- `README.md`

## NRP Kubeconfig Paths

Be explicit about two different kubeconfig modes:

- Interactive user kubeconfig: downloaded from the NRP portal; current NRP docs require the `kubelogin` plugin for this flow. If the user is setting this up now, verify official NRP docs because this is external platform behavior.
- Service-account kubeconfig: useful for scripted or server-side access. `mission_control` already uses a service-account kubeconfig pattern, including a downloadable config exposed by the `service-accounts` service and secret-mounted kubeconfigs for containers.

On `braingeneers.gi.ucsc.edu`, prefer the service-account kubeconfig pattern when operating the Compose stack, because lab operators may not have admin access on that host to install `kubelogin` system-wide.

Secret access is ultimately a Kubernetes authorization check against the Braingeneers namespace. `secret-fetcher` can only populate `/secrets` if the kubeconfig it sees can list and read namespace secrets.

## Browser Web Auth

Ordinary browser-facing web services sit behind `service-proxy`, which uses `auth_request` against `oauth2-proxy`. Unauthenticated users are sent through Auth0 and CILogon. The default proxy also strips the downstream `Authorization` header before proxying to the backend, so do not assume a normal web backend will receive bearer tokens.

Relevant local sources:

- `README.md`
- `service-proxy/default`
- `oauth2-proxy/oauth2-proxy.cfg`

## Service-Account JWTs

The `service-accounts` service generates broad Auth0-backed service-account JWTs. For local interactive user bootstrap, `braingeneerspy` can use `python -m braingeneers.iot.authenticate`.

For services deployed under `mission_control`, prefer the refreshed runtime token:

- Source secret: `braingeneers-jwt-service-account-token`
- Runtime file: `/secrets/braingeneers-jwt-service-account-token/config.json`
- Refreshed by: `service-account-jwt-token-refresh`

Do not recommend copying `/secrets/service-accounts/config.json` into the runtime `braingeneerspy` service-account path for long-running unattended services unless the existing service is known to rely on that older pattern and the tradeoff is explicit.

Relevant local sources:

- `README.md`
- `docker-compose.yaml`
- `service-accounts/app/token_service.py`
- `cron-braingeneers-jwt-token-refresh/refresh-braingeneers-jwt-service-account-token.sh`

## MCP Auth

MCP services do not use normal browser-session enforcement for MCP traffic. They should validate bearer tokens in the backend as OAuth protected resource servers. Current MCP helper-user flows use the self-hosted broker at `oauth2.braingeneers.gi.ucsc.edu` and local `braingeneerspy` stdio helper paths.

Relevant local sources:

- `docs/mcp-onboarding.md`
- `../wiki/shared/mcp_architecture.md`
- `oauth2-broker/README.md`

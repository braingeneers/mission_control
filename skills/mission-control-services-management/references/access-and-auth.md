# Access And Auth

Use this reference when the user needs access, kubeconfig, web auth, or token guidance.

- [Access checklist](#access-checklist)
- [NRP kubeconfig paths](#nrp-kubeconfig-paths)
- [Browser web auth](#browser-web-auth)
- [Service-account JWTs](#service-account-jwts)
  - [Local HTTPS API diagnosis](#local-https-api-diagnosis)
- [MCP auth](#mcp-auth)

## Access Checklist

Before deploying or operating services, verify the user has:

- GI server access to `braingeneers.gi.ucsc.edu`; the wiki permissions page says GI public server accounts require PI approval and a separate request for `braingeneers.gi.ucsc.edu`.
- Braingeneers GitHub access for `mission_control`.
- Braingeneers NRP namespace access if they will use Kubernetes secrets or validate secret availability.
- Docker or registry credentials if they will push images.

Relevant sources. Use a local checkout of `github.com/braingeneers/wiki` when available; otherwise use the GitHub links:

- `shared/permissions.md`: https://github.com/braingeneers/wiki/blob/main/shared/permissions.md
- `shared/onboarding.md`: https://github.com/braingeneers/wiki/blob/main/shared/onboarding.md
- `shared/prp.md`: https://github.com/braingeneers/wiki/blob/main/shared/prp.md
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

The standard Auth0 service-account JWT authenticates HTTPS requests to ordinary
Braingeneers web services protected by `oauth2-proxy`; it is not limited to one
application. Send it as `Authorization: Bearer <token>` to the service's documented
`/api/...` endpoint. The proxy consumes that header for authentication and strips it
before forwarding the request to an ordinary private-web backend. MCP routes use a
separate backend-validation contract and must not assume this pattern.

### Local HTTPS API Diagnosis

Prefer the operator-managed local token when it exists:

```bash
operator_token_file="${HOME}/.ssh/braingeneers_jwt_token.json"
if [ -s "${operator_token_file}" ]; then
    token_file="${operator_token_file}"
fi
```

This JSON file contains `access_token` and `expires_at`. Require owner-only file
permissions, never print its contents, and validate the JWT's embedded `exp` below
before every use.

If the operator-managed file is absent, discover the token through the active Python
environment rather than assuming a fixed checkout, Conda environment, or
site-packages path:

```bash
if [ -z "${token_file:-}" ]; then
    token_file="$(python - <<'PY'
from pathlib import Path
import braingeneers.iot

candidates = [
    Path(package_path) / "service_account" / "config.json"
    for package_path in braingeneers.iot.__path__
]
print(next((path for path in candidates if path.is_file()), candidates[0]))
PY
)"
fi
```

Run these commands from a Python environment that has `braingeneerspy` installed.
The package-path approach supports Python versions that predate
`importlib.resources.files()` and also follows editable installs.

If the file is missing, generate it interactively with:

```bash
python -m braingeneers.iot.authenticate
```

For routine refresh, ask `braingeneerspy` to check the stored token without opening
MQTT or Redis connections:

```bash
python - <<'PY'
import io
from braingeneers.iot.messaging import MessageBroker

token_data = MessageBroker(
    credentials_file=io.StringIO(""),
).jwt_service_account_token
print("Declared expires_at:", token_data.get("expires_at", "missing"))
PY
```

Re-run the embedded-expiration check below after refreshing. The current helper
uses the surrounding `expires_at` value to decide whether to refresh; if that value
is later than the embedded `exp`, regenerate interactively instead.

Validate the JWT's embedded `exp` claim without printing the credential. Treat the
embedded claim as authoritative if it disagrees with the surrounding JSON
`expires_at` value:

```bash
python - "$token_file" <<'PY'
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import stat
import sys

token_path = Path(sys.argv[1])
if stat.S_IMODE(token_path.stat().st_mode) & 0o077:
    raise SystemExit("JWT file must have owner-only permissions.")
token_data = json.loads(token_path.read_text(encoding="utf-8"))
token = token_data["access_token"]
payload_part = token.split(".")[1]
payload_part += "=" * (-len(payload_part) % 4)
payload = json.loads(base64.urlsafe_b64decode(payload_part))
expires_at = datetime.fromtimestamp(payload["exp"], timezone.utc)
print("JWT exp:", expires_at.isoformat())
print("Declared expires_at:", token_data.get("expires_at", "missing"))
if expires_at <= datetime.now(timezone.utc):
    raise SystemExit("JWT is expired; regenerate it before making API requests.")
PY
```

Load the token without echoing it and call a read-only API endpoint:

```bash
service_url="https://SERVICE.braingeneers.gi.ucsc.edu"
api_path="/api/HEALTH-OR-STATUS-ENDPOINT"
bearer_token="$(python - "$token_file" <<'PY'
import json
from pathlib import Path
import sys

print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["access_token"])
PY
)"
curl --silent --show-error --fail \
  --location --max-redirs 0 \
  -H "Authorization: Bearer ${bearer_token}" \
  "${service_url}${api_path}"
unset bearer_token
```

Use the same pattern for any ordinary protected Braingeneers web-service API. For
Data Explorer paths, searches, and downloads, use the `data-explorer-cli-access`
skill when it is available.

An unexpected `302` redirect to the login service means the proxy did not accept
the bearer request. Confirm that the header was sent, inspect the embedded `exp`,
and regenerate the token with `python -m braingeneers.iot.authenticate` if it is
expired or rejected. Do not trust a later wrapper `expires_at` when the embedded
JWT has already expired, and never print or paste the token into commands, logs,
source files, shell history, or chat. Capturing it directly into a shell variable
for the bearer header is acceptable; do not echo that variable.

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
- Braingeneers wiki `shared/mcp_architecture.md`: https://github.com/braingeneers/wiki/blob/main/shared/mcp_architecture.md
- `oauth2-broker/README.md`

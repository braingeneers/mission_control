# Access And Authentication

Use this reference for production web/API access, service-account JWTs,
kubeconfig selection, and identity-provider boundaries.

- [Choose the access surface](#choose-the-access-surface)
- [Browser authentication](#browser-authentication)
- [Local HTTPS API diagnosis](#local-https-api-diagnosis)
- [NRP and secret access](#nrp-and-secret-access)
- [MCP authentication](#mcp-authentication)

## Choose The Access Surface

- Use a signed-in browser for rendered state, navigation, or interaction.
- Use a protected HTTPS API with the standard service-account JWT for semantic
  data, health, status, searches, and read-only diagnosis.
- For Data Explorer paths, listings, searches, and downloads, use the
  `data-explorer-cli-access` skill when available. Follow the JWT precedence in
  this reference and the Data Explorer skill for source-relative API paths.
- Give the operator commands for anything that must run on
  `braingeneers.gi.ucsc.edu`. Never SSH there or run its Compose commands from
  the local workstation.

If a request combines semantic evidence and visual evidence, validate each on
its appropriate surface and report them separately.

## Browser Authentication

Ordinary browser-facing services sit behind `service-proxy`, which performs an
`auth_request` against `oauth2-proxy`. Unauthenticated users are sent through
Auth0 and CILogon.

The protected proxy overwrites trusted identity-header names and strips the
downstream `Authorization` header. A normal private-web backend should rely only
on identity headers supplied through that protected route; it should not expect
to validate the browser or service-account bearer token itself. Header
population varies by route and identity provider, so verify a deployed route
before making an application depend on a particular field.

Relevant local sources:

- `service-proxy/default`
- `oauth2-proxy/oauth2-proxy.cfg`
- the matching service and proxy override in `docker-compose.yaml`

## Local HTTPS API Diagnosis

The standard Auth0 service-account JWT authenticates HTTPS requests to ordinary
Braingeneers private-web APIs. Send it as `Authorization: Bearer <token>` to a
documented `/api/...` endpoint. `oauth2-proxy` validates the token, and nginx
removes it before forwarding the request to the application. MCP and true
machine-api routes use different backend-validation contracts.

### 1. Locate The Token

Prefer the operator-managed file when present:

```bash
operator_token_file="${HOME}/.ssh/braingeneers_jwt_token.json"
if [ -s "${operator_token_file}" ]; then
    token_file="${operator_token_file}"
fi
```

If it is absent, discover the active `braingeneerspy` package path instead of
assuming a checkout, Conda environment, Python version, or site-packages path:

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

Run this from an environment with `braingeneerspy` installed. If the file does
not exist, generate it interactively:

```bash
python -m braingeneers.iot.authenticate
```

### 2. Validate Permissions And Embedded Expiry

The JSON wrapper contains `access_token` and `expires_at`, but the JWT's embedded
`exp` claim is authoritative. Never print the token or file contents.

```bash
python - "${token_file}" <<'PY'
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
payload_part = token_data["access_token"].split(".")[1]
payload_part += "=" * (-len(payload_part) % 4)
payload = json.loads(base64.urlsafe_b64decode(payload_part))
expires_at = datetime.fromtimestamp(payload["exp"], timezone.utc)
print("JWT exp:", expires_at.isoformat())
print("Declared expires_at:", token_data.get("expires_at", "missing"))
if expires_at <= datetime.now(timezone.utc):
    raise SystemExit("JWT is expired; regenerate it before making requests.")
PY
```

The owner-only rule applies to either token location. If the wrapper expiry is
later than embedded `exp`, regenerate the credential rather than trusting the
wrapper.

For routine `braingeneerspy` refresh without opening MQTT or Redis connections:

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

Re-run the embedded-expiry check after refresh. If refresh does not replace a
JWT whose embedded `exp` is stale, authenticate interactively again.

### 3. Make A Read-Only Request

Load the bearer token directly into a shell variable, never echo it, and unset
it immediately after the request:

```bash
service_url="https://SERVICE.braingeneers.gi.ucsc.edu"
api_path="/api/HEALTH-OR-STATUS-ENDPOINT"
bearer_token="$(python - "${token_file}" <<'PY'
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

An unexpected `302` to the login service means the proxy did not accept the
bearer request. Confirm that the header was sent, recheck embedded `exp`, and
regenerate the token if necessary. Never paste a token into chat, source,
command output, logs, or shell history.

## NRP And Secret Access

Do not conflate web-service JWTs with Kubernetes credentials:

- **Interactive user kubeconfig:** downloaded from the NRP portal and currently
  requires `kubelogin`. Verify current official NRP documentation when helping
  a user set it up.
- **Service-account kubeconfig:** preferred for unattended or server-side
  Mission Control use, where operators may not be able to install `kubelogin`.

`secret-fetcher` can populate `/secrets` only when its kubeconfig may list and
read Secrets in the Braingeneers namespace. The agent must not mutate those
Secrets; missing permissions or credentials require operator escalation.

Access prerequisites and onboarding are documented in the local wiki files
`shared/permissions.md`, `shared/onboarding.md`, and `shared/prp.md`.

## MCP Authentication

MCP traffic does not use the ordinary private-web bearer-consumption pattern.
MCP routes preserve `Authorization`, clear proxy-trusted identity headers, and
require the backend to validate OAuth bearer tokens and IAM. Read
`docs/mcp-onboarding.md`, `oauth2-broker/README.md`, the MCP proxy template, and
the wiki MCP architecture before changing or diagnosing MCP authentication.

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

Prefer the local file `~/.ssh/braingeneers_jwt_token.json` when present:

```bash
operator_token_file="${HOME}/.ssh/braingeneers_jwt_token.json"
token_file=""
if [ -f "${operator_token_file}" ]; then
    token_file="${operator_token_file}"
fi
```

If it is absent, discover the active `braingeneerspy` package path instead of
assuming a checkout, Conda environment, Python version, or site-packages path:

```bash
if [ -z "${token_file:-}" ]; then
    token_file="$(python - <<'PY'
from pathlib import Path

try:
    import braingeneers.iot
except ImportError:
    candidates = []
else:
    candidates = [
        Path(package_path) / "service_account" / "config.json"
        for package_path in braingeneers.iot.__path__
    ]
print(next(
    (path for path in candidates if path.is_file()),
    Path.home() / ".ssh" / "braingeneers_jwt_token.json",
))
PY
)"
fi
```

Package discovery uses the active Python environment when `braingeneerspy` is
installed. If neither location has a credential, or the package is unavailable,
the default is `~/.ssh/braingeneers_jwt_token.json` for browser setup below.
Keep the selected path through validation and renewal; do not silently fall
back to another file because the selected token is empty, malformed, or expired.

### 2. Browser Setup Or Interactive Renewal

For a missing, expired, or rejected credential, offer the user this direct link:
[Generate a service-account token](https://service-accounts.braingeneers.gi.ucsc.edu/generate_token).
They sign in through the normal browser flow. The complete JSON response belongs
in the selected `token_file`, with owner-only permissions (`0600`). Have them
enter it only in their local terminal or save it locally from the browser;
never ask for it in chat or put it in a shell command or shell history.
Validate the JSON and embedded expiry before replacing an existing file, using
the atomic-save procedure in step 4.

Alternatively, from an environment containing `braingeneerspy`, offer:

```bash
python -m braingeneers.iot.authenticate
```

This command opens the same page and prompts for its complete JSON in the user's
terminal. It saves the package's `service_account/config.json`, not the preferred
`~/.ssh` file. If a different `token_file` was selected, validate the result and
securely copy it to that selected path using the same atomic-save procedure;
otherwise rediscover the package path. Ensure owner-only permissions, reload,
and validate the selected file before continuing.

### 3. Validate Permissions And Embedded Expiry

The JSON wrapper contains `access_token` and `expires_at`, but the JWT's embedded
`exp` claim is authoritative. Never print the token or file contents.

```bash
python - "${token_file}" <<'PY'
import base64
from datetime import datetime, timedelta, timezone
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
remaining = expires_at - datetime.now(timezone.utc)
if remaining <= timedelta(0):
    raise SystemExit("JWT is expired; use browser setup or interactive renewal.")
print("Automatic renewal due:", remaining <= timedelta(days=7))
PY
```

The owner-only rule applies to either token location. Use embedded `exp` for
all expiry decisions. A different wrapper `expires_at` alone is not a reason
to renew; the wrapper may overstate the actual lifetime. Decoding claims checks
expiry only; the protected service verifies the JWT's signature and access.

### 4. Automatically Renew Within Seven Days

During an API task, when `0 < exp - now <= 604800` seconds, renew the local
credential automatically without asking for confirmation. This is expected
credential maintenance, like the automatic renewal performed by `braingeneerspy`;
the threshold for this skill is seven days. It does not authorize application
mutations, production operations, or Kubernetes Secret changes.

1. Make one HTTPS `GET` to
   `https://service-accounts.braingeneers.gi.ucsc.edu/generate_token`, with the
   selected still-valid token in `Authorization: Bearer <token>`. Keep the token
   and response in process memory, leave TLS verification enabled, use a bounded
   timeout (for example, 30 seconds), and disable redirects. Never print request
   headers, the response body, or credential-bearing exception details.
2. Require HTTP `200` and a JSON object containing a nonempty `access_token` and
   `expires_at`. Decode the returned JWT and require a valid embedded `exp` in
   the future and later than the selected token's `exp`. Do not save a login
   page, error response, malformed token, or response that fails to extend expiry.
3. Save the validated JSON to a temporary file in the selected file's directory,
   with mode `0600` from creation, then atomically replace that selected file
   (for example, `os.replace`). Preserve the original on validation or write
   failure. Apply this procedure to either local credential location; do not
   refresh only the package copy when the `~/.ssh` file was selected.
4. Reload and revalidate the saved file, then notify the user that renewal
   succeeded, naming the path and new embedded expiry only. Continue the
   requested task. Do not wait for acknowledgment.

Attempt automatic renewal at most once per task. If it fails, preserve the
original file and report a sanitized reason; continue authorized API requests
while that credential remains valid and accepted. If a new token still expires
within seven days, report its short lifetime rather than repeatedly renewing.
For missing, malformed, expired, or rejected credentials, offer step 2. A fresh
valid token that is still rejected requires access/admin help, not a renewal loop.

### 5. Make A Read-Only Request

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
use step 2 if the credential is expired or rejected. Never paste a token into
chat, source, command output, logs, or shell history.

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

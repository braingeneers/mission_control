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

### 1. Check Existing Sign-In

Use the bundled [sign-in helper](../scripts/authenticate.py) with an available
Python 3 interpreter; it needs no third-party packages. `<SKILL>` below means
this skill's absolute installed directory. Run this check without opening a browser:

```bash
python3 "<SKILL>/scripts/authenticate.py" --check
```

The helper prefers an existing `~/.ssh/braingeneers_jwt_token.json`, otherwise
an existing active `braingeneerspy` package's `service_account/config.json`.
With neither present, it selects `~/.ssh/braingeneers_jwt_token.json`. Honor an
explicitly established user path with `--token-file /absolute/path` on every
helper invocation. Keep that selection throughout setup, checking, API use and
renewal; do not switch files because the selected one is expired or malformed.
`--path` prints only the selected path, so the agent can set `token_file` for
subsequent API requests without reading a credential into tool output.

### 2. Guide First-Use Sign-In Through Completion

When a requested API task needs sign-in, actively walk the user through it.
Do not stop at “API not set up,” require them to understand JWT/service accounts,
or substitute S3 access for the requested Data Explorer operation. A purely
explanatory question does not require authentication.

Use plain language, for example:

> To find your datasets, first sign in with the academic account you use for
> Braingeneers web services—UCSC or your institution.
> [Sign in to Braingeneers](https://service-accounts.braingeneers.gi.ucsc.edu/generate_token).
> I'll help connect this computer, then continue the search.

Choose the least manual supported transfer, without promising browser abilities
that have not been verified:

- If browser tools can transfer the response privately to a local file without
  putting it in chat, screenshots, tool output or logs, open the login page and
  let the user complete institutional sign-in/MFA themselves. Import that local
  response with the helper below. Do not extract credentials through an ordinary
  browser snapshot or return them from a browser evaluation.
- Otherwise use the bundled helper in **a terminal the user can actually type
  into**. If agent terminals are not user-interactive, give the user the exact
  command with the resolved absolute skill path to run in their own terminal.
  First establish that this terminal runs in the same environment/filesystem
  the agent can access; a path on the agent’s remote machine may not exist on
  the user’s laptop. For a remote agent, use a user-accessible terminal in that
  environment or a supported private file transfer. Never send the response
  through chat to bridge computers. Do not claim setup completed until the
  agent can check the selected file in its own environment.
  Do not start an inaccessible agent PTY and wait for input. The helper opens
  the login page and privately accepts the complete response copied from it:

  ```bash
  python3 "<SKILL>/scripts/authenticate.py"
  ```

  Tell the user to sign in, copy the entire response shown by the page, paste
  into the helper's terminal prompt, and press Enter twice. The paste stays
  hidden, including formatted multiline responses. They need not create a file,
  choose a directory, or set permissions. Keep the clickable login link available
  if a browser cannot open, including when the terminal runs remotely.
- If terminal pasting is unavailable, ask them to save/download the complete
  response locally using their browser and give **only its path**, never its
  contents. The agent handles the import and destination:

  ```bash
  python3 "<SKILL>/scripts/authenticate.py" --import-file /absolute/path/to/response.json
  ```

The helper validates the response and embedded expiry, saves atomically with
owner-only permissions, and preserves existing credentials on cancellation or
failure. For a permissions-only problem, import the selected file itself to
secure it without requiring another login. After a successful import from a
separate downloaded file, tell the user that the download also contains their
private sign-in and should be removed from Downloads using their normal trash.
Never print it or ask them to paste it in chat, a shell command, or shell history.
If canceled, pause dependent API work; do not treat cancellation as success.
If institutional access is denied, explain that lab access may need approval
and direct them to the lab's documented access/support route.

The existing package command remains an alternative when the user prefers it:

```bash
python -m braingeneers.iot.authenticate
```

It also opens the page and requires copying its response into the user's
terminal; it does not capture the browser response automatically. It saves
inside the active package, which may differ from the selected file. Import
that package file into the selected destination using the bundled helper and
verify permissions afterward. Do not install braingeneerspy just for sign-in.

### 3. Verify And Resume

Rerun `--check` on the selected file. It reports only the path, embedded expiry
and whether renewal is due; it never displays the credential. The JWT's `exp`
is authoritative; `expires_at` in the response wrapper does not override it.
Local decoding checks structure/expiry, **not** signature or service access.
Follow step 4 for a still-valid credential within seven days of expiry.

Then make a documented read-only protected API request (for Data Explorer,
`/api/sources`), with TLS verification enabled and redirects disabled. Confirm
an expected JSON success response, not a login page; only then say the connection
works and resume the user's original task. Do not stop after saving the file or
ask for a new task. A freshly issued credential that still gets rejected needs
access/admin help, not repeated login/renewal attempts.

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
For missing, malformed, expired, or rejected credentials, guide the user through
step 2. A fresh valid token that is still rejected requires access/admin help,
not a renewal loop.

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

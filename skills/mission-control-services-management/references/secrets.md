# Secrets And Runtime Credentials

Use this reference for `secret-fetcher`, mounted secret files, entrypoint setup,
and runtime token refresh. It does not authorize the agent to mutate a
Kubernetes Secret.

## Ownership Boundary

Kubernetes Secret creation, patching, replacement, and deletion are
operator-owned. The agent may:

- inspect tracked configuration and public secret-name/key contracts;
- diagnose whether a mounted file is expected;
- give an authorized operator exact mutation or refresh instructions;
- wait for sanitized status or existence checks.

The agent must not read, decode, print, modify, or submit secret values. Read the
wiki administrator guidance before advising an operator on a mutation, and do
not present administrator procedures as ordinary self-service.

## Materialization Model

`secret-fetcher` uses its Kubernetes credentials to list and read Secrets in the
Braingeneers namespace, decodes each key, and writes it into the shared in-memory
`secrets` Docker volume:

```text
/secrets/<kubernetes-secret-name>/<key>
```

The kubeconfig visible to `secret-fetcher` must have the required namespace
permissions. The shared volume keeps credentials out of images and Git, but it
does not strongly isolate one secret-mounted service from another; do not
overstate that trust boundary.

Relevant sources:

- `secret-fetcher/download-secrets.sh`
- `secret-fetcher/Dockerfile`
- `secret-fetcher/entrypoint-secrets-setup.sh`
- the consuming service in `docker-compose.yaml`

## Compose Contract

A service that needs fetched credentials normally has:

```yaml
volumes:
  - secrets:/secrets
depends_on:
  secret-fetcher:
    condition: service_healthy
```

Read the exact file under `/secrets/<name>/<key>`. Do not bake credentials into
the image, commit them, add service-specific host credential files, or convert a
public configuration value into a pseudo-secret.

## Entrypoint Setup

Use `/secrets/entrypoint-secrets-setup.sh` only when the application cannot read
the fetched location directly:

- `--copy <source>:<destination>` copies a credentials file, kubeconfig, SSH
  key, service-account token, or similar file to the path expected by the app.
- `--env <file>` exports a genuinely secret-backed env file before executing the
  application.

Prefer an application setting that accepts an exact secret-file path. Stable
runtime defaults belong in the image or owning repository, and deployment-only
public values may remain normal Compose environment entries.

## Runtime Service-Account Token

Unattended `braingeneerspy` services should use the refreshed token at:

```text
/secrets/braingeneers-jwt-service-account-token/config.json
```

`service-account-jwt-token-refresh` refreshes the source Secret. Avoid the older
raw `/secrets/service-accounts/config.json` runtime pattern unless an existing
service deliberately depends on it and the tradeoff is documented.

This runtime token is distinct from the NRP-hosted LLM API key and from MCP
backend bearer tokens. Load `hosted-llms.md` or the MCP authentication guidance
instead of substituting credentials.

## Diagnosis And Refresh Handoff

Common causes of missing credentials:

- `secret-fetcher` cannot authenticate or lacks namespace permissions;
- the Kubernetes Secret name or key differs from the mounted path;
- `secret-fetcher` has not been recreated since an operator changed a Secret;
- `--copy` or `--env` points to the wrong source or application destination;
- the consuming service was not recreated after refreshed materialization.

Ask the operator to check file existence or size without printing content, then
refresh only `secret-fetcher` and the affected consumer when required. Inspect
bounded logs for names and status, never values. Missing Slack, DKIM, LLM, or
other provider credentials should follow the owning reference's documented
degraded behavior rather than introducing an insecure fallback.

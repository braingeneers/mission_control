# Secrets And Runtime Credentials

Use this reference for `secret-fetcher`, mounted secret files, entrypoint setup,
and runtime token refresh.

## Ownership Boundary

Agents may verify Secret and key presence through authorized read-only
Kubernetes access and check sanitized consumer status through approved HTTPS
APIs. Keep credential values in the existing fetcher and application paths,
with no raw or decoded values in agent output, commands, logs, or local copies.
Kubernetes Secret mutations and production host operations are
operator-owned. Read the wiki administrator guidance before advising an
operator on a mutation.

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

### Verify Before Handoff

1. Use the authorized workstation kubeconfig and explicit namespace to
   check the exact Secret and data key. Project a boolean with `kubectl`
   instead of requesting YAML, JSON, or the field value. Replace `SECRET_NAME`
   and `KEY_NAME` with the expected names.

   ```bash
   kubectl --namespace braingeneers get secret SECRET_NAME \
     -o go-template='{{if index .data "KEY_NAME"}}present-and-nonempty{{else}}missing-or-empty{{end}}{{"\n"}}'
   ```

   A successful check establishes presence with the workstation identity.
   An authorization error requires an authorized operator or an existing
   consumer signal.
2. Trace the shared volume, exact `/secrets/<name>/<key>` path, any entrypoint
   copy or environment mapping, and how the pinned image reads the result.
   The fetcher's current health check sees a completion marker. A failed
   Kubernetes read can still leave the fetcher healthy.
3. Prefer a documented read-only HTTPS signal from the live consumer or an
   established consumer of the same shared key. Check what its status
   actually measures. An existing consumer can confirm the shared mount,
   while the target's status or a normal operation can verify its own
   access and upstream authentication.

Ask the operator for a targeted check only when the remaining uncertainty
matters for the rollout. For a running consumer, this checks the exact path
without displaying its contents. The command succeeds only for a readable,
nonempty file.

```bash
docker compose exec -T SERVICE sh -c 'test -r "$1" && test -s "$1"' sh /secrets/SECRET_NAME/KEY_NAME
```

### Refresh After A Secret Change

`secret-fetcher` populates the volume at startup. When an operator adds or
rotates a key or diagnoses stale materialization, have them recreate
`secret-fetcher` with `docker compose up -d --no-deps --force-recreate secret-fetcher`
and verify the affected consumer. Recreate the consumer when it copies or
caches credentials at startup. A routine application image update using a
verified existing key follows the normal
[targeted pull and recreate](operations.md#targeted-service-operations).
Missing provider credentials follow the owning reference's documented
degraded behavior.

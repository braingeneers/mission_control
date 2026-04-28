# Secrets

Use this reference for Kubernetes secrets, `secret-fetcher`, runtime mounts, and token refresh.

## Model

Credentials live in Kubernetes secrets in the Braingeneers namespace. `secret-fetcher` reads those secrets with `kubectl`, decodes every key, and writes files into a shared in-memory Docker volume mounted at `/secrets`.

Shape:

- Kubernetes secret name becomes `/secrets/<secret-name>/`.
- Each key becomes a file under that directory.
- Services consume those files through the shared `secrets:/secrets` volume.

The kubeconfig visible to `secret-fetcher` must be able to list and get secrets in the Braingeneers namespace.

Relevant local sources:

- `secret-fetcher/download-secrets.sh`
- `secret-fetcher/Dockerfile`
- `docker-compose.yaml`
- `README.md`

## Service Compose Pattern

When a service needs secrets:

- Mount `secrets:/secrets`.
- Add `depends_on: secret-fetcher: condition: service_healthy`.
- Read files from `/secrets/<secret-name>/<key>`.

Do not put credentials in Docker images or Git-tracked service source.

## Entrypoint Wrapper

Use `/secrets/entrypoint-secrets-setup.sh` when secrets must be moved or exported before the real process starts.

Supported operations:

- `--copy` takes a `from:to` path and copies a fetched secret file into the location the application expects.
- `--env` reads a secret-backed env file and exports its key-value pairs before launching the final command.

Use `--copy` for credentials files, kubeconfigs, SSH keys, RustDesk keys, or `braingeneerspy` runtime token files.

Use `--env` for services with secret-backed environment files such as Auth0, database, or Keycloak variables.

## Creating And Replacing Secrets

Separate ordinary-user and admin workflows:

- Ordinary users should know where secrets come from and when to ask for help.
- Admins can use the wiki-documented delete-then-create replacement pattern.

Docs to read before advising. Use a local checkout of `github.com/braingeneers/wiki` when available; otherwise use the GitHub links:

- `shared/prp.md`: https://github.com/braingeneers/wiki/blob/main/shared/prp.md
- `shared/administrators.md`: https://github.com/braingeneers/wiki/blob/main/shared/administrators.md

After adding or replacing a Kubernetes secret, restart or recreate `secret-fetcher` and watch its logs to confirm the new secret and keys were fetched. Services that depend on the changed secret may also need a targeted recreate.

## Service-Account Runtime Token

For unattended services using `braingeneerspy`, prefer:

- `/secrets/braingeneers-jwt-service-account-token/config.json`

That secret is refreshed by the `service-account-jwt-token-refresh` service. It calls the internal `service-accounts` endpoint and updates the Kubernetes secret daily.

Avoid recommending the older raw `/secrets/service-accounts/config.json` runtime pattern unless preserving existing service behavior is the explicit goal.

## Secret Debugging

Common symptoms:

- `secret-fetcher` unhealthy: kubeconfig cannot authenticate, namespace access is missing, or Kubernetes API is unreachable.
- File missing under `/secrets`: wrong Kubernetes secret name, wrong key name, or `secret-fetcher` has not refreshed since the secret changed.
- Env missing in app: `--env` path is wrong, env file format is incompatible with the wrapper, or service was not recreated.
- App cannot find credentials: `--copy` target path does not match what the app library expects.

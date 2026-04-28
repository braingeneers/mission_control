---
name: braingeneers-service-deploy
description: Build, deploy, update, or troubleshoot Braingeneers lab services managed by mission_control on braingeneers.gi.ucsc.edu. Use when Codex is helping create a new Docker Compose service, choose between proxied web, public web, headless port-published, or MCP service patterns, configure service-proxy overrides, handle Braingeneers Kubernetes secrets and secret-fetcher, choose NRP kubeconfig authentication, package images for Docker Hub or another registry, add Makefile build/push/local-test workflows, or operate existing services with docker compose.
---

# Braingeneers Service Deploy

Use this skill for Braingeneers services managed by `mission_control` on `braingeneers.gi.ucsc.edu`.

## Start Here

1. Confirm the user is working in or referencing the `mission_control` repo and read its current `README.md`, `docker-compose.yaml`, `service-proxy/`, `secret-fetcher/`, and relevant `../wiki` pages before advising or editing.
2. Route the service into one branch before proposing changes:
   - `private-web`: browser-authenticated service behind `service-proxy/default`.
   - `public-web`: web service intentionally bypassing browser auth with a host-specific `service-proxy` override.
   - `headless`: non-HTTP or direct-port service such as MQTT or RustDesk; do not route this through `VIRTUAL_HOST` or host-specific nginx vhost files.
   - `mcp`: MCP resource server; keep shared edge TLS, bypass browser auth for MCP traffic, preserve `Authorization`, and make the backend validate bearer tokens and IAM.
3. Check access prerequisites early. Users need GI server access to `braingeneers.gi.ucsc.edu`, Braingeneers GitHub access, and Braingeneers NRP namespace access for secret-related operations.
4. Prefer a published container image in Docker Hub, the PRP registry, or another registry over a server-local build. Use a small `Makefile` for repeatable `build`, `push`, `local-test` or `run-test`, and `shell` workflows when the service owns a custom image.
5. Treat secrets as Kubernetes namespace resources materialized by `secret-fetcher` into the shared `/secrets` volume. Do not bake credentials into images.

## Reference Loading

Load only the reference files needed for the current task:

- `references/access-and-auth.md`: server access, NRP kubeconfig, `kubelogin`, service-account kubeconfig, web auth, service-account JWTs.
- `references/service-routing.md`: private web, public web, headless, and MCP routing patterns.
- `references/packaging.md`: registry-published image policy and Makefile target conventions.
- `references/secrets.md`: Kubernetes secret lifecycle, secret-fetcher, entrypoint secret setup, and token refresh.
- `references/operations.md`: deployment, update, verification, troubleshooting, and escalation.

## Workflow

### 1. Build Context

Read local sources before making claims. Minimum source set:

- `README.md`
- `docker-compose.yaml`
- `service-proxy/default`
- Any matching `service-proxy/<hostname>` or `<hostname>_location` files
- `secret-fetcher/download-secrets.sh`
- `secret-fetcher/entrypoint-secrets-setup.sh`
- `../wiki/shared/permissions.md`
- `../wiki/shared/onboarding.md`
- `../wiki/shared/nrp_quickstart.md`
- `../wiki/shared/prp.md`
- `../wiki/shared/administrators.md` only when admin-only secret or Auth0 work is relevant

For MCP services, also read `docs/mcp-onboarding.md`, `../wiki/shared/mcp_architecture.md`, and `oauth2-broker/README.md`.

### 2. Choose The Service Branch

Use the branch to determine which details matter:

- `private-web`: add or update a Compose service with `VIRTUAL_HOST`, `VIRTUAL_PORT`, `LETSENCRYPT_HOST`, `LETSENCRYPT_EMAIL`, and `braingeneers-net`. Default browser auth comes from `service-proxy/default`.
- `public-web`: use the same Compose service discovery, plus a host-specific `service-proxy/<hostname>` override with `auth_request off`; add the matching bind mount under the `service-proxy` service.
- `headless`: use explicit `ports:` and network settings as needed. Do not add `VIRTUAL_HOST`, `LETSENCRYPT_HOST`, or service-proxy vhost files unless the service also has an HTTP UI.
- `mcp`: follow the MCP onboarding contract. Preserve bearer tokens, strip proxy identity headers, mount IAM read-only, and configure issuer, JWKS, audience, and resource-server URL explicitly.

### 3. Handle Auth And Access

Use the wiki for access instructions rather than restating long onboarding text. For NRP auth, be precise:

- User kubeconfigs downloaded from the NRP portal currently require `kubelogin`; verify current official NRP docs when the user is actively setting this up.
- On `braingeneers.gi.ucsc.edu`, the practical pattern is often the service-account kubeconfig already used by `mission_control`, because operators may not have admin access to install `kubelogin` system-wide.
- Secret access expects Kubernetes credentials with access to the Braingeneers namespace. This is the primary authentication challenge for `secret-fetcher`.

### 4. Package Before Deploying

Push custom images to a registry before adding them to production Compose. Prefer:

- A versioned or intentionally managed tag.
- A repeatable `Makefile` with `build`, `push`, `local-test` or `run-test`, and `shell` targets.
- Compose `image:` references to registry images for production services.

Avoid depending on `build:` in production service definitions unless there is a deliberate reason. Server-local builds make migration and future rebuilds fragile when upstream package versions change.

### 5. Wire Secrets Correctly

When a service needs secrets:

- Add `secrets:/secrets`.
- Add `depends_on: secret-fetcher: condition: service_healthy`.
- Use `/secrets/<kubernetes-secret-name>/<key>` paths.
- Use `/secrets/entrypoint-secrets-setup.sh` only when the app needs copied files or exported env vars before launch.
- Use `--copy` for files such as AWS credentials, kubeconfigs, SSH keys, or service-account token files.
- Use `--env` for secret-backed env files.

For unattended `braingeneerspy` services, prefer the daily refreshed `/secrets/braingeneers-jwt-service-account-token/config.json` mounted to the expected `braingeneers/iot/service_account/config.json` location. Do not recommend stale raw `service-accounts/config.json` patterns unless the local code specifically requires it and the risk is acknowledged.

### 6. Deploy Conservatively

For existing services, prefer targeted operations:

- Pull the target image.
- Recreate only the target service.
- Check logs and status for only the affected services.
- Avoid whole-stack restarts except after reboot or when the user explicitly intends broad maintenance.

If changes affect proxy overrides, restart or recreate the proxy path needed for the override to load.

## Escalation Rules

Tell the user to use Slack or an admin path when they lack:

- GI server login.
- Braingeneers GitHub access.
- Braingeneers NRP namespace access.
- Permission to view, create, replace, or delete Kubernetes secrets.
- Registry credentials for the chosen image registry.
- Auth0, CILogon, Keycloak, or MCP audience administration access.

Never present admin-only secret rotation as ordinary self-service.

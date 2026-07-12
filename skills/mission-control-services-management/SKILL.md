---
name: mission-control-services-management
description: Build, deploy, update, or troubleshoot Braingeneers lab services managed by mission_control on braingeneers.gi.ucsc.edu. Use when Codex is helping create a new Docker Compose service, choose between proxied web, public web, headless port-published, or MCP service patterns, configure service-proxy overrides, handle Braingeneers Kubernetes secrets and secret-fetcher, choose NRP kubeconfig authentication, package images for Docker Hub or another registry, add Makefile build/push/local-test workflows, or operate existing services with docker compose.
---

# Mission Control Services Management

Use this skill for Braingeneers services managed by `mission_control` on `braingeneers.gi.ucsc.edu`.

## Start Here

1. Confirm the user is working in or referencing the `mission_control` repo and read its current `README.md`, `docker-compose.yaml`, `service-proxy/`, `secret-fetcher/`, and relevant Braingeneers wiki pages before advising or editing. If the wiki repo is available locally, use it; otherwise use `https://github.com/braingeneers/wiki`.
2. Route the service into one branch before proposing changes:
   - `private-web`: browser-authenticated service behind `service-proxy/default`.
   - `public-web`: web service intentionally bypassing browser auth with a host-specific `service-proxy` override.
   - `headless`: non-HTTP or direct-port service such as MQTT or RustDesk; do not route this through `VIRTUAL_HOST` or host-specific nginx vhost files.
   - `mcp`: MCP resource server; keep shared edge TLS, bypass browser auth for MCP traffic, preserve `Authorization`, and make the backend validate bearer tokens and IAM.
3. Check access prerequisites early. Users need GI server access to `braingeneers.gi.ucsc.edu`, Braingeneers GitHub access, and Braingeneers NRP namespace access for secret-related operations.
4. Prefer a published container image in Docker Hub, the PRP registry, or another registry over a server-local build. Use a small `Makefile` for repeatable `build`, `push`, `local-test` or `run-test`, and `shell` workflows when the service owns a custom image.
5. Treat secrets as Kubernetes namespace resources materialized by `secret-fetcher` into the shared `/secrets` volume. Do not bake credentials into images.
6. Keep `mission_control` as a thin deployment repo. Put project-specific code, scripts, scheduler logic, runtime defaults, and application config in the owning service repo and published image. Compose should not become a second application configuration file, shell script host, scheduler, or maintenance-job registry.
7. Avoid host-level configuration and local bind mounts. The normal operator requirements should be only a `mission_control` checkout and a valid `~/.kube/config` for `secret-fetcher`.
8. Use shared local volumes for persistent service state. `local` is restart-persistent disposable state; `replicated` is backed-up static state. Each service owns a service-named subdirectory under the volume root.
9. Keep service topology manageable. Package tightly coupled helper behavior inside the owning service image; add sidecar services only when they are independently operated, scaled, or reused.

## Reference Loading

Load only the reference files needed for the current task:

- `references/access-and-auth.md`: server access, NRP kubeconfig, `kubelogin`, service-account kubeconfig, web auth, service-account JWTs.
- `references/service-routing.md`: private web, public web, headless, and MCP routing patterns.
- `references/packaging.md`: registry-published image policy and Makefile target conventions.
- `references/web-app-style.md`: Braingeneers web app visual language, reusable UI patterns, and bundled image assets.
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
- Braingeneers wiki `shared/permissions.md`
- Braingeneers wiki `shared/onboarding.md`
- Braingeneers wiki `shared/nrp_quickstart.md`
- Braingeneers wiki `shared/prp.md`
- Braingeneers wiki `shared/administrators.md` only when admin-only secret or Auth0 work is relevant

For MCP services, also read `docs/mcp-onboarding.md`, Braingeneers wiki `shared/mcp_architecture.md`, and `oauth2-broker/README.md`.

For browser-facing services with a new or refreshed UI, also read `references/web-app-style.md` and inspect nearby Braingeneers apps when available, especially `data-lifecycle`, `data_uploader`, and `data-explorer`.

### 2. Choose The Service Branch

Use the branch to determine which details matter:

- `private-web`: add or update a Compose service with `VIRTUAL_HOST`, `VIRTUAL_PORT`, `LETSENCRYPT_HOST`, `LETSENCRYPT_EMAIL`, and `braingeneers-net`. Default browser auth comes from `service-proxy/default`.
- `public-web`: use the same Compose service discovery, plus a host-specific `service-proxy/<hostname>` override with `auth_request off`; add the matching bind mount under the `service-proxy` service.
- `headless`: use explicit `ports:` and network settings as needed. Do not add `VIRTUAL_HOST`, `LETSENCRYPT_HOST`, or service-proxy vhost files unless the service also has an HTTP UI.
- `mcp`: follow the MCP onboarding contract. Preserve bearer tokens, strip proxy identity headers, mount IAM read-only, and configure issuer, JWKS, audience, and resource-server URL explicitly.

When the branch includes a web UI, align the app with the existing Braingeneers operations-app style unless the user asks for a different design direction.

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

Keep service-owned operational code in the owning repo before packaging. Examples include schedulers, entrypoint wrappers, maintenance scripts, backup scripts, worker defaults, and static application config. Bake stable runtime defaults into the image or service repo config rather than storing them as `environment:` entries in `mission_control/docker-compose.yaml`. For application services, Compose `environment:` should normally be limited to proxy discovery, ports/hostnames, secret paths, service endpoints that are truly deployment-specific, and rare operator-tuned values. Infrastructure images such as official Postgres may use small public env blocks required by the image initialization contract. Do not move a long list of app defaults into Compose just because the app reads environment variables.

Keep Compose commands short and declarative. Do not embed long shell scripts, scheduler loops, backup logic, migrations, or operational programs directly in `docker-compose.yaml`; package that behavior in the owning image and expose a boring entrypoint or command. Shared infrastructure services owned by `mission_control`, such as a database image, should keep their build and push targets in the root `mission_control/Makefile`. Client repos should document dependency contracts and connection defaults, not own shared service packaging.

When you add a production service, explicitly state whether the image is registry-published and how it is built and pushed from the owning repo. If a required image has not been published yet, update the owning repo workflow first or call out the blocker instead of adding a server-local `build:`.

### 5. Wire Secrets Correctly

When a service needs secrets:

- Add `secrets:/secrets`.
- Add `depends_on: secret-fetcher: condition: service_healthy`.
- Use `/secrets/<kubernetes-secret-name>/<key>` paths.
- Use `/secrets/entrypoint-secrets-setup.sh` only when the app needs copied files or exported env vars before launch.
- Use `--copy` for files such as AWS credentials, kubeconfigs, SSH keys, or service-account token files.
- Use `--env` for secret-backed env files.

For unattended `braingeneerspy` services, prefer the daily refreshed `/secrets/braingeneers-jwt-service-account-token/config.json` mounted to the expected `braingeneers/iot/service_account/config.json` location. Do not recommend stale raw `service-accounts/config.json` patterns unless the local code specifically requires it and the risk is acknowledged.

Avoid additional bind mounts for service files. Host-mounted files are acceptable for mission_control-owned proxy overrides, IAM policy files, and narrow legacy cases, but they should not be the default way to ship project-specific code or configuration.

Use the shared `local` and `replicated` Docker volumes for local service state. Mount the volume root and have each service create a service-named subdirectory, for example `/local/sql-db` or `/replicated/sql-db`. Put active files, databases, mutable state, and restart-persistent disposable state in `local`. Put only completed static files that should be backed up in `replicated`; stage changing files in `local` and publish finished outputs into `replicated` with final names. Dot-prefixed temporary publish files in `replicated` are tolerated only as short-lived incomplete files and should be ignored by backup tooling. Do not add new service-specific top-level volumes unless a legacy image or external compatibility requirement makes it necessary.

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

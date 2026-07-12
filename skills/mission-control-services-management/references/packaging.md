# Packaging And Makefiles

Use this reference when a service needs a Docker image, registry choice, or local developer workflow.

## Registry-First Policy

Prefer deploying registry-published images instead of building on `braingeneers.gi.ucsc.edu`.

Rationale:

- The server may be rebuilt or migrated.
- Upstream package versions can change and make a future rebuild fail.
- A published image gives Compose a stable artifact to pull.
- Operators can use `docker compose pull` and targeted recreates.

Acceptable registries include Docker Hub, the PRP GitLab registry, Quay, GitHub Container Registry, or another registry the lab can access. For Braingeneers services, prefer a registry path that future maintainers can push to.

Before adding or updating a production Compose service, verify and state where the image is built and pushed from. If the service owns custom code, the owning repo should provide the build and push workflow; `mission_control` should consume the resulting image.

Do not add service-specific scripts, schedulers, worker code, backup logic, or application config files to `mission_control` just to mount them into a container. Put those files in the owning repo, bake them into the image, and keep Compose focused on selecting the image and wiring secrets, networks, ports, dependencies, and proxy settings. Treat long service-specific `environment:` blocks as a design smell unless each key is clearly deployment-specific.

Do not embed long shell scripts, scheduler loops, or maintenance programs directly in `docker-compose.yaml`. Compose should describe service topology and deployment wiring; executable behavior belongs in the image. Add an extra sidecar service only when it is independently operated, independently scaled, or meaningfully reusable. If helper behavior is tightly coupled to a service, package it inside that service's image.

## Compose Image Guidance

For production services, prefer:

- `image: owner/service:version-or-managed-tag`
- A clear owner or maintainer comment near the service.
- Avoiding `build:` unless the user explicitly wants server-local builds and accepts the migration risk.
- Minimal `environment:` entries for application services. Stable runtime defaults belong in the image or service repo config, not in `mission_control/docker-compose.yaml`.
- Small public env blocks are acceptable for infrastructure images when they are the image's initialization API, for example `POSTGRES_DB`, `POSTGRES_USER`, and a non-secret internal-only `POSTGRES_PASSWORD`.
- Minimal bind mounts. Mount mission_control-owned files only when they are genuinely deployment-owned, such as proxy overrides or IAM policy files.
- Shared local state volumes. Prefer service-scoped directories under `local` and `replicated` over new service-specific top-level volumes.
- Manageable service units. Avoid creating separate Compose services for tightly coupled helper tasks that can run inside the owning service image.

If an existing service uses `build:`, avoid rewriting it opportunistically. For a new service or a substantive service cleanup, recommend moving to a published image.

## Tags

Prefer one of these patterns:

- Immutable release tags for production rollouts, such as `v1.2.3`.
- A managed channel tag, such as `latest`, only when the owning team understands that `docker compose pull` changes what is deployed.
- Both immutable release tags and a channel tag when maintainers need easy rollback plus a conventional default.

## Makefile Pattern

For custom-image services, recommend a small `Makefile` with stable targets:

- `build`: build the local image.
- `push`: push the selected tag to the registry.
- `local-test` or `run-test`: run the service locally with representative ports and mounts.
- `shell`: open a shell in the image for debugging.
- `release`: optional; tag and push a versioned release.

Keep target names boring and predictable. The point is to make repeated operations discoverable for future operators.

Shared infrastructure images owned by `mission_control` should expose their build, push, shell, and smoke-test targets from the root `mission_control/Makefile`. Client repositories should not own targets for shared Mission Control services; they should document only the connection contract they require.

## Shared Local Volumes

New services that need local state should use the shared top-level Docker volumes:

- `local`: restart-persistent state that can be regenerated or recovered. Active file changes belong here.
- `replicated`: backed-up static files. Services should stage work in `local` and publish completed artifacts into service-scoped folders under `replicated`.

Each service owns a service-named directory under the volume root, such as `/local/sql-db` and `/replicated/sql-db`. Do not add a new top-level volume for each service unless a legacy image or external compatibility requirement requires it. Backup tooling should ignore dot-prefixed temporary publish files in `replicated`.

Existing local examples:

- `mqtt/README.md` references `make mqtt-build`, `make mqtt-push`, and `make mqtt-shell`.
- `plotly-dash-picroscope-control-console/Makefile` has `build`, `build-and-test`, `push`, `shell`, `run`, and release-oriented targets.
- `strapi-shadows-db/Makefile` has simple `build` and test run targets.

## Local Testing

When proposing local tests:

- Avoid using production secrets unless the existing service already requires them and the user has access.
- Prefer read-only mounts for local credentials.
- Map to non-conflicting local ports.
- Make the expected health check or smoke test clear.

## Registry Troubleshooting

Common failures:

- `ImagePullBackOff`: image not pushed, wrong tag, private registry auth missing, or wrong registry path.
- Pull succeeds locally but not on server: server lacks registry auth or network access.
- Compose keeps running an old image: the service was not pulled or recreated.

Use targeted `docker compose pull <service>` and `docker compose up -d --force-recreate --pull always <service>` when operating production services.

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

Do not add service-specific scripts, schedulers, worker code, or application config files to `mission_control` just to mount them into a container. Put those files in the owning repo, bake them into the image, and keep Compose focused on selecting the image and wiring secrets, networks, ports, and proxy settings.

## Compose Image Guidance

For production services, prefer:

- `image: owner/service:version-or-managed-tag`
- A clear owner or maintainer comment near the service.
- Avoiding `build:` unless the user explicitly wants server-local builds and accepts the migration risk.
- Minimal `environment:` entries. Stable runtime defaults belong in the image or service repo config, not in `mission_control/docker-compose.yaml`.
- Minimal bind mounts. Mount mission_control-owned files only when they are genuinely deployment-owned, such as proxy overrides or IAM policy files.

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

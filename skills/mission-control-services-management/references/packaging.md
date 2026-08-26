# Packaging, Images, And State

Use this reference when a service needs a container image, registry workflow,
Compose ownership boundary, or local persistent storage.

## Keep Deployment Thin

`mission_control` should select and wire deployable artifacts, not become a
second application repository. Put service-owned code, entrypoints, schedulers,
migrations, maintenance jobs, runtime defaults, and application configuration
in the owning repository and image.

Compose should normally contain only:

- the published image and deployment-specific command;
- proxy discovery, internal ports, and networks;
- secret paths and required mounts;
- genuine startup dependencies;
- deployment-specific endpoints or rare operator-tuned values.

Long embedded shell, scheduler loops, maintenance programs, large application
environment blocks, and host-mounted service source indicate misplaced
ownership. Mission Control-owned shared infrastructure images may keep their
source and build targets in this repository.

## Registry And Tag Policy

Prefer a registry-published image over `build:` on the production server. A
published artifact survives host migration, supports targeted pulls, and avoids
future rebuilds drifting with upstream dependencies.

Before changing production Compose, identify:

- the owning repository and maintainer;
- the registry path and who can push it;
- the build, test, and push workflow;
- the rollback artifact.

Prefer immutable release or date/SHA tags for production. A moving tag such as
`latest` is acceptable only when maintainers intentionally use pull-and-recreate
semantics and retain a rollback reference. Do not rewrite an unrelated legacy
`build:` service opportunistically.

## Makefile Contract

Custom-image repositories should expose predictable targets when useful:

- `build`
- `push`
- `local-test` or `run-test`
- `shell`
- optional `release`

Shared infrastructure images owned by Mission Control expose equivalent named
targets from the root `Makefile`. Client repositories document their connection
contract; they do not own shared-infrastructure build targets.

## Service Boundaries

Package tightly coupled helpers with the owning service. Add a separate Compose
service only when the component is independently operated, scaled, secured, or
reused. Use `depends_on` only when the dependent process genuinely cannot start
without the prerequisite; optional integrations should start degraded and
reconnect or retry.

Avoid host-level bind mounts. Narrow exceptions include Mission Control-owned
proxy overrides, IAM policies, and compatibility files that are genuinely
deployment-owned.

## Shared State Volumes

Use the existing top-level volumes:

- `local`: restart-persistent state that may be regenerated or restored; active
  databases, caches, queues, and in-progress work belong here.
- `replicated`: completed static artifacts that require additive backup.

Each service owns a service-named subdirectory such as `/local/sql-db` or
`/replicated/sql-db`. Do not add a top-level volume per service without a
concrete compatibility or isolation requirement.

Stage changing files in `local` and atomically publish completed files into
`replicated`. If an incomplete file must temporarily exist there, use a
dot-prefixed name such as `.artifact.tmp`, then rename it to its final visible
name. Do not use visible suffix-only temporary names such as `artifact.tmp` in
`replicated`; backup tooling intentionally excludes dot-prefixed and `*.tmp`
objects.

The replicated-volume backup is additive: it copies new and changed eligible
files and never deletes destination objects. Mount `replicated` read-only in the
backup service.

## Local Validation

Do not run production-style Mission Control services locally unless requested.
For an approved local test, avoid production credentials where possible, mount
any required credentials read-only, use non-conflicting ports, and state the
expected health or smoke-test evidence.

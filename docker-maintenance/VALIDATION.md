# Initial release validation — 2026-11-11

## Published artifact

- Runtime/test source commit: `c39dfe6d4a53f37bb00bc0b2ef9ef3ec08773fae`.
- Image: `braingeneers/docker-maintenance:20261111-c39dfe6d4a53` (linux/amd64).
- Registry manifest digest: `sha256:bf55b77d826b0568288bfbc87bd9f072bfaaf5d1c2e8ce936dbe62e7a985b013`.
- Image revision label matches the full source commit above. Tests and README
  are excluded from the actual image; `/app` contains only `maintenance.py`.
- Actual image health check invokes `python3 /app/maintenance.py healthcheck`
  every five minutes, with a ten-second timeout and three-minute start period.

## Completed checks

- `make docker-maintenance-test DOCKER_MAINTENANCE_TAG=20261111-c39dfe6d4a53`:
  **27 tests passed**, plus image CLI and runtime/test-exclusion smoke checks.
  Tests ran in the final image without network access, a Docker socket, production
  storage or credentials. Coverage includes daily/hourly scheduling, explicit
  age-filtered image-only pruning arguments, pressure cleanup, disk/inode limits,
  observation failures, atomic state round trip, malformed state, restart cooldown,
  process locking, read-only status/health, failed/ambiguous notifications and
  critical-alert suppression/recovery. Docker's container-image protection is
  delegated to its documented prune contract; tests do not actually delete images.
- `make test`: complete repository configuration/proxy/Compose contract gate
  passed against the release pin, including the new maintenance contract.
- Scoped source/permission review and `git diff --check` passed. Publication
  completed successfully; registry inspection verified the manifest digest.
- Read-only HTTPS `GET /v1/slack/destinations` returned HTTP 200 and mapped
  `C08NSDULLR1` to `#braingeneers-helpdesk`. No test message was sent.

The deployment commit adds wiring, Make targets and this record; it does not
change the runtime, Dockerfile, tests or base image from the source commit above.
Earlier development images were not published. No raw runtime/server evidence
is claimed or required to reproduce the isolated tests.

Final integration merged concurrent NRP-monitor changes in `6ae5614`. An exact
comparison against deployment commit `320d6c6` found no changes to this service,
Makefile, Compose configuration, proxy files or affected contract tests. The
completed image tests and full repository gate above therefore retain their
original scope; no runtime check was repeated for that unrelated skills merge.

## Operator acceptance still outstanding

This release has **not** been deployed by the assistant. The operator must pull
and start `docker-maintenance`, confirm running image identity, initial cleanup
success and health, and compare its disk readings with host `df`/`findmnt`.
Specifically confirm that `/local` and the Docker root share the affected `/data`
filesystem. Commands and stopping conditions are in the service README.

No production cleanup, service restart or Slack delivery has been exercised by
these checks. A same-host monitor cannot guarantee alerts through a host or
notification-service outage. External monitoring and non-image storage retention
remain explicit follow-ups, not acceptance claims for this release.

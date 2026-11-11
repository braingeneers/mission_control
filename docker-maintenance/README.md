# Docker maintenance

Independent Mission Control infrastructure for local Docker image retention and
critical storage alerts. No host cron, systemd unit, daemon configuration edit,
PostgreSQL, Workflows, or provider credential is required. Source is owned here;
production uses a published immutable image.

## Policy

- Observe Docker and the shared `local` volume filesystem every five minutes.
- At startup when due, then daily, run only
  `docker --host unix:///var/run/docker.sock image prune --all --force --filter until=336h`.
  Docker removes unused images **created** more than fourteen days ago, protecting
  images referenced by any existing container, including stopped containers.
  Old rollback images may need downloading from the registry again.
- Under critical disk pressure, run that same cleanup early, at most hourly.
  Failures retry hourly. No broader emergency deletion is attempted.
- Never prune containers, volumes, networks or build caches, change Secrets,
  restart services, or touch files in another service directory.
- Critical capacity means available space below **10 GiB or 5%**, or available
  inodes below **5%**. Filesystems without inode counts skip that inode check.
  These are alert thresholds, not a guaranteed database capacity reservation.
- After cleanup, two consecutive critical observations trigger an alert. Three
  failed Docker/disk observations, 26 hours without successful cleanup, or an
  inability to persist state also need operator attention.

The process has one scheduling loop and an exclusive advisory lock. Commands and
network calls have timeouts. One small atomic state file under
`/local/docker-maintenance/state.json` records heartbeat, observations, cleanup,
and notification cooldown. Corrupt state is rebuilt and logged. State write
failures do not suppress cleanup or the in-memory critical alert; if storage
cannot save state, cooldown cannot survive a restart and duplicate alerts are
possible. A completely unavailable volume can prevent the process starting.

## Permissions and portability

The Docker socket bind is an explicit infrastructure exception to the normal
avoid-host-bind-mount rule, like the existing proxy's socket access. The socket
grants powerful control over the **host Docker daemon**, even mounted `:ro`;
that flag does not make API operations read-only. Do not expose this service or
give it unrelated credentials. It runs as root to access the standard socket.

`statvfs(/local)` measures the shared data volume filesystem, not the container
overlay. Operator acceptance must confirm that this filesystem is also the
filesystem backing the Docker root directory; this cannot be established from
the container's filesystem namespace alone. If deployment places those on
different filesystems, this release does not cover Docker image filesystem
capacity: resolve the monitoring placement before accepting deployment.

## Notifications and health

Only critical, actionable alerts are sent to `#braingeneers-helpdesk` (stable ID
`C08NSDULLR1`) through `http://notification-service:8000/v1/slack`. Each top-level
message identifies `Mission Control / docker-maintenance`, server, condition,
capacity, last cleanup result, and requested action. No thread replies, mentions,
test alerts, routine successes, startup messages, or recovery posts are sent.

Conditions are combined. Ongoing incidents repeat at most daily; three clear
checks reset suppression. Explicit HTTP delivery failures retry at most hourly;
ambiguous delivery waits 24 hours to limit duplicates. Cooldown is saved before
posting. No unbounded queue or database is used. Notification failure never
blocks cleanup. Slack integration needs no credential mounts or startup dependency.

Image health checks detect heartbeat older than 15 minutes, observation failures,
overdue cleanup, critical pressure, persistence errors and failed/uncertain alert
delivery. Docker marks an unhealthy container but does **not** restart it just
because health fails. A host or notification outage cannot be reliably reported
by this same-host service; external monitoring is separate work.

## Build and validate

```bash
make docker-maintenance-test
make test
```

Unit and image tests use mocked Docker/notification interfaces, no real daemon
socket, no production state and no network access. They do not prune local Docker
resources or send Slack messages. Tests are excluded from the production image.
The Docker base is digest-pinned. The image revision label identifies the source
commit; release builds must use clean committed service source.

After validation, publish with `make docker-maintenance-push`, retaining the same
`DOCKER_MAINTENANCE_TAG` used to build/test, then update the Compose pin. Existing
image defaults and implementation constants own policy; deployment-specific
`MAINTENANCE_SERVER` and `MAINTENANCE_SLACK_CHANNEL_ID` identify the host/channel.

## Deploy and inspect (operator on the server)

```bash
git pull --ff-only
docker compose pull docker-maintenance
docker compose up -d --no-deps docker-maintenance
docker compose ps docker-maintenance
docker compose logs --tail=100 docker-maintenance
docker compose exec docker-maintenance python3 /app/maintenance.py status
docker compose exec docker-maintenance python3 /app/maintenance.py healthcheck
```

To confirm storage placement, inspect the Docker root and shared volume mount:

```bash
docker info --format '{{.DockerRootDir}}'
docker inspect docker-maintenance --format '{{range .Mounts}}{{if eq .Destination "/local"}}{{.Source}}{{end}}{{end}}'
```

Use `findmnt -T` for **each returned host path** and confirm the same filesystem
and `/data` backing storage. Check `df -h` and `df -i` for that filesystem and
compare the readings with service status. Confirm the running image matches the
Compose pin, then check initial cleanup success and health. Slack destination
verification is read-only; no synthetic alert is posted to the busy channel.

`once` runs one policy-respecting cycle, acquiring the same lock as `run`; it
returns 75 if a scheduler already holds the lock. `status` and `healthcheck` are
read-only and safe alongside the scheduler. To disable maintenance, stop only
`docker-maintenance`; retained state remains in `local`.

Existing application log limits, build-cache retention, application data growth,
separate database storage, and external host monitoring remain follow-ups. Image
cleanup alone cannot guarantee the shared filesystem never fills.

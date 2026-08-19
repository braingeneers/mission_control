# Replicated Volume Backup

This Mission Control infrastructure service copies completed static artifacts
from the shared `replicated` Docker volume to:

```text
s3://braingeneersdev/services/replicated/
```

It runs every day at 02:00 in `America/Los_Angeles`. The copy is additive:
new and changed files are uploaded, while objects that no longer exist locally
are retained at the destination. Dot-prefixed files and `*.tmp` files are
excluded so incomplete publications are not copied.

The image reads NRP credentials directly from
`/secrets/prp-s3-credentials/credentials`, mounts `/replicated` read-only, and
stores its lock and latest run status under `/local/replicated-volume-backup`.
The health check requires a successful sync within the last 36 hours. A manual
sync must therefore be completed as part of first deployment.

Build, test, publish, and inspect the image from the repository root:

```bash
make replicated-volume-backup-build
make replicated-volume-backup-test
make replicated-volume-backup-push
make replicated-volume-backup-shell
```

Run a manual sync on `braingeneers.gi.ucsc.edu`:

```bash
docker compose run --rm replicated-volume-backup sync
```

Inspect status and logs:

```bash
docker compose ps replicated-volume-backup
docker compose logs --tail=200 replicated-volume-backup
docker compose exec replicated-volume-backup replicated-volume-backup healthcheck
docker compose exec replicated-volume-backup cat /local/replicated-volume-backup/last-attempt.env
```

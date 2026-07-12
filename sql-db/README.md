# SQL DB Service Image

This image owns the shared Mission Control SQL service. It extends
`postgres:16-alpine`, starts Postgres through the upstream entrypoint, and runs
a small cron-managed backup script in the same container.

## Runtime Paths

- Active database files: `/local/sql-db/postgres/pgdata`
- Backup staging files: `/local/sql-db/backups`
- Static backup outputs: `/replicated/sql-db/postgres`

The service expects the shared Mission Control `local` and `replicated` Docker
volumes to be mounted at `/local` and `/replicated`.

## Backups

`backup-sql-db.sh` runs daily at `08:00 UTC`. It writes custom-format
`pg_dump` archives using 30 rolling slots:

```text
services-rotation-00.dump
services-rotation-00.json
...
services-rotation-29.dump
services-rotation-29.json
```

Slots are selected from the UTC epoch day modulo 30, so old backups are
overwritten by filename. The script stages work under `/local` and publishes
completed files into `/replicated`.

Run a manual backup from a running container:

```bash
docker compose exec sql-db /usr/local/bin/backup-sql-db.sh
```

Inspect a dump:

```bash
docker compose exec sql-db pg_restore -l /replicated/sql-db/postgres/services-rotation-00.dump
```

Restore into a target database with normal Postgres restore tooling. Choose the
rotation file by timestamp in the adjacent JSON metadata file.

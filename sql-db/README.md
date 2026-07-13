# Shared SQL Database

`sql-db` is the PostgreSQL 16 service shared by applications deployed through
Mission Control. It is internal infrastructure: clients reach it only on the
`braingeneers-net` Docker network, and its port is not published on the host.

## Client contract

The production connection defaults are:

| Setting | Value |
| --- | --- |
| Host | `sql-db` |
| Port | `5432` |
| Database | `services` |
| User | `services` |
| Password | `services` |

The shared credentials are public defaults for internal compatibility. They are
not a security boundary. Network isolation comes from Docker, and schema
separation prevents accidental table and migration-name collisions between
applications.

New clients must own one PostgreSQL schema. Derive the schema from the Compose
service name by replacing hyphens with underscores; names must match
`[a-z][a-z0-9_]*`. For example, `my-service` owns `my_service`. Do not create new
application tables in `public` and do not use another service's schema.

Workflows was deployed before this convention and currently uses `public`.
Treat it as a legacy exception until a separately planned production migration
moves it into a `workflows` schema.

## Provision a client schema

On `braingeneers.gi.ucsc.edu`, create the schema once before starting a new
client. Substitute the approved schema name directly in both places:

```bash
docker compose exec sql-db psql -U services -d services \
  -c 'CREATE SCHEMA IF NOT EXISTS my_service AUTHORIZATION services;'
docker compose exec sql-db psql -U services -d services \
  -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'my_service';"
```

Because every client uses the same database role, `AUTHORIZATION services`
provides namespace ownership rather than access control. Schema removal is a
destructive, operator-managed action and is not part of routine service removal.

## Connect an application

A psycopg/SQLAlchemy URL that selects the client schema is:

```text
postgresql+psycopg://services:services@sql-db:5432/services?options=-csearch_path%3Dmy_service
```

For other drivers, configure the equivalent PostgreSQL startup option
`search_path=my_service`. Do not include `public` as a writable fallback for a
new client. Verify the effective connection before running migrations:

```sql
SHOW search_path;
SELECT current_schema();
```

`current_schema()` must return the client's schema. Migration tools must also
store their version table there; for example, Alembic's default
`alembic_version` table is safe only after the schema-aware connection has been
verified.

The client and `sql-db` must share `braingeneers-net`. Make database readiness an
explicit dependency:

```yaml
services:
  my-service:
    image: braingeneers/my-service:<immutable-tag>
    networks:
      - braingeneers-net
    depends_on:
      sql-db:
        condition: service_healthy
```

Keep stable production connection defaults and migration/startup behavior in
the client repository and published image. Mission Control Compose should only
declare the shared dependency or a genuinely deployment-specific override. Do
not add a client-specific Postgres container, publish port `5432`, or mount the
database volumes into a client.

For local development, a client may run its own disposable Postgres container
with the same database, role, and schema contract. That local container is not
part of the production Mission Control topology.

## First client: Workflows

The Workflows backend demonstrates the current production wiring in
`docker-compose.yaml`: it joins `braingeneers-net`, waits for the healthy
`sql-db` service, and runs Alembic before starting. Its image currently defaults
to this legacy public-schema URL:

```text
postgresql+psycopg://services:services@sql-db:5432/services
```

Use Workflows as an example of network and health-dependency wiring, not as an
example of the schema contract for a new client.

## Image and runtime paths

The image extends `postgres:16-alpine`, starts Postgres through the upstream
entrypoint, and runs the backup scheduler in the same container.

- Active database files: `/local/sql-db/postgres/pgdata`
- Backup staging files: `/local/sql-db/backups`
- Static backup outputs: `/replicated/sql-db/postgres`

The service mounts the shared Mission Control `local` and `replicated` Docker
volumes at `/local` and `/replicated`. Build, publish, and test the shared image
from the Mission Control repository root:

```bash
make sql-db-build
make sql-db-push
make sql-db-shell
make sql-db-test-backup
```

## Backups and restore

`backup-sql-db.sh` runs daily at `08:00 UTC`. It dumps the entire `services`
database—including every client schema—to a custom-format archive using 30
rolling slots:

```text
services-rotation-00.dump
services-rotation-00.json
...
services-rotation-29.dump
services-rotation-29.json
```

Slots are selected from the UTC epoch day modulo 30, so old backups are
overwritten by filename. Work is staged under `/local`; only completed dump and
metadata files are published into `/replicated`.

Run a manual backup and inspect a selected dump:

```bash
docker compose exec sql-db /usr/local/bin/backup-sql-db.sh
docker compose exec sql-db pg_restore -l /replicated/sql-db/postgres/services-rotation-00.dump
```

Choose a rotation file by the timestamp in its adjacent JSON metadata file.
Restoring the shared database or an individual schema can overwrite client data,
so test the intended `pg_restore` selection in a separate target before any
production restore.

## Operate and troubleshoot

Refresh only the shared database when its image or configuration changes:

```bash
docker compose pull sql-db
docker compose up -d --force-recreate sql-db
docker compose ps sql-db
docker compose logs -f sql-db
```

Useful checks from the server are:

```bash
docker compose exec sql-db pg_isready -U services -d services
docker compose exec sql-db psql -U services -d services -c '\dn'
```

If a client cannot connect, confirm that `sql-db` is healthy, both services are
on `braingeneers-net`, the hostname is `sql-db`, and the schema exists. If
migrations appear in `public`, stop the client and correct its connection or
migration configuration before retrying.

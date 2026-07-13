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
moves it into a `workflows` schema. Do not enable the sql-db schema guardrail in
production until that migration is complete.

## Default schema guardrail

The sql-db image installs a database-specific empty default `search_path` for
the shared `services` role. A client that omits its service schema therefore has
no current schema, and unqualified migrations fail instead of silently creating
objects in `public`. A correctly configured client overrides the default with
its connection-level `search_path`.

This is an accidental-misconfiguration guardrail, not access isolation. The
shared `services` role remains a superuser and can explicitly target `public` or
another client schema. Enforcing that boundary would require separate roles and
credentials for every client.

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
verified. A default connection without a schema override should return `NULL`
from `current_schema()` after the guardrail is enabled.

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

## Enable the guardrail on the existing database

Initialization scripts only run for a new PostgreSQL data directory. Enable the
same policy once on the existing production database only after Workflows uses
the `workflows` schema and no application tables or migration-version tables
remain in `public`.

On `braingeneers.gi.ucsc.edu`, take a backup and inspect both schemas before
applying the policy:

```bash
docker compose exec sql-db /usr/local/bin/backup-sql-db.sh
docker compose exec sql-db psql -U services -d services \
  -c "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema IN ('public', 'workflows') ORDER BY 1, 2;"
docker compose exec sql-db psql -X -U services -d services -c 'SHOW search_path;'
```

Verify the Workflows connection itself reports `current_schema() = 'workflows'`
before continuing. Apply the versioned policy file from the Mission Control
checkout, then verify a new default connection has no current schema:

```bash
docker compose exec -T sql-db psql -X -U services -d services \
  -v ON_ERROR_STOP=1 < sql-db/require-client-schema.sql
docker compose exec sql-db psql -X -U services -d services \
  -tAc 'SELECT current_schema() IS NULL;'
```

The policy file refuses to run while tables, partitioned tables, views,
materialized views, sequences, or foreign tables remain in `public`. The final
query must return `t`. Then publish the updated sql-db image, update its
immutable Compose tag, recreate only `sql-db`, and verify sql-db health,
Workflows readiness, schema locations, and another backup. If an unexpected
legacy client is blocked, roll back the session default while correcting that
client:

```bash
docker compose exec sql-db psql -X -U services -d services \
  -c 'ALTER ROLE services IN DATABASE services RESET search_path;'
```

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
docker compose exec sql-db /usr/local/bin/check-client-schema-policy.sh
docker compose exec sql-db psql -U services -d services -c '\dn'
```

If a client cannot connect, confirm that `sql-db` is healthy, both services are
on `braingeneers-net`, the hostname is `sql-db`, and the schema exists. If
migrations appear in `public`, stop the client and correct its connection or
migration configuration before retrying.

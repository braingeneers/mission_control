# Shared SQL Database

Use this reference when a Mission Control service needs PostgreSQL. The
canonical operator and client guide is `sql-db/README.md`.

## Decide Whether To Use It

Prefer the shared `sql-db` service for ordinary application relational state.
Do not add a client-specific production Postgres container merely because the
client uses one during local development. Propose separate database
infrastructure only for a concrete compatibility, isolation, scaling, or
operational requirement.

## Client Contract

- Host and port: `sql-db:5432` on `braingeneers-net`.
- Database, user, and password: `services`.
- Schema: normalized Compose service name, with hyphens replaced by
  underscores, matching `[a-z][a-z0-9_]*`.
- Isolation: schemas prevent accidental namespace collisions; the shared role
  means they are not a security boundary.

An operator creates the schema once before the first deployment:

```bash
docker compose exec sql-db psql -U services -d services \
  -c 'CREATE SCHEMA IF NOT EXISTS my_service AUTHORIZATION services;'
```

A psycopg/SQLAlchemy URL is:

```text
postgresql+psycopg://services:services@sql-db:5432/services?options=-csearch_path%3Dmy_service
```

Use the equivalent PostgreSQL `search_path` startup setting for other drivers.
Do not add `public` as a writable fallback. Before migrations, verify that
`SHOW search_path` selects the client schema and `SELECT current_schema()`
returns it. Ensure migration version tables, including Alembic's
`alembic_version`, are created in that schema.

The sql-db image gives default `services` connections an empty `search_path`,
so omitted client configuration fails rather than creating objects in `public`.
This is a configuration guardrail only: the shared superuser can still target a
schema explicitly. For an existing cluster, apply
`sql-db/require-client-schema.sql` once after every client selects its owned
schema and `public` contains no application relations; fresh clusters apply it
during initialization. The sql-db health check verifies that a default
connection has no current schema.

## Compose And Packaging

Join the client to `braingeneers-net` and wait for database health:

```yaml
networks:
  - braingeneers-net
depends_on:
  sql-db:
    condition: service_healthy
```

Do not expose or publish port `5432`, mount `local` or `replicated` into the
client, or make the client own the shared database image. Keep models,
migrations, schema-aware connection configuration, and local Postgres setup in
the client repository and published image. A local disposable database may
mirror the production database/role/schema contract without becoming a Mission
Control production service.

## Backups And Operations

The daily backup dumps the entire `services` database, so all client schemas are
included. Active files live under `/local/sql-db`; completed rotating dumps live
under `/replicated/sql-db/postgres`. Treat any restore or schema drop as a
destructive shared-infrastructure operation.

Refresh and inspect only the database service when it changes:

```bash
docker compose pull sql-db
docker compose up -d --force-recreate sql-db
docker compose ps sql-db
docker compose logs -f sql-db
```

For connection failures, verify database health, shared network membership,
hostname, and schema existence. If a client's migrations create objects in
`public`, stop it and fix the connection or migration configuration before
retrying. If the guardrail exposes a client without an explicit schema, the
documented temporary rollback is
`ALTER ROLE services IN DATABASE services RESET search_path`.

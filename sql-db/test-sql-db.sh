#!/bin/sh
set -eu

image="${1:?usage: test-sql-db.sh IMAGE}"
suffix="${SQL_DB_TEST_SUFFIX:-$$}"
container="sql-db-test-${suffix}"
network="sql-db-test-${suffix}"
local_volume="sql-db-test-local-${suffix}"
replicated_volume="sql-db-test-replicated-${suffix}"
container_created=0
network_created=0
local_volume_created=0
replicated_volume_created=0

cleanup() {
  if [ "$container_created" -eq 1 ]; then
    docker container rm -f "$container" >/dev/null 2>&1 || true
  fi
  if [ "$network_created" -eq 1 ]; then
    docker network rm "$network" >/dev/null 2>&1 || true
  fi
  if [ "$local_volume_created" -eq 1 ]; then
    docker volume rm "$local_volume" >/dev/null 2>&1 || true
  fi
  if [ "$replicated_volume_created" -eq 1 ]; then
    docker volume rm "$replicated_volume" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

docker network create "$network" >/dev/null
network_created=1
docker volume create "$local_volume" >/dev/null
local_volume_created=1
docker volume create "$replicated_volume" >/dev/null
replicated_volume_created=1
docker run -d --name "$container" --network "$network" \
  -e PGDATA=/local/sql-db/postgres/pgdata \
  -e POSTGRES_DB=services \
  -e POSTGRES_USER=services \
  -e POSTGRES_PASSWORD=services \
  -v "$local_volume:/local" \
  -v "$replicated_volume:/replicated" \
  "$image" >/dev/null
container_created=1

docker run --rm --network "$network" -e PGPASSWORD=services postgres:16-alpine \
  sh -lc "until pg_isready -h '$container' -U services -d services; do sleep 1; done"

# Fresh clusters must install the fail-closed default.
docker exec "$container" /usr/local/bin/check-client-schema-policy.sh

# The same SQL file must migrate an existing cluster safely and repeatedly.
docker exec "$container" psql -X -U services -d services -v ON_ERROR_STOP=1 \
  -c "ALTER ROLE services IN DATABASE services RESET search_path" >/dev/null
default_schema="$(docker run --rm --network "$network" -e PGPASSWORD=services postgres:16-alpine \
  psql -X -h "$container" -U services -d services -tAc 'SELECT current_schema()')"
test "$default_schema" = "public"
docker exec "$container" psql -X -U services -d services -v ON_ERROR_STOP=1 \
  -c 'CREATE TABLE public.public_guardrail_probe (id integer)' >/dev/null
if docker exec "$container" psql -X -U services -d services \
  -f /docker-entrypoint-initdb.d/010-require-client-schema.sql >/dev/null 2>&1; then
  echo "sql-db test: policy enabled while public still contained a relation" >&2
  exit 1
fi
docker exec "$container" psql -X -U services -d services -v ON_ERROR_STOP=1 \
  -c 'DROP TABLE public.public_guardrail_probe' >/dev/null
docker exec "$container" psql -X -U services -d services \
  -f /docker-entrypoint-initdb.d/010-require-client-schema.sql >/dev/null
docker exec "$container" psql -X -U services -d services \
  -f /docker-entrypoint-initdb.d/010-require-client-schema.sql >/dev/null
docker exec "$container" /usr/local/bin/check-client-schema-policy.sh
docker exec "$container" sh -c \
  'pg_isready -U services -d services >/dev/null && [ "$(psql -X -U services -d services -tAc '\''SELECT current_schema() IS NULL'\'')" = t ]'

# An unconfigured client must fail instead of creating in public.
if docker run --rm --network "$network" -e PGPASSWORD=services postgres:16-alpine \
  psql -X -h "$container" -U services -d services -v ON_ERROR_STOP=1 \
  -c 'CREATE TABLE schema_guardrail_must_fail (id integer)' >/dev/null 2>&1; then
  echo "sql-db test: unconfigured client created a table unexpectedly" >&2
  exit 1
fi

# A configured client can migrate and query within its provisioned schema.
docker exec "$container" psql -X -U services -d services -v ON_ERROR_STOP=1 \
  -c 'CREATE SCHEMA test_client AUTHORIZATION services' >/dev/null
docker run --rm --network "$network" -e PGPASSWORD=services \
  -e PGOPTIONS=-csearch_path=test_client postgres:16-alpine \
  psql -X -h "$container" -U services -d services -v ON_ERROR_STOP=1 \
  -c 'CREATE TABLE guardrail_probe (id integer); INSERT INTO guardrail_probe VALUES (1)' >/dev/null
configured_result="$(docker run --rm --network "$network" -e PGPASSWORD=services \
  -e PGOPTIONS=-csearch_path=test_client postgres:16-alpine \
  psql -X -h "$container" -U services -d services -tAc \
  "SELECT current_schema() || ':' || count(*) FROM guardrail_probe")"
test "$configured_result" = "test_client:1"

# Backups must continue to include client schemas and publish complete files.
docker exec "$container" /usr/local/bin/backup-sql-db.sh
docker exec "$container" /usr/local/bin/backup-sql-db.sh
file_count="$(docker run --rm -v "$replicated_volume:/replicated" postgres:16-alpine \
  sh -lc 'find /replicated/sql-db/postgres -maxdepth 1 -type f | wc -l')"
test "$file_count" -eq 2
visible_tmp_count="$(docker run --rm -v "$replicated_volume:/replicated" postgres:16-alpine \
  sh -lc 'find /replicated/sql-db/postgres -maxdepth 1 -type f -name "*.tmp" | wc -l')"
test "$visible_tmp_count" -eq 0
hidden_file_count="$(docker run --rm -v "$replicated_volume:/replicated" postgres:16-alpine \
  sh -lc 'find /replicated/sql-db/postgres -maxdepth 1 -type f -name ".*" | wc -l')"
test "$hidden_file_count" -eq 0
docker run --rm -v "$replicated_volume:/replicated" postgres:16-alpine \
  sh -lc 'pg_restore -l "$(find /replicated/sql-db/postgres -name "*.dump" | head -n 1)" >/dev/null'

echo "sql-db schema guardrail and backup tests passed"

#!/bin/sh
set -eu

db_name="${POSTGRES_DB:-services}"
db_user="${POSTGRES_USER:-services}"

pg_isready -U "$db_user" -d "$db_name" >/dev/null

if [ "$(psql -X -U "$db_user" -d "$db_name" -tAc 'SELECT current_schema() IS NULL')" != "t" ]; then
  echo "sql-db health check: default connections must not select a writable schema" >&2
  exit 1
fi

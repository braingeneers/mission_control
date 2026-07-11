#!/bin/sh
set -eu

if [ "${1:-}" = "postgres" ]; then
  mkdir -p /cache/sql-db/backups /replicated/sql-db/postgres
  crond -b -l 8
fi

exec /usr/local/bin/docker-entrypoint.sh "$@"

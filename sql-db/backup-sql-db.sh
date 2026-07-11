#!/bin/sh
set -eu

db_host="${POSTGRES_HOST:-localhost}"
db_name="${POSTGRES_DB:-services}"
db_user="${POSTGRES_USER:-services}"
export PGPASSWORD="${POSTGRES_PASSWORD:-services}"

cache_dir="${SQL_DB_BACKUP_CACHE_DIR:-/cache/sql-db/backups}"
replicated_dir="${SQL_DB_BACKUP_REPLICATED_DIR:-/replicated/sql-db/postgres}"
rotation_days="${SQL_DB_BACKUP_ROTATION_DAYS:-30}"

mkdir -p "$cache_dir" "$replicated_dir"

attempts=0
until pg_isready -h "$db_host" -U "$db_user" -d "$db_name" >/dev/null 2>&1; do
  attempts=$((attempts + 1))
  if [ "$attempts" -ge 60 ]; then
    echo "sql-db backup: database did not become ready at ${db_host}" >&2
    exit 1
  fi
  sleep 2
done

epoch_day="$(($(date -u +%s) / 86400))"
slot="$(printf '%02d' "$((epoch_day % rotation_days))")"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
basename="services-rotation-${slot}"

tmp_dump="${cache_dir}/${basename}.dump.tmp"
cache_dump="${cache_dir}/${basename}.dump"
tmp_meta="${cache_dir}/${basename}.json.tmp"
cache_meta="${cache_dir}/${basename}.json"
final_dump="${replicated_dir}/${basename}.dump"
final_meta="${replicated_dir}/${basename}.json"

echo "[${stamp}] backing up ${db_name} database to ${final_dump}"

pg_dump -h "$db_host" -U "$db_user" -d "$db_name" -Fc -f "$tmp_dump"
mv "$tmp_dump" "$cache_dump"

printf '{"created_at":"%s","database":"%s","source_service":"sql-db","rotation_slot":"%s"}\n' \
  "$stamp" "$db_name" "$slot" > "$tmp_meta"
mv "$tmp_meta" "$cache_meta"

cp "$cache_dump" "${final_dump}.tmp"
mv "${final_dump}.tmp" "$final_dump"
cp "$cache_meta" "${final_meta}.tmp"
mv "${final_meta}.tmp" "$final_meta"

echo "[${stamp}] completed ${db_name} database backup slot ${slot}"

#!/bin/bash

DB_DIR="/root/rustdesk-data"
DB_FILE="${DB_DIR}/db_v2.sqlite3"
DB_SHM="${DB_DIR}/db_v2.sqlite3-shm"
DB_WAL="${DB_DIR}/db_v2.sqlite3-wal"
S3_BASE="s3://braingeneers/rustdesk"
S3_ENDPOINT="https://s3.braingeneers.gi.ucsc.edu"
RELAY_HOST="braingeneers.gi.ucsc.edu:21117"

mkdir -p "${DB_DIR}"

# hbbs stores its DB under /root; keep it persistent via symlinks into the volume.
for name in db_v2.sqlite3 db_v2.sqlite3-shm db_v2.sqlite3-wal; do
  root_path="/root/${name}"
  data_path="${DB_DIR}/${name}"
  if test -f "${root_path}" && ! test -f "${data_path}"; then
    mv "${root_path}" "${data_path}"
  fi
  ln -sf "${data_path}" "${root_path}"
done

# Download database files from S3 if they don't exist
if ! test -f "${DB_FILE}"; then
  aws --endpoint "${S3_ENDPOINT}" s3 cp "${S3_BASE}/db_v2.sqlite3" "${DB_FILE}"
  aws --endpoint "${S3_ENDPOINT}" s3 cp "${S3_BASE}/db_v2.sqlite3-shm" "${DB_SHM}"
  aws --endpoint "${S3_ENDPOINT}" s3 cp "${S3_BASE}/db_v2.sqlite3-wal" "${DB_WAL}"
fi

# Back up database files in the background every hour
{
  while true; do
    aws --endpoint "${S3_ENDPOINT}" s3 cp "${DB_FILE}" "${S3_BASE}/db_v2.sqlite3"
    aws --endpoint "${S3_ENDPOINT}" s3 cp "${DB_SHM}" "${S3_BASE}/db_v2.sqlite3-shm"
    aws --endpoint "${S3_ENDPOINT}" s3 cp "${DB_WAL}" "${S3_BASE}/db_v2.sqlite3-wal"
    sleep 3600
  done
} &

echo "Starting hbbr..."
hbbr &
hbbr_pid=$!

echo "Starting hbbs..."
hbbs -r "${RELAY_HOST}" &
hbbs_pid=$!

trap 'kill ${hbbr_pid} ${hbbs_pid}; wait ${hbbr_pid} ${hbbs_pid}' TERM INT
wait -n ${hbbr_pid} ${hbbs_pid}

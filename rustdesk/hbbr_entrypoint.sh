#!/bin/bash

# Download database files from S3 if they don't exist
if ! test -f '/root/db_v2.sqlite3'; then
  aws --endpoint https://s3.braingeneers.gi.ucsc.edu s3 cp s3://braingeneers/rustdesk/db_v2.sqlite3 /root/rustdesk-data/
  aws --endpoint https://s3.braingeneers.gi.ucsc.edu s3 cp s3://braingeneers/rustdesk/db_v2.sqlite3-shm /root/rustdesk-data/
  aws --endpoint https://s3.braingeneers.gi.ucsc.edu s3 cp s3://braingeneers/rustdesk/db_v2.sqlite3-wal /root/rustdesk-data/
fi

# Back up database files in the background every hour
{
  while true; do
    aws --endpoint https://s3.braingeneers.gi.ucsc.edu s3 cp /root/rustdesk-data/db_v2.sqlite3 s3://braingeneers/rustdesk/db_v2.sqlite3
    aws --endpoint https://s3.braingeneers.gi.ucsc.edu s3 cp /root/rustdesk-data/db_v2.sqlite3-shm s3://braingeneers/rustdesk/db_v2.sqlite3-shm
    aws --endpoint https://s3.braingeneers.gi.ucsc.edu s3 cp /root/rustdesk-data/db_v2.sqlite3-wal s3://braingeneers/rustdesk/db_v2.sqlite3-wal
    sleep 3600
  done
} &

# Run hbbr (relay server) in foreground
hbbr

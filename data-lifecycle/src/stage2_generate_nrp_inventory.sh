#!/usr/bin/env bash

set -euo pipefail

echo ""
echo "#"
echo "# Stage 2: Scan PRP/S3 and generate inventory."
echo "#"

# Optional defaults, override via environment or Docker
: "${LOCAL_SCRATCH_DIR:=/tmp}"
: "${NRP_ENDPOINT:=https://s3.braingeneers.gi.ucsc.edu}"
: "${PRIMARY_INVENTORY_PATH:=s3://braingeneers/services/data-lifecycle/}"

function fetch_s3_paths {
  echo "Parsing data-lifecycle.yaml for S3 paths..."
  yq eval '.backup.include_paths[]' data-lifecycle.yaml
}

function extract_bucket {
  sed -E 's|s3://([^/]+).*|\1|'
}

function extract_prefix {
  sed -E 's|s3://[^/]+/?(.*)|\1|'
}

function scan_s3_inventory {
  local s3_path="$1"
  local bucket
  local prefix
  local remote_path
  local listing_file
  local error_log
  local full_log

  bucket=$(echo "$s3_path" | extract_bucket)
  prefix=$(echo "$s3_path" | extract_prefix)
  remote_path="s3west:${bucket}/${prefix}"
  listing_file="${LOCAL_SCRATCH_DIR}/tmp_listing.txt"
  error_log="${LOCAL_SCRATCH_DIR}/rclone_errors.log"
  full_log="${LOCAL_SCRATCH_DIR}/rclone_full.log"

  echo "🟢 Scanning: $remote_path"

  # Run rclone and save file list to a temp file
  rclone lsf --recursive --fast-list "$remote_path" \
    --log-file="$full_log" --log-level INFO > "$listing_file" 2>> "$error_log"

  echo "✅ Listing complete. Processing paths..."
  generate_csv_from_listing "$listing_file" "$bucket" "$prefix"
}

function generate_csv_from_listing {
  local listing_file="$1"
  local bucket="$2"
  local prefix="$3"
  local count=0

  while read -r path; do
    ((count++))
    if (( count == 1 )); then
      echo -n "Processed: 1"
    elif (( count % 500 == 0 )); then
      echo -n "...$count"
    fi
    echo "UNKNOWN_DATE,\"s3://${bucket}/${prefix:+${prefix}/}${path}\""
  done < "$listing_file" >> "${LOCAL_SCRATCH_DIR}/local_inventory.csv"

  echo ""
  echo "✅ Completed: s3://${bucket}/${prefix} — $count objects"
}

function upload_inventory {
  local attempts=0
  local max_attempts=10
  local output_path="${PRIMARY_INVENTORY_PATH}local_inventory.csv.gz"

  echo "Uploading inventory CSV to: $output_path"

  while [[ $attempts -lt $max_attempts ]]; do
    gzip -c "${LOCAL_SCRATCH_DIR}/local_inventory.csv" | \
      aws --endpoint "${NRP_ENDPOINT}" s3 cp - "$output_path" && {
        echo "✅ Saved: $output_path"
        return
      }
    ((attempts++))
    echo "❌ Upload attempt $attempts failed, retrying in 5 seconds..."
    sleep 5
  done

  echo "🔥 Failed to upload inventory after $max_attempts attempts."
}

function main {
  : > "${LOCAL_SCRATCH_DIR}/local_inventory.csv"
  : > "${LOCAL_SCRATCH_DIR}/rclone_errors.log"

  fetch_s3_paths | while read -r s3_path; do
    scan_s3_inventory "$s3_path"
  done

  echo "🧾 Inventory scan complete. CSV: ${LOCAL_SCRATCH_DIR}/local_inventory.csv"
  echo "📄 Errors logged to: ${LOCAL_SCRATCH_DIR}/rclone_errors.log"

  upload_inventory
}

main

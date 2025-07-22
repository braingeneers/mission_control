#!/usr/bin/env bash

set -euo pipefail

#####################################################################################
## Stage 2:
## Crawl PRP/S3 and generate an inventory of files using rclone, with progress shown
#####################################################################################

echo ""
echo "#"
echo "# Stage 2: Scan PRP/S3 and generate inventory."
echo "#"

# Optional defaults, override via Docker env
: "${LOCAL_SCRATCH_DIR:=/tmp}"
: "${NRP_ENDPOINT:=https://your-nrp-endpoint}"
: "${PRIMARY_INVENTORY_PATH:=s3://braingeneers/services/data-lifecycle/}"

#-----------------------------
# Fetch S3 paths from YAML
#-----------------------------
function fetch_s3_paths {
  echo "Parsing data-lifecycle.yaml for S3 paths..."
  yq eval '.backup.include_paths[]' data-lifecycle.yaml
}

#-----------------------------
# Extract bucket and prefix
#-----------------------------
function extract_bucket {
  sed -E 's|s3://([^/]+).*|\1|'
}

function extract_prefix {
  sed -E 's|s3://[^/]+/?(.*)|\1|'
}

#-----------------------------
# Process S3 path into inventory via FIFO
#-----------------------------
function scan_s3_inventory {
  local s3_path="$1"
  local bucket
  local prefix
  local remote_path
  local fifo="${LOCAL_SCRATCH_DIR}/rclone_fifo"
  local error_log="${LOCAL_SCRATCH_DIR}/rclone_errors.log"
  local full_log="${LOCAL_SCRATCH_DIR}/rclone_full.log"

  bucket=$(echo "$s3_path" | extract_bucket)
  prefix=$(echo "$s3_path" | extract_prefix)
  remote_path="s3west:${bucket}/${prefix}"

  echo "🟢 Scanning: $remote_path"

  rm -f "$fifo"
  mkfifo "$fifo"

  # Background: rclone writes to FIFO
  rclone lsf --recursive --fast-list "$remote_path" \
    --log-file="$full_log" --log-level INFO > "$fifo" 2>> "$error_log" &

  # Foreground: read from FIFO and build CSV
  generate_csv_from_fifo "$fifo" "$bucket" "$prefix"

  echo ""
  echo "✅ Completed: s3://${bucket}/${prefix}"

  rm -f "$fifo"
}

#-----------------------------
# Read paths from FIFO and generate CSV with inline progress
#-----------------------------
function generate_csv_from_fifo {
  local fifo="$1"
  local bucket="$2"
  local prefix="$3"
  local count=0

  echo -n "Processed: 1"
  while read -r path; do
    ((count++))
    if (( count % 500 == 0 && count > 1 )); then
      echo -n "...$count"
    fi
    echo "UNKNOWN_DATE,\"s3://${bucket}/${prefix:+${prefix}/}${path}\"" >> "${LOCAL_SCRATCH_DIR}/local_inventory.csv"
  done < "$fifo"
}

#-----------------------------
# Upload generated CSV with retry logic
#-----------------------------
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

#-----------------------------
# Main: Orchestrate inventory workflow
#-----------------------------
function main {
  : > "${LOCAL_SCRATCH_DIR}/local_inventory.csv"
  : > "${LOCAL_SCRATCH_DIR}/rclone_errors.log"

  fetch_s3_paths | while read -r s3_path; do
    scan_s3_inventory "$s3_path"
  done

  echo "🧾 Inventory scan complete. CSV saved to: ${LOCAL_SCRATCH_DIR}/local_inventory.csv"
  echo "📄 Any rclone errors logged to: ${LOCAL_SCRATCH_DIR}/rclone_errors.log"

  upload_inventory
}

main

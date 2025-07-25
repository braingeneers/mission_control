#!/usr/bin/env bash

set -euo pipefail

#####################################################################################
## Stage 2:
## Crawl PRP/S3 and generate an inventory of files using rclone, with debug-friendly progress
#####################################################################################

echo ""
echo "#"
echo "# Stage 2: Scan PRP/S3 and generate inventory."
echo "#"

# Optional defaults, override via Docker ENV
: "${LOCAL_SCRATCH_DIR:=/tmp}"
: "${NRP_ENDPOINT:=https://your-nrp-endpoint}"
: "${PRIMARY_INVENTORY_PATH:=s3://braingeneers/services/data-lifecycle/}"

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
# Scan one S3 path using rclone and store in temp file
#-----------------------------
function scan_s3_inventory {
  local s3_path="$1"
  local bucket
  local prefix
  local remote_path
  local listing_file="${LOCAL_SCRATCH_DIR}/rclone_list.txt"
  local error_log="${LOCAL_SCRATCH_DIR}/rclone_errors.log"
  local full_log="${LOCAL_SCRATCH_DIR}/rclone_full.log"

  bucket=$(echo "$s3_path" | extract_bucket)
  prefix=$(echo "$s3_path" | extract_prefix)
  remote_path="s3west:${bucket}/${prefix}"

  echo "🟢 Scanning: $remote_path"

  # Clear any previous file
  rm -f "$listing_file"

  #-----------------------------------------
  # Background progress monitor
  # Prints: 1...500...1000... as file grows
  #-----------------------------------------
  echo -n "1..."  # Initial output for first entry

  (
    count=0
    while sleep 1; do
      [[ -f "$listing_file" ]] || continue
      lines=$(wc -l < "$listing_file")
      if (( lines >= count + 500 )); then
        count=$(( ((lines / 500)) * 500 ))
        echo -n "${count}..."
      fi
    done
  ) &
  monitor_pid=$!

  # Run rclone and output to file (debuggable)
  rclone lsf --recursive --fast-list "$remote_path" \
    --log-file="$full_log" --log-level INFO > "$listing_file" 2>> "$error_log"

  # Clean up progress monitor
  kill "$monitor_pid" 2>/dev/null || true
  wait "$monitor_pid" 2>/dev/null || true

  # Ensure newline after final progress batch
  echo ""

  # Process the file and generate CSV
  generate_csv_from_file "$listing_file" "$bucket" "$prefix"

  echo ""
  echo "✅ Completed: s3://${bucket}/${prefix}"
}

#-----------------------------
# Convert listing file to CSV (progress now handled in scan)
#-----------------------------
function generate_csv_from_file {
  local listing_file="$1"
  local bucket="$2"
  local prefix="$3"

  while read -r path; do
    echo "UNKNOWN_DATE,\"s3://${bucket}/${prefix:+${prefix}/}${path}\"" >> "${LOCAL_SCRATCH_DIR}/local_inventory.csv"
  done < "$listing_file"
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

  echo "Parsing data-lifecycle.yaml for S3 paths..."
  s3_paths=$(yq eval '.backup.include_paths[]' data-lifecycle.yaml)

  echo "Found the following S3 paths:"
  echo "$s3_paths" | sed 's/^/ - /'

  echo ""
  echo "# Starting inventory scan..."
  echo ""

  echo "$s3_paths" | while read -r s3_path; do
    scan_s3_inventory "$s3_path"
  done

  echo ""
  echo "🧾 Inventory scan complete. CSV saved to: ${LOCAL_SCRATCH_DIR}/local_inventory.csv"
  echo "📄 Any rclone errors logged to: ${LOCAL_SCRATCH_DIR}/rclone_errors.log"

  upload_inventory
}

main

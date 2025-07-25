#!/usr/bin/env bash

set -euo pipefail

#####################################################################################
## Stage 2:
## Crawl PRP/S3 and generate an inventory of files using rclone with accurate timestamps
#####################################################################################

echo ""
echo "#"
echo "# Stage 2: Scan PRP/S3 and generate inventory."
echo "#"

: "${LOCAL_SCRATCH_DIR:=/tmp}"
: "${NRP_ENDPOINT:=https://your-nrp-endpoint}"
: "${PRIMARY_INVENTORY_PATH:=s3://braingeneers/services/data-lifecycle/}"

function extract_bucket {
  sed -E 's|s3://([^/]+).*|\1|'
}

function extract_prefix {
  sed -E 's|s3://[^/]+/?(.*)|\1|'
}

function scan_s3_inventory {
  local s3_path="$1"
  local bucket prefix remote_path listing_file error_log full_log

  bucket=$(echo "$s3_path" | extract_bucket)
  prefix=$(echo "$s3_path" | extract_prefix)
  remote_path="s3west:${bucket}/${prefix}"
  listing_file="${LOCAL_SCRATCH_DIR}/rclone_list.json"
  error_log="${LOCAL_SCRATCH_DIR}/rclone_errors.log"
  full_log="${LOCAL_SCRATCH_DIR}/rclone_full.log"

  echo "🟢 Scanning: $remote_path"
  rm -f "$listing_file"

  # Progress monitor
  echo -n "1..."
  (
    count=0
    while sleep 1; do
      [[ -f "$listing_file" ]] || continue
      lines=$(grep -c '^{.*}$' "$listing_file" || true)
      if (( lines >= count + 5000 )); then
        count=$(( ((lines / 5000)) * 5000 ))
        echo -n "${count}..."
      fi
    done
  ) &
  monitor_pid=$!

  # rclone lsjson provides timestamps
  rclone lsjson --recursive "$remote_path" \
    --log-file="$full_log" --log-level INFO > "$listing_file" 2>> "$error_log"

  kill "$monitor_pid" 2>/dev/null || true
  wait "$monitor_pid" 2>/dev/null || true
  echo ""

  generate_csv_from_json "$listing_file" "$bucket" "$prefix"
  echo "✅ Completed: s3://${bucket}/${prefix}"
}

function generate_csv_from_json {
  local listing_file="$1"
  local bucket="$2"
  local prefix="$3"

  jq -r --arg bucket "$bucket" --arg prefix "$prefix" '
    .[] | select(.IsDir == false) |
    "\(.ModTime | sub("\\.[0-9]+Z$"; "Z") | sub("Z$"; "+00:00") | sub(" "; "T")),\"s3://\($bucket)/\($prefix)\(.Path | @uri)\""
  ' "$listing_file" >> "${LOCAL_SCRATCH_DIR}/local_inventory.csv"
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

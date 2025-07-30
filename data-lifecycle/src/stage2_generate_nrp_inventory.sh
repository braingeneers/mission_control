#!/usr/bin/env bash
set -euo pipefail

: "${LOCAL_SCRATCH_DIR:=/tmp}"
: "${NRP_ENDPOINT:=https://your-nrp-endpoint}"
: "${PRIMARY_INVENTORY_PATH:=s3://braingeneers/services/data-lifecycle/}"

LOCAL_INVENTORY="${LOCAL_SCRATCH_DIR}/local_inventory.csv"
ERROR_LOG="${LOCAL_SCRATCH_DIR}/rclone_errors.log"
FULL_LOG="${LOCAL_SCRATCH_DIR}/rclone_full.log"
LISTING_FILE="${LOCAL_SCRATCH_DIR}/rclone_list.json"
OUTPUT_PATH="${PRIMARY_INVENTORY_PATH}local_inventory.csv.gz"

echo ""
echo "#"
echo "# Stage 2: Scan PRP/S3 and generate inventory."
echo "#"

echo ""
echo "📂 Output files will be written to:"
echo " - Inventory CSV (local):     $LOCAL_INVENTORY"
echo " - Compressed upload target:  $OUTPUT_PATH"
echo " - Error log:                 $ERROR_LOG"
echo " - Full rclone log:           $FULL_LOG"
echo " - Raw rclone listing:        $LISTING_FILE"
echo ""

echo "🔧 Initializing output files..."
: > "$LOCAL_INVENTORY"
: > "$ERROR_LOG"
rm -f "$LISTING_FILE"

echo "📖 Reading S3 paths from data-lifecycle.yaml..."
s3_paths=$(yq eval '.backup.include_paths[]' data-lifecycle.yaml)

echo "🔍 Found S3 paths to scan:"
echo "$s3_paths" | sed 's/^/ - /'

echo ""
echo "# Starting inventory scan..."
echo ""

while read -r s3_path; do
  [[ -z "$s3_path" ]] && continue
  echo ""
  echo "🔄 Processing: $s3_path"

  # Extract bucket and prefix
  bucket=$(echo "$s3_path" | sed -E 's|s3://([^/]+).*|\1|')
  prefix=$(echo "$s3_path" | sed -E 's|s3://[^/]+/?(.*)|\1|')
  remote_path="s3west:${bucket}/${prefix}"

  echo "🟢 Scanning remote path: $remote_path"
  rm -f "$LISTING_FILE"

  # Start progress monitor
  echo -n "Progress: 1..."
  (
    count=0
    while sleep 1; do
      [[ -f "$LISTING_FILE" ]] || continue
      lines=$(grep -c '^{.*}$' "$LISTING_FILE" || true)
      if (( lines >= count + 5000 )); then
        count=$(( ((lines / 5000)) * 5000 ))
        echo -n "${count}..."
      fi
    done
  ) &
  monitor_pid=$!

  # Perform scan
  rclone lsjson --recursive "$remote_path" \
    --log-file="$FULL_LOG" --log-level INFO > "$LISTING_FILE" 2>> "$ERROR_LOG"

  kill "$monitor_pid" 2>/dev/null || true
  wait "$monitor_pid" 2>/dev/null || true
  echo ""

  echo "📦 Parsing listing JSON to CSV..."
  jq -r --arg bucket "$bucket" --arg prefix "$prefix" '
    .[] | select(.IsDir == false) |
    "\(.ModTime | sub("\\.[0-9]+Z$"; "Z") | sub("Z$"; "+00:00") | sub(" "; "T")),\"s3://\($bucket)/\($prefix)\(.Path | @uri)\""
  ' "$LISTING_FILE" >> "$LOCAL_INVENTORY"

  echo "✅ Completed: s3://${bucket}/${prefix}"

done <<< "$s3_paths"

echo ""
echo "🧾 Inventory scan complete."

# Upload CSV to S3 (gzipped)
attempts=0
max_attempts=10

echo ""
echo "📤 Uploading compressed CSV to: $OUTPUT_PATH"
while [[ $attempts -lt $max_attempts ]]; do
  if gzip -c "$LOCAL_INVENTORY" | aws --endpoint "$NRP_ENDPOINT" s3 cp - "$OUTPUT_PATH"; then
    echo "✅ Successfully uploaded inventory to $OUTPUT_PATH"
    break
  fi
  ((attempts++))
  echo "❌ Upload failed (attempt $attempts). Retrying in 5 seconds..."
  sleep 5
done

if [[ $attempts -eq $max_attempts ]]; then
  echo "🔥 Failed to upload inventory after $max_attempts attempts."
fi

echo ""
echo "✅ Done. See output files in: $LOCAL_SCRATCH_DIR"

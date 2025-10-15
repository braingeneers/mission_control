#!/usr/bin/env bash
set -euo pipefail

LOCAL_INVENTORY="${LOCAL_SCRATCH_DIR}/local_inventory.csv"
ERROR_LOG="${LOCAL_SCRATCH_DIR}/rclone_errors.log"
FULL_LOG="${LOCAL_SCRATCH_DIR}/rclone_full.log"
LISTING_FILE="${LOCAL_SCRATCH_DIR}/rclone_list.json"
OUTPUT_PATH="${PRIMARY_INVENTORY_PATH}local_inventory.csv.gz"

echo -e "\n#"
echo   "# Stage 2: Scan PRP/S3 and generate inventory."
echo   "#"
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
echo "\n# Starting inventory scan..."

while read -r s3_path; do
  [[ -z "$s3_path" ]] && continue
  echo -e "\n🔄 Processing: $s3_path"

  bucket=$(echo "$s3_path" | sed -E 's|s3://([^/]+).*|\1|')
  prefix=$(echo "$s3_path" | sed -E 's|s3://[^/]+/?(.*)|\1|')
  remote_path="s3west:${bucket}/${prefix}"

  echo "🟢 Scanning remote path: $remote_path"
  rm -f "$LISTING_FILE"

  echo "⏳ Listing in progress. This may take some time."
  echo "👀 Monitor progress in: $LISTING_FILE"

  # Step 1: Run rclone, output JSON array directly
  rclone lsjson \
    --log-file="$FULL_LOG" \
    --log-level INFO \
    --checkers=32 \
    --transfers=32 \
    --fast-list \
    --recursive \
    --s3-list-version 2 \
    --s3-list-chunk 1000 \
    "$remote_path" \
    > "$LISTING_FILE" 2>> "$ERROR_LOG"

  # Step 2: Convert JSON array to NDJSON, overwrite listing file
  jq -c '.[]' "$LISTING_FILE" > "${LISTING_FILE}.ndjson"
  mv "${LISTING_FILE}.ndjson" "$LISTING_FILE"

  echo ""

  echo "📦 Parsing listing NDJSON to CSV..."
  jq -r --arg bucket "$bucket" --arg prefix "$prefix" '
    select(.IsDir == false) |
    "\(.ModTime | sub(\"\\.[0-9]+Z$\"; \"Z\") | sub(\"Z$\"; \"+00:00\") | sub(\" \"; \"T\")),\"s3://\($bucket)/\($prefix)\(.Path | @uri)\""
  ' "$LISTING_FILE" >> "$LOCAL_INVENTORY"

  echo "✅ Completed: s3://${bucket}/${prefix}"
done <<< "$s3_paths"

echo -e "\n🧾 Inventory scan complete."

attempts=0
max_attempts=10

echo -e "\n📤 Uploading compressed CSV to: $OUTPUT_PATH"
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

echo -e "\n✅ Done. See output files in: $LOCAL_SCRATCH_DIR"

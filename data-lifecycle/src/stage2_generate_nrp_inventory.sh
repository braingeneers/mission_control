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

  # Background process: rclone writes to FIFO
  rclone lsf --recursive --fast-list "$remote_path" \
    --log-file="$full_log" --log-level INFO > "$fifo" 2>> "$error_log" &

  # Foreground: process FIFO and show progress
  generate_csv_from_fifo "$fifo" "$bucket" "$prefix"

  echo ""
  echo "✅ Completed: s3://${bucket}/${prefix}"
  rm -f "$fifo"
}

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

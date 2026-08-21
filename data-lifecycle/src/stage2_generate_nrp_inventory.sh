#!/usr/bin/env bash
set -euo pipefail

LOCAL_INVENTORY="${LOCAL_SCRATCH_DIR}/local_inventory.csv"
ERROR_LOG="${LOCAL_SCRATCH_DIR}/rclone_errors.log"
FULL_LOG="${LOCAL_SCRATCH_DIR}/rclone_full.log"
LISTING_DIR="${LOCAL_SCRATCH_DIR}/rclone_list"
OUTPUT_PATH="${PRIMARY_INVENTORY_PATH}local_inventory.csv.gz"
BAD_PATHS_LOG="${LOCAL_SCRATCH_DIR}/rclone_bad_paths.log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_LIFECYCLE_CONFIG_PATH="${DATA_LIFECYCLE_CONFIG_PATH:-${SCRIPT_DIR}/data-lifecycle.yaml}"

RCLONE_LOG_LEVEL="${RCLONE_LOG_LEVEL:-INFO}"
RCLONE_FAST_LIST="${RCLONE_FAST_LIST:-1}"
RCLONE_NO_MIMETYPE="${RCLONE_NO_MIMETYPE:-1}"
RCLONE_USE_SERVER_MODTIME="${RCLONE_USE_SERVER_MODTIME:-1}"
RCLONE_S3_LIST_VERSION="${RCLONE_S3_LIST_VERSION:-2}"
RCLONE_S3_LIST_CHUNK="${RCLONE_S3_LIST_CHUNK:-1000}"
RCLONE_S3_ENCODING="${RCLONE_S3_ENCODING:-Slash,InvalidUtf8}"
RCLONE_S3_LIST_URL_ENCODE_EXPLICIT=0
if [[ -v RCLONE_S3_LIST_URL_ENCODE ]]; then
  RCLONE_S3_LIST_URL_ENCODE_EXPLICIT=1
fi
RCLONE_S3_LIST_URL_ENCODE="${RCLONE_S3_LIST_URL_ENCODE:-unset}"
RCLONE_LIST_RETRIES="${RCLONE_LIST_RETRIES:-3}"
RCLONE_LIST_RETRY_SLEEP_SECONDS="${RCLONE_LIST_RETRY_SLEEP_SECONDS:-2}"
RCLONE_SHARD_MAX_DEPTH="${RCLONE_SHARD_MAX_DEPTH:-2}"
RCLONE_SHARD_EXPAND_MIN_CHILDREN="${RCLONE_SHARD_EXPAND_MIN_CHILDREN:-50}"
default_shard_jobs=4
if command -v nproc >/dev/null 2>&1; then
  default_shard_jobs=$(nproc)
elif command -v sysctl >/dev/null 2>&1; then
  default_shard_jobs=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)
fi
if (( default_shard_jobs > 8 )); then
  default_shard_jobs=8
fi
if (( default_shard_jobs < 2 )); then
  default_shard_jobs=2
fi

RCLONE_SHARD_JOBS="${RCLONE_SHARD_JOBS:-$default_shard_jobs}"

if (( RCLONE_SHARD_JOBS < 1 )); then
  RCLONE_SHARD_JOBS=1
fi

RCLONE_LIST_FLAGS=(
  --log-file="$FULL_LOG"
  --log-level "$RCLONE_LOG_LEVEL"
  --s3-list-version "$RCLONE_S3_LIST_VERSION"
  --s3-list-chunk "$RCLONE_S3_LIST_CHUNK"
  --s3-encoding "$RCLONE_S3_ENCODING"
  --files-only
)

if (( RCLONE_FAST_LIST )); then
  RCLONE_LIST_FLAGS+=(--fast-list)
fi
if (( RCLONE_NO_MIMETYPE )); then
  RCLONE_LIST_FLAGS+=(--no-mimetype)
fi
if (( RCLONE_USE_SERVER_MODTIME )); then
  RCLONE_LIST_FLAGS+=(--use-server-modtime)
fi

RCLONE_DISCOVER_FLAGS=(
  --log-file="$FULL_LOG"
  --log-level "$RCLONE_LOG_LEVEL"
  --s3-list-version "$RCLONE_S3_LIST_VERSION"
  --s3-list-chunk "$RCLONE_S3_LIST_CHUNK"
  --s3-encoding "$RCLONE_S3_ENCODING"
)

resolve_list_url_encode_mode() {
  local attempt="$1"

  if (( RCLONE_S3_LIST_URL_ENCODE_EXPLICIT )); then
    printf '%s' "$RCLONE_S3_LIST_URL_ENCODE"
    return
  fi

  if (( attempt > 1 )); then
    printf 'true'
  else
    printf 'unset'
  fi
}

build_rclone_flags() {
  local command_kind="$1"
  local list_url_encode_mode="$2"
  local -n flags_out="$3"

  if [[ "$command_kind" == "lsjson" ]]; then
    flags_out=("${RCLONE_LIST_FLAGS[@]}")
  else
    flags_out=("${RCLONE_DISCOVER_FLAGS[@]}")
  fi

  if [[ "$list_url_encode_mode" != "unset" ]]; then
    flags_out+=(--s3-list-url-encode "$list_url_encode_mode")
  fi
}

log_stage2_warning() {
  local message="$1"
  printf '%s\n' "$message" | tee -a "$ERROR_LOG" >&2
}

log_rclone_retry_failure() {
  local command_name="$1"
  local attempt="$2"
  local exit_code="$3"
  local list_url_encode_mode="$4"
  local target_label="$5"

  local message
  message="⚠️  rclone ${command_name} attempt ${attempt}/${RCLONE_LIST_RETRIES} failed for ${target_label} (exit=${exit_code}, s3-list-url-encode=${list_url_encode_mode})."
  log_stage2_warning "$message"
}

rclone_lsf_with_retries() {
  local target_label="$1"
  local out_file="$2"
  local remote_target="$3"

  local attempt=1
  while (( attempt <= RCLONE_LIST_RETRIES )); do
    local list_url_encode_mode
    list_url_encode_mode=$(resolve_list_url_encode_mode "$attempt")

    local flags=()
    build_rclone_flags "lsf" "$list_url_encode_mode" flags

    local tmp_file="${out_file}.tmp.${attempt}.$$"
    if rclone lsf "${flags[@]}" --dirs-only --max-depth 1 "$remote_target" 2>> "$ERROR_LOG" > "$tmp_file"; then
      mv "$tmp_file" "$out_file"
      return 0
    else
      local exit_code=$?
      rm -f "$tmp_file"
      log_rclone_retry_failure "lsf" "$attempt" "$exit_code" "$list_url_encode_mode" "$target_label"
      if (( attempt == RCLONE_LIST_RETRIES )); then
        break
      fi
      sleep "$RCLONE_LIST_RETRY_SLEEP_SECONDS"
    fi
    ((attempt++))
  done
  return "${exit_code:-1}"
}

rclone_lsjson_with_retries() {
  local target_label="$1"
  local out_file="$2"
  local list_mode="$3"
  local remote_target="$4"

  local attempt=1
  while (( attempt <= RCLONE_LIST_RETRIES )); do
    local list_url_encode_mode
    list_url_encode_mode=$(resolve_list_url_encode_mode "$attempt")

    local flags=()
    build_rclone_flags "lsjson" "$list_url_encode_mode" flags

    local tmp_file="${out_file}.tmp.${attempt}.$$"
    local cmd_args=()
    case "$list_mode" in
      recursive)
        cmd_args=(--recursive "$remote_target")
        ;;
      max-depth-1)
        cmd_args=(--max-depth 1 "$remote_target")
        ;;
      *)
        log_stage2_warning "Unsupported rclone list mode: $list_mode"
        return 1
        ;;
    esac

    if rclone lsjson "${flags[@]}" "${cmd_args[@]}" 2>> "$ERROR_LOG" | lsjson_to_ndjson > "$tmp_file"; then
      mv "$tmp_file" "$out_file"
      return 0
    else
      local exit_code=$?
      rm -f "$tmp_file"
      log_rclone_retry_failure "lsjson" "$attempt" "$exit_code" "$list_url_encode_mode" "$target_label"
      if (( attempt == RCLONE_LIST_RETRIES )); then
        break
      fi
      sleep "$RCLONE_LIST_RETRY_SLEEP_SECONDS"
    fi
    ((attempt++))
  done
  return "${exit_code:-1}"
}

sanitize_path() {
  local raw="$1"
  local sanitized
  local digest
  sanitized=$(sed -E 's#[^A-Za-z0-9._-]+#_#g' <<< "$raw")
  digest=$(printf '%s' "$raw" | sha1sum | cut -c1-12)
  printf '%s__%s' "$sanitized" "$digest"
}

normalize_prefix() {
  local raw_prefix="$1"
  raw_prefix="${raw_prefix#/}"
  if [[ -n "$raw_prefix" && "$raw_prefix" != */ ]]; then
    raw_prefix="${raw_prefix}/"
  fi
  printf '%s' "$raw_prefix"
}

label_for_listing() {
  local bucket="$1"
  local prefix="$2"
  local label_prefix="${prefix%/}"
  if [[ -n "$label_prefix" ]]; then
    sanitize_path "${bucket}_${label_prefix}"
  else
    sanitize_path "$bucket"
  fi
}

lsjson_to_ndjson() {
  awk '
    {
      line=$0
      sub(/^[[:space:]]+/, "", line)
      sub(/[[:space:]]+$/, "", line)
      if (line == "[" || line == "]" || line == "[]") next
      sub(/,[[:space:]]*$/, "", $0)
      print
    }
  '
}

parse_ndjson_with_python() {
  local ndjson_file="$1"
  local extra_prefix="$2"

  python - "$ndjson_file" "$bucket" "$prefix" "$extra_prefix" "$LOCAL_INVENTORY" "$BAD_PATHS_LOG" <<'PY'
import csv
import json
import re
import sys

ndjson_path, bucket, prefix, extra_prefix, out_path, bad_log = sys.argv[1:]
bucket_prefix = f"{bucket}/{prefix}"
extra_prefix = extra_prefix.lstrip("/")
if extra_prefix and not extra_prefix.endswith("/"):
    extra_prefix = f"{extra_prefix}/"

def has_surrogates(value: str) -> bool:
    return any(0xD800 <= ord(ch) <= 0xDFFF for ch in value)

with open(out_path, "a", encoding="utf-8") as out_f, \
     open(bad_log, "a", encoding="utf-8") as bad_f, \
     open(ndjson_path, "rb") as in_f:
    writer = csv.writer(out_f, lineterminator="\n")
    for line_no, raw in enumerate(in_f, 1):
        if not raw.strip():
            continue
        try:
            line = raw.decode("utf-8", "surrogateescape")
        except Exception as exc:
            bad_f.write(f"{ndjson_path}:line {line_no}: decode_error: {exc}\n")
            continue
        try:
            obj = json.loads(line)
        except Exception as exc:
            preview = line[:200].replace("\n", "\\n")
            bad_f.write(f"{ndjson_path}:line {line_no}: json_error: {exc}: {preview!r}\n")
            continue
        if obj.get("IsDir") is True:
            continue
        mod_time = obj.get("ModTime", "") or ""
        if mod_time:
            mod_time = re.sub(r"\.[0-9]+Z$", "Z", mod_time)
            mod_time = re.sub(r"Z$", "+00:00", mod_time)
            mod_time = mod_time.replace(" ", "T")
        size_val = obj.get("Size", "")
        if size_val in ("", None):
            size_str = ""
        else:
            try:
                size_str = str(int(size_val))
            except (TypeError, ValueError):
                size_str = str(size_val)
        path_val = obj.get("Path", "") or ""
        if has_surrogates(path_val):
            path_bytes = path_val.encode("utf-8", "surrogateescape")
            bad_f.write(
                f"{ndjson_path}:line {line_no}: invalid_utf8_path: {path_bytes.hex()} path_repr={path_val!r}\n"
            )
            continue
        key = f"{bucket_prefix}{extra_prefix}{path_val}"
        writer.writerow([mod_time, key, size_str])
PY
}

parse_ndjson_file() {
  local ndjson_file="$1"
  local prefix_file="${ndjson_file}.prefix"
  local extra_prefix=""
  if [[ -f "$prefix_file" ]]; then
    extra_prefix=$(<"$prefix_file")
  fi
  parse_ndjson_with_python "$ndjson_file" "$extra_prefix"
}

sem_init() {
  local max="$1"
  local fifo
  fifo=$(mktemp -u)
  mkfifo "$fifo"
  exec 9<>"$fifo"
  rm -f "$fifo"
  for ((i = 0; i < max; i++)); do
    printf '.' >&9
  done
}

sem_acquire() {
  read -r -u 9 -n 1
}

sem_release() {
  printf '.' >&9
}

run_single_listing() {
  local remote_path="$1"
  local list_dir="$2"
  local out_file="$list_dir/listing.ndjson"

  rclone_lsjson_with_retries "$remote_path" "$out_file" "recursive" "$remote_path"
}

run_shard() {
  local shard="$1"
  local remote_path="$2"
  local list_dir="$3"
  local out_file
  local prefix_file
  local shard_prefix=""

  if [[ "$shard" == "__ROOT__" ]]; then
    out_file="$list_dir/root.ndjson"
    prefix_file="${out_file}.prefix"
    : > "$prefix_file"
    rclone_lsjson_with_retries "${remote_path} [root]" "$out_file" "max-depth-1" "$remote_path"
    return
  fi

  if [[ "$shard" == "__FILES__:"* ]]; then
    local shard_path="${shard#__FILES__:}"
    local safe_shard
    safe_shard=$(sanitize_path "${shard_path%/}")
    out_file="$list_dir/${safe_shard}__files.ndjson"
    prefix_file="${out_file}.prefix"
    shard_path="${shard_path#/}"
    shard_prefix=$(normalize_prefix "$shard_path")
    printf '%s' "$shard_prefix" > "$prefix_file"

    rclone_lsjson_with_retries "${remote_path%/}/$shard_path [files]" "$out_file" "max-depth-1" "${remote_path%/}/$shard_path"
    return
  fi

  local safe_shard
  safe_shard=$(sanitize_path "$shard")
  out_file="$list_dir/${safe_shard}.ndjson"
  prefix_file="${out_file}.prefix"
  shard="${shard#/}"
  shard_prefix=$(normalize_prefix "$shard")
  printf '%s' "$shard_prefix" > "$prefix_file"

  rclone_lsjson_with_retries "${remote_path%/}/$shard" "$out_file" "recursive" "${remote_path%/}/$shard"
}

run_sharded_listing() {
  local remote_path="$1"
  local list_dir="$2"
  local shards_file="$list_dir/shards.txt"
  local expanded_shards_file="$list_dir/shards.expanded.txt"

  if ! rclone_lsf_with_retries "$remote_path" "$shards_file" "$remote_path"; then
    echo "⚠️  Shard discovery failed; falling back to single listing."
    run_single_listing "$remote_path" "$list_dir"
    return
  fi

  awk 'NF {print}' "$shards_file" > "${shards_file}.clean"
  mv "${shards_file}.clean" "$shards_file"

  if ! [[ -s "$shards_file" ]]; then
    echo "⚠️  No shards found; falling back to single listing."
    run_single_listing "$remote_path" "$list_dir"
    return
  fi

  if (( RCLONE_SHARD_MAX_DEPTH < 2 )); then
    cp "$shards_file" "$expanded_shards_file"
  else
    : > "$expanded_shards_file"
    while IFS= read -r shard; do
      [[ -z "$shard" ]] && continue
      local child_file
      local safe_shard
      safe_shard=$(sanitize_path "$shard")
      child_file="$list_dir/shards.${safe_shard}.children"

      if ! rclone_lsf_with_retries "${remote_path%/}/$shard" "$child_file" "${remote_path%/}/$shard"; then
        echo "⚠️  Child shard discovery failed for $shard; listing as single shard."
        echo "$shard" >> "$expanded_shards_file"
        continue
      fi

      awk 'NF {print}' "$child_file" > "${child_file}.clean"
      mv "${child_file}.clean" "$child_file"
      local child_count
      child_count=$(wc -l < "$child_file")

      if (( child_count >= RCLONE_SHARD_EXPAND_MIN_CHILDREN )); then
        echo "__FILES__:${shard}" >> "$expanded_shards_file"
        while IFS= read -r child; do
          [[ -z "$child" ]] && continue
          echo "${shard}${child}" >> "$expanded_shards_file"
        done < "$child_file"
      else
        echo "$shard" >> "$expanded_shards_file"
      fi
    done < "$shards_file"
  fi

  printf "__ROOT__\n" >> "$expanded_shards_file"

  if ! [[ -s "$expanded_shards_file" ]]; then
    echo "⚠️  No shards found after expansion; falling back to single listing."
    run_single_listing "$remote_path" "$list_dir"
    return
  fi

  echo "🔀 Sharded listing enabled: $(wc -l < "$expanded_shards_file") shards, $RCLONE_SHARD_JOBS workers."

  sem_init "$RCLONE_SHARD_JOBS"
  local failed=0
  local failed_shards_file="$list_dir/failed_shards.log"
  rm -f "$failed_shards_file"

  while IFS= read -r shard; do
    [[ -z "$shard" ]] && continue
    sem_acquire
    {
      if ! run_shard "$shard" "$remote_path" "$list_dir"; then
        printf '%s\n' "$shard" >> "$failed_shards_file"
      fi
      sem_release
    } &
  done < "$expanded_shards_file"

  wait
  exec 9>&-
  exec 9<&-

  if [[ -s "$failed_shards_file" ]]; then
    local first_pass_failed_shards="${failed_shards_file}.parallel"
    mv "$failed_shards_file" "$first_pass_failed_shards"
    : > "$failed_shards_file"

    echo "⚠️  Retrying failed shards serially: $(wc -l < "$first_pass_failed_shards") shard(s)."
    while IFS= read -r shard; do
      [[ -z "$shard" ]] && continue
      echo "↻ Serial retry: $shard"
      if ! run_shard "$shard" "$remote_path" "$list_dir"; then
        printf '%s\n' "$shard" >> "$failed_shards_file"
      fi
    done < "$first_pass_failed_shards"

    if ! [[ -s "$failed_shards_file" ]]; then
      rm -f "$first_pass_failed_shards"
    fi
  fi

  if [[ -s "$failed_shards_file" ]]; then
    failed=1
  fi

  if (( failed )); then
    echo "❌ One or more shard listings failed. See $ERROR_LOG and $failed_shards_file for details."
    exit 1
  fi
}

echo -e "\n#"
echo   "# Stage 2: Scan NRP/S3 and generate inventory."
echo   "#"
echo ""
echo "📂 Output files will be written to:"
echo " - Inventory CSV (local):     $LOCAL_INVENTORY"
echo " - Compressed upload target:  $OUTPUT_PATH"
echo " - Error log:                 $ERROR_LOG"
echo " - Full rclone log:           $FULL_LOG"
echo " - Raw rclone listings dir:   $LISTING_DIR"
echo " - Bad paths log:             $BAD_PATHS_LOG"
echo " - Upload activity log:       ${LOCAL_SCRATCH_DIR}/activity.log"
echo ""

echo "🔧 Initializing output files..."
: > "$LOCAL_INVENTORY"
: > "$ERROR_LOG"
: > "$BAD_PATHS_LOG"
rm -rf "$LISTING_DIR"
mkdir -p "$LISTING_DIR"

echo "📖 Reading S3 paths from ${DATA_LIFECYCLE_CONFIG_PATH}..."
s3_paths=$(yq eval '.backup.include_paths[]' "${DATA_LIFECYCLE_CONFIG_PATH}")

echo "🔍 Found S3 paths to scan:"
echo "$s3_paths" | sed 's/^/ - /'
echo -e "\n# Starting inventory scan..."

while read -r s3_path; do
  [[ -z "$s3_path" ]] && continue
  echo -e "\n🔄 Processing: $s3_path"

  bucket=$(echo "$s3_path" | sed -E 's|s3://([^/]+).*|\1|')
  prefix=$(echo "$s3_path" | sed -E 's|s3://[^/]+/?(.*)|\1|')
  prefix=$(normalize_prefix "$prefix")
  remote_path="s3west:${bucket}/${prefix}"

  echo "🟢 Scanning remote path: $remote_path"

  list_label=$(label_for_listing "$bucket" "$prefix")
  list_dir="$LISTING_DIR/$list_label"
  rm -rf "$list_dir"
  mkdir -p "$list_dir"

  echo "⏳ Listing in progress. This may take some time."
  echo "👀 Listing files will appear in: $list_dir"

  if (( RCLONE_SHARD_JOBS > 1 )); then
    run_sharded_listing "$remote_path" "$list_dir"
  else
    run_single_listing "$remote_path" "$list_dir"
  fi

  echo "📦 Parsing listing NDJSON to CSV..."
  shopt -s nullglob
  ndjson_files=("$list_dir"/*.ndjson)
  shopt -u nullglob

  if (( ${#ndjson_files[@]} == 0 )); then
    echo "⚠️  No listing files found for $s3_path."
    continue
  fi

  bad_before=$(wc -l < "$BAD_PATHS_LOG" || echo 0)
  for ndjson_file in "${ndjson_files[@]}"; do
    parse_ndjson_file "$ndjson_file"
  done
  bad_after=$(wc -l < "$BAD_PATHS_LOG" || echo 0)
  bad_delta=$((bad_after - bad_before))
  if (( bad_delta > 0 )); then
    echo "⚠️  Bad paths logged to: $BAD_PATHS_LOG ($bad_delta entries for this prefix)."
  fi

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

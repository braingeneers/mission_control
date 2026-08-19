#!/usr/bin/env bash
set -euo pipefail

service_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
test_root="$(mktemp -d)"
trap 'trash "$test_root"' EXIT

source_dir="${test_root}/replicated"
state_dir="${test_root}/state"
mkdir -p "$source_dir" "$state_dir" "${test_root}/bin"

args_log="${test_root}/aws-args"
fake_aws="${test_root}/bin/aws"
cat > "$fake_aws" <<'EOF'
#!/bin/sh
printf '%s\n' "$@" > "$AWS_ARGS_LOG"
exit "${FAKE_AWS_EXIT:-0}"
EOF
chmod +x "$fake_aws"

run_sync() {
    AWS_ARGS_LOG="$args_log" \
    AWS_CLI="$fake_aws" \
    REPLICATED_SYNC_SOURCE="$source_dir" \
    REPLICATED_SYNC_STATE_DIR="$state_dir" \
    REPLICATED_SYNC_DESTINATION="${1:-s3://braingeneersdev/services/replicated}" \
    NRP_ENDPOINT="${NRP_ENDPOINT_OVERRIDE:-https://example.invalid}" \
        "$service_dir/sync-replicated-volume"
}

run_sync
grep -Fx -- '--endpoint-url' "$args_log" >/dev/null
grep -Fx -- 'https://example.invalid' "$args_log" >/dev/null
grep -Fx -- "${source_dir}/" "$args_log" >/dev/null
grep -Fx -- 's3://braingeneersdev/services/replicated/' "$args_log" >/dev/null
grep -Fx -- '.*' "$args_log" >/dev/null
grep -Fx -- '*/.*' "$args_log" >/dev/null
grep -Fx -- '*.tmp' "$args_log" >/dev/null
grep -Fx -- '*/*.tmp' "$args_log" >/dev/null
if grep -Fx -- '--delete' "$args_log" >/dev/null; then
    echo 'replicated-volume-backup test: sync unexpectedly deletes destination objects' >&2
    exit 1
fi
grep -Fx 'status=succeeded' "${state_dir}/last-attempt.env" >/dev/null
grep -Fx 'destination=s3://braingeneersdev/services/replicated/' \
    "${state_dir}/last-success.env" >/dev/null

REPLICATED_SYNC_STATE_DIR="$state_dir" \
    "$service_dir/healthcheck" >/dev/null

old_epoch="$(( $(date -u +%s) - 200 ))"
printf '%s\n' "$old_epoch" > "${state_dir}/last-success.epoch"
if REPLICATED_SYNC_STATE_DIR="$state_dir" \
    REPLICATED_SYNC_MAX_SUCCESS_AGE_SECONDS=100 \
    "$service_dir/healthcheck" >/dev/null 2>&1; then
    echo 'replicated-volume-backup test: stale success passed healthcheck' >&2
    exit 1
fi

printf '%s\n' "$(date -u +%s)" > "${state_dir}/last-success.epoch"
if FAKE_AWS_EXIT=9 run_sync; then
    echo 'replicated-volume-backup test: failed AWS sync returned success' >&2
    exit 1
fi
grep -Fx 'status=failed' "${state_dir}/last-attempt.env" >/dev/null
grep -Fx 'exit_code=9' "${state_dir}/last-attempt.env" >/dev/null
grep -Fx 'status=succeeded' "${state_dir}/last-success.env" >/dev/null

if REPLICATED_SYNC_SOURCE="${test_root}/missing" \
    REPLICATED_SYNC_STATE_DIR="$state_dir" \
    AWS_CLI="$fake_aws" \
    "$service_dir/sync-replicated-volume" >/dev/null 2>&1; then
    echo 'replicated-volume-backup test: missing source returned success' >&2
    exit 1
fi

if REPLICATED_SYNC_SOURCE="$source_dir" \
    REPLICATED_SYNC_STATE_DIR="$state_dir" \
    REPLICATED_SYNC_DESTINATION='https://example.invalid/not-s3' \
    AWS_CLI="$fake_aws" \
    "$service_dir/sync-replicated-volume" >/dev/null 2>&1; then
    echo 'replicated-volume-backup test: invalid destination returned success' >&2
    exit 1
fi

lock_ready="${test_root}/lock-ready"
flock "${state_dir}/sync.lock" sh -c "touch '$lock_ready'; sleep 30" &
lock_pid=$!
while [ ! -e "$lock_ready" ]; do
    sleep 0.05
done
set +e
run_sync >/dev/null 2>&1
lock_status=$?
set -e
kill "$lock_pid"
wait "$lock_pid" 2>/dev/null || true
if [ "$lock_status" -ne 75 ]; then
    echo "replicated-volume-backup test: overlap returned ${lock_status}, expected 75" >&2
    exit 1
fi

grep -Fx '0 2 * * * sync-replicated-volume' "$service_dir/crontab" >/dev/null

echo 'replicated-volume-backup tests passed'

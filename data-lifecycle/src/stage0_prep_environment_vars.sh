#!/usr/bin/env bash

DEFAULT_NRP_ENDPOINT="https://s3.braingeneers.gi.ucsc.edu"

export PRIMARY_INVENTORY_PATH="${PRIMARY_INVENTORY_PATH:-s3://braingeneers/services/data-lifecycle/inventory/}"
export LOCAL_SCRATCH_DIR="${LOCAL_SCRATCH_DIR:-/tmp}"
if [ -z "${NRP_ENDPOINT:-}" ]; then
  export NRP_ENDPOINT="${ENDPOINT:-$DEFAULT_NRP_ENDPOINT}"
else
  export NRP_ENDPOINT
fi
# Keep ENDPOINT aligned for tools/libraries that read ENDPOINT.
export ENDPOINT="${NRP_ENDPOINT}"
export GLACIER_BUCKET="${GLACIER_BUCKET:-braingeneers-backups-glacier}"
export GLACIER_ENDPOINT="${GLACIER_ENDPOINT:-https://s3.us-west-2.amazonaws.com}"
# An explicitly empty value selects the default AWS credential chain.
export GLACIER_PROFILE="${GLACIER_PROFILE-aws-braingeneers-backups}"
export AWS_INVENTORY_BUCKET="${AWS_INVENTORY_BUCKET:-braingeneers-backups-inventory}"
export AWS_INVENTORY_PREFIX="${AWS_INVENTORY_PREFIX:-braingeneers-backups-glacier/daily-inventory/}"
export DEBUG_RCLONE_LIMIT="${DEBUG_RCLONE_LIMIT:-0}"

# Get the date of the latest inventory file available on AWS
# Pipe command explained:
#   aws) List the inventory files in the daily-inventory folder
#   awk) Extract the date portion of the filename
#   sed) Remove trailing slash
#   grep) Filter out any filenames that aren't a date (e.g. data and hive)
#   sort) Sort the dates with newest last
#   tail) Select the last (newest) date
if [ -z "${LATEST_INVENTORY_MANIFEST_DATE:-}" ]; then
  glacier_profile_args=()
  if [ -n "${GLACIER_PROFILE}" ]; then
    glacier_profile_args=(--profile "${GLACIER_PROFILE}")
  fi
  export LATEST_INVENTORY_MANIFEST_DATE=$( \
    aws --endpoint "${GLACIER_ENDPOINT}" "${glacier_profile_args[@]}" s3 ls "s3://${AWS_INVENTORY_BUCKET}/${AWS_INVENTORY_PREFIX}" | \
    awk '{print $2}' |
    sed 's/\/$//' | \
    grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}-[0-9]{2}Z$' | \
    sort | \
    tail -n 1 \
  )
else
  export LATEST_INVENTORY_MANIFEST_DATE
fi

# Function to assert that a variable is not empty and only one line long
assert_one_line_non_empty() {
  local var_to_check="$1"
  if [ -z "$var_to_check" ]; then
    echo "Error: Variable is empty"
    return 1
  fi

  local line_count=$(echo -n "$var_to_check" | grep -c '^')
  if [ "$line_count" -ne 1 ]; then
    echo "Error: Variable contains more than one line"
    return 1
  fi
}

assert_one_line_non_empty "${LATEST_INVENTORY_MANIFEST_DATE}" || return 1

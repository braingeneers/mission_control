#!/usr/bin/env bash

export PRIMARY_INVENTORY_PATH="s3://braingeneers/services/data-lifecycle/inventory/"
export LOCAL_SCRATCH_DIR="/tmp"
export NRP_ENDPOINT="https://s3.braingeneers.gi.ucsc.edu"
export GLACIER_BUCKET="braingeneers-backups-glacier"
export GLACIER_ENDPOINT="https://s3.us-west-2.amazonaws.com"
export GLACIER_PROFILE="aws-braingeneers-backups"
export DEBUG_RCLONE_LIMIT="0"

# Get the date of the latest inventory file available on AWS
# Pipe command explained:
#   aws) List the inventory files in the daily-inventory folder
#   awk) Extract the date portion of the filename
#   sed) Remove trailing slash
#   grep) Filter out any filenames that aren't a date (e.g. data and hive)
#   sort) Sort the dates with newest last
#   tail) Select the last (newest) date
export LATEST_INVENTORY_MANIFEST_DATE=$( \
  aws --endpoint ${GLACIER_ENDPOINT} --profile ${GLACIER_PROFILE} s3 ls 's3://braingeneers-backups-inventory/braingeneers-backups-glacier/daily-inventory/' | \
  awk '{print $2}' |
  sed 's/\/$//' | \
  grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}-[0-9]{2}Z$' | \
  sort | \
  tail -n 1 \
)

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


#!/usr/bin/env bash
set -euo pipefail

#
# This script is used to run the data lifecycle process,
# backing up data from NRP/S3 to AWS/Glacier and deleting expired data.
# See mission_control/data-lifecycle/README.md for more information.
#

#####################################################################################
## Stage 1:
## Copy data-lifecycle.yaml file and latest AWS inventory file (both locally and to NRP/S3)
#####################################################################################

echo "#"
echo "# Stage 1: Prepare inventory files."
echo "#"
echo "Current date/time (UTC):" $(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Download the inventory manifest(s) from AWS, concatenate them and save the result to NRP/S3 and local
# Pipe command explained:
#   aws) Download manifest.json
#   jq) extract the list of possibly multiple inventory files from manifest.json
#   xargs) download each file using aws and unzip it, emitting the inventory as a CSV list
#   gzip) concatenate and gzip the resulting inventory
glacier_profile_args=()
if [ -n "${GLACIER_PROFILE:-}" ]; then
  glacier_profile_args=(--profile "${GLACIER_PROFILE}")
fi

aws --endpoint "${GLACIER_ENDPOINT}" "${glacier_profile_args[@]}" s3 cp "s3://${AWS_INVENTORY_BUCKET}/$(printf '%s' "${AWS_INVENTORY_PREFIX}" | sed 's#/*$##')/${LATEST_INVENTORY_MANIFEST_DATE}/manifest.json" - | \
  jq -r '.files[] | .key' | \
  xargs -I {} bash -c 'profile_args=(); if [ -n "${GLACIER_PROFILE:-}" ]; then profile_args=(--profile "${GLACIER_PROFILE}"); fi; aws --endpoint "${GLACIER_ENDPOINT}" "${profile_args[@]}" s3 cp "s3://${AWS_INVENTORY_BUCKET}/{}" - | gunzip -c' | \
  gzip -c > ${LOCAL_SCRATCH_DIR}/glacier_inventory.csv.gz
echo "Copied s3://${AWS_INVENTORY_BUCKET}/${AWS_INVENTORY_PREFIX}${LATEST_INVENTORY_MANIFEST_DATE}/manifest.json to: ${LOCAL_SCRATCH_DIR}/glacier_inventory.csv.gz"
# Upload the glacier manifest to NRP/S3
aws --endpoint "${NRP_ENDPOINT}" s3 cp "${LOCAL_SCRATCH_DIR}/glacier_inventory.csv.gz" "${PRIMARY_INVENTORY_PATH}glacier_inventory.csv.gz"
gunzip -f ${LOCAL_SCRATCH_DIR}/glacier_inventory.csv.gz

#!/usr/bin/env bash

#
# This script is used to run the data lifecycle process,
# backing up data from PRP/S3 to AWS/Glacier and deleting expired data.
# See the README.md file in repo braingeneers/data-lifecycle for more information.
#

#####################################################################################
## Stage 1:
## Copy data-lifecycle.yaml file and latest AWS inventory file (both locally and to PRP/S3)
#####################################################################################

echo "#"
echo "# Stage 1: Prepare inventory files."
echo "#"

# Download the inventory manifest(s) from AWS, concatenate them and save the result to PRP/S3 and local
# Pipe command explained:
#   aws) Download manifest.json
#   jq) extract the list of possibly multiple inventory files from manifest.json
#   xargs) download each file using aws and unzip it, emitting the inventory as a CSV list
#   gzip) concatenate and gzip the resulting inventory
aws --endpoint ${GLACIER_ENDPOINT} --profile ${GLACIER_PROFILE} s3 cp s3://braingeneers-backups-inventory/braingeneers-backups-glacier/daily-inventory/${LATEST_INVENTORY_MANIFEST_DATE}/manifest.json - | \
  jq -r '.files[] | .key' | \
  xargs -I {} bash -c 'aws --endpoint ${GLACIER_ENDPOINT} --profile ${GLACIER_PROFILE} s3 cp "s3://braingeneers-backups-inventory/{}" - | gunzip -c' | \
  gzip -c > ${LOCAL_SCRATCH_DIR}/glacier_inventory.csv.gz
echo "saved: ${LOCAL_SCRATCH_DIR}/glacier_inventory.csv.gz"
# Upload the glacier manifest to PRP/S3
aws --endpoint ${NRP_ENDPOINT} s3 cp ${LOCAL_SCRATCH_DIR}/glacier_inventory.csv.gz ${PRIMARY_INVENTORY_PATH}glacier_inventory.csv.gz
gunzip -f ${LOCAL_SCRATCH_DIR}/glacier_inventory.csv.gz


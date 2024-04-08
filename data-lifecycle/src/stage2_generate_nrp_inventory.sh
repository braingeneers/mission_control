#!/usr/bin/env bash

#####################################################################################
## Stage 2:
## Crawl the PRP/S3 and generate an inventory of the files using aws CLI
#####################################################################################

# Copy the result to PRP/S3 at s3://braingeneers/services/data-lifecycle/local-inventory.csv
# Note that rclone wasn't used here because it has a bug in which filenames with // in them aren't processed properly.
# CSV output format example: 2022-01-30T11:21:50+00:00,"braingeneersdev/tmp/test"
echo ""
echo "#"
echo "# Stage 2: Scan PRP/S3 and generate inventory."
echo "#"

yq eval '.backup.include_paths[]' data-lifecycle.yaml | \
  xargs -I {} sh -c 'aws --endpoint ${NRP_ENDPOINT} s3 ls --recursive {} |  awk -v path={} "{ sub(/s3:\/\//, \"\", path); print \$1\"T\"\$2\"+00:00,\\\"\"path\$4\"\\\"\" }"' | \
  tee ${LOCAL_SCRATCH_DIR}/local_inventory.csv | \
  { I=0; while read; do printf "Processed: $((++I))\r"; done; echo ""; }
# Attempt to upload, retry on failure 10 times, transient failures have been a problem here.
for i in {1..10}; do
  gzip -c ${LOCAL_SCRATCH_DIR}/local_inventory.csv | aws --endpoint ${NRP_ENDPOINT} s3 cp - ${PRIMARY_INVENTORY_PATH}local_inventory.csv.gz && break || sleep 5;
done
echo "saved: ${PRIMARY_INVENTORY_PATH}local_inventory.csv.gz"


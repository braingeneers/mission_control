#!/usr/bin/env bash
set -e

#
# This script is used to run the data lifecycle process,
# backing up data from PRP/S3 to AWS/Glacier and deleting expired data.
# See the README.md file in repo braingeneers/data-lifecycle for more information.
#

CONFIG_FILE_PATH="${CONFIG_FILE_PATH:=s3://braingeneers/services/data-lifecycle/data-lifecycle.yaml}"
PRIMARY_INVENTORY_PATH="${PRIMARY_INVENTORY_PATH:=s3://braingeneers/services/data-lifecycle/inventory/}"
LOCAL_SCRATCH_DIR="/tmp"
ENDPOINT=${ENDPOINT:=https://s3-west.nrp-nautilus.io}
AWS_BUCKET='braingeneers-backups-glacier'
AWS_ENDPOINT='https://s3.us-west-2.amazonaws.com'
AWS_INVENTORY_PATH=s3://braingeneers-backups-inventory/braingeneers-backups-glacier/daily-inventory/data/
LATEST_INVENTORY_FILE=$(aws --endpoint ${AWS_ENDPOINT} --profile aws-braingeneers-backups s3 ls ${AWS_INVENTORY_PATH} | sort | tail -n 1 | awk '{print $4}')

#
# Stage 1:
# Copy data-lifecycle.yaml file and latest AWS inventory file (both locally and to PRP/S3)
#
echo "#"
echo "# Stage 1: Prepare inventory files."
echo "#"
aws --endpoint ${ENDPOINT} s3 cp ${CONFIG_FILE_PATH} ${LOCAL_SCRATCH_DIR}/data-lifecycle.yaml
aws --endpoint ${AWS_ENDPOINT} --profile aws-braingeneers-backups s3 cp ${AWS_INVENTORY_PATH}${LATEST_INVENTORY_FILE} ${LOCAL_SCRATCH_DIR}/glacier_inventory.csv.gz
aws --endpoint ${ENDPOINT} s3 cp ${LOCAL_SCRATCH_DIR}/glacier_inventory.csv.gz ${PRIMARY_INVENTORY_PATH}glacier_inventory.csv.gz
gunzip -f ${LOCAL_SCRATCH_DIR}/glacier_inventory.csv.gz

#
# Stage 2:
# Crawl the PRP/S3 and generate an inventory of the files using aws CLI
#

# Copy the result to PRP/S3 at s3://braingeneers/services/data-lifecycle/local-inventory.csv
# Note that rclone wasn't used here because it has a bug in which filenames with // in them aren't processed properly.
# CSV output format example: 2022-01-30T11:21:50+00:00,"braingeneersdev/tmp/test"
echo -e "\n#"
echo "# Stage 2: Scan PRP/S3 and generate inventory."
echo "#"
yq eval '.backup.include_paths[]' ${LOCAL_SCRATCH_DIR}/data-lifecycle.yaml | \
  xargs -I {} sh -c 'aws --endpoint ${ENDPOINT} s3 ls --recursive {} |  awk -v path={} "{ sub(/s3:\/\//, \"\", path); print \$1\"T\"\$2\"+00:00,\\\"\"path\$4\"\\\"\" }"' | \
  tee ${LOCAL_SCRATCH_DIR}/local_inventory.csv
gzip -c ${LOCAL_SCRATCH_DIR}/local_inventory.csv | aws --endpoint ${ENDPOINT} s3 cp - ${PRIMARY_INVENTORY_PATH}local_inventory.csv.gz

#
# Stage 3:
# Run python script to generate PUTS and DELETES based on the two inventory files.
#
echo -e "\n#"
echo "# Stage 3: Generate PUTS and DELETES."
echo "#"
python generate_puts_deletes.py \
  --config ${LOCAL_SCRATCH_DIR}/data-lifecycle.yaml \
  --prp-inventory ${LOCAL_SCRATCH_DIR}/local_inventory.csv \
  --aws-inventory ${LOCAL_SCRATCH_DIR}/glacier_inventory.csv \
  --puts-output ${LOCAL_SCRATCH_DIR}/puts.txt \
  --deletes-output ${LOCAL_SCRATCH_DIR}/deletes.txt

#
# Stage 4:
# Run awscli to process PUTS and DELETES (deletes are removed from both PRP/S3 and AWS/Glacier)
#
echo -e "\n#"
echo "# Stage 4: Process PUTS and DELETES."
echo "#"

# If any aws s3 cp command fails, the || true part makes sure that the overall command returns a success status,
# so xargs can proceed to the next line.

# xargs -P 16 -I {} bash -c "(aws --endpoint ${ENDPOINT} --cli-connect-timeout 60 --cli-read-timeout 60 s3 cp 's3://{}' - | aws --profile aws-braingeneers-backups --region us-west-2 --cli-connect-timeout 60 --cli-read-timeout 60 s3 cp - 's3://${AWS_BUCKET}/{}') || true" < ${LOCAL_SCRATCH_DIR}/puts.txt

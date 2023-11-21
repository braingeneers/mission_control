#!/usr/bin/env bash
set -e
set -o pipefail

#
# This script is used to run the data lifecycle process,
# backing up data from PRP/S3 to AWS/Glacier and deleting expired data.
# See the README.md file in repo braingeneers/data-lifecycle for more information.
#

export PRIMARY_INVENTORY_PATH='s3://braingeneers/services/data-lifecycle/inventory/'
export LOCAL_SCRATCH_DIR='/tmp'
export NRP_ENDPOINT='https://s3.braingeneers.gi.ucsc.edu'
export GLACIER_BUCKET='braingeneers-backups-glacier'
export GLACIER_ENDPOINT='https://s3.us-west-2.amazonaws.com'
export GLACIER_PROFILE='aws-braingeneers-backups'

# Get the date of the latest inventory file available on AWS
# Pipe command explained:
#   aws) List the inventory files in the daily-inventory folder
#   awk) Extract the date portion of the filename
#   sed) Remove trailing slash
#   grep) Filter out any filenames that aren't a date (e.g. data and hive)
#   sort) Sort the dates with newest last
#   tail) Select the last (newest) date
LATEST_INVENTORY_MANIFEST_DATE=$( \
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
    exit 1
  fi

  local line_count=$(echo -n "$var_to_check" | grep -c '^')
  if [ "$line_count" -ne 1 ]; then
    echo "Error: Variable contains more than one line"
    exit 1
  fi
}

assert_one_line_non_empty "${LATEST_INVENTORY_MANIFEST_DATE}"

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

#####################################################################################
## Stage 2:
## Crawl the PRP/S3 and generate an inventory of the files using aws CLI
#####################################################################################

# Copy the result to PRP/S3 at s3://braingeneers/services/data-lifecycle/local-inventory.csv
# Note that rclone wasn't used here because it has a bug in which filenames with // in them aren't processed properly.
# CSV output format example: 2022-01-30T11:21:50+00:00,"braingeneersdev/tmp/test"
echo -e "\n#"
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

#####################################################################################
## Stage 3:
## Run python script to generate PUTS and DELETES based on the two inventory files.
#####################################################################################
echo -e "\n#"
echo "# Stage 3: Generate PUTS, DELETES, and NOTIFICATIONS."
echo "#"
python generate_puts_deletes.py \
  --config ./data-lifecycle.yaml \
  --prp-inventory ${LOCAL_SCRATCH_DIR}/local_inventory.csv \
  --aws-inventory ${LOCAL_SCRATCH_DIR}/glacier_inventory.csv \
  --puts-output ${LOCAL_SCRATCH_DIR}/puts.txt \
  --deletes-output ${LOCAL_SCRATCH_DIR}/deletes.txt \
  --notifications-output ${LOCAL_SCRATCH_DIR}/notifications.txt

#
# Stage 4:
# Run awscli to process PUTS and DELETES (deletes are removed from both PRP/S3 and AWS/Glacier, but Glacier keeps deleted files for a 1 year period)
#
echo -e "\n#"
echo "# Stage 4: Process PUTS and DELETES."
echo "#"

# If any aws s3 cp command fails, the || echo part makes sure that the overall command returns a success status
# so that xargs will proceed to the next line.
#
# Magic bash line below explained:
#  - Processes each line from puts.txt (< ${LOCAL_SCRATCH_DIR}/puts.txt)) in parallel (-P 16)
#  - Runs the aws s3 cp command to copy the file from PRP/S3 to AWS/Glacier via a pipe and two aws s3 cp commands
#  - If the aws s3 cp command succeeds, it prints "Uploaded: <filename>" to stdout or "Upload failed: <filename>" to stderr
#  - The last while read line prints a progress counter
xargs -P 16 -I {} bash -c \
  "( \
    aws --endpoint ${NRP_ENDPOINT} --cli-connect-timeout 60 --cli-read-timeout 60 s3 cp 's3://{}' - | \
    aws --profile aws-braingeneers-backups --region us-west-2 --cli-connect-timeout 60 --cli-read-timeout 60 s3 cp - 's3://${GLACIER_BUCKET}/{}' \
   ) ; if [ $? -eq 0 ]; then echo 'Uploaded: {}'; else echo 'Upload failed: {}' >&2; fi" < ${LOCAL_SCRATCH_DIR}/puts.txt | \
  { I=0; while read; do printf "Processed: $((++I))\r"; done; echo ""; }

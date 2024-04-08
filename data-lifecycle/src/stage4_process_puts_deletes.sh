#!/usr/bin/env bash

#####################################################################################################################################################
## Stage 4:
## Run awscli to process PUTS and DELETES (deletes are removed from both PRP/S3 and AWS/Glacier, but Glacier keeps deleted files for a 1 year period)
#####################################################################################################################################################

echo ""
echo "#"
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


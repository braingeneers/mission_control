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

# Function to fetch S3 paths and generate CSV
function generate_inventory_csv {
    yq eval '.backup.include_paths[]' data-lifecycle.yaml | \
    xargs -I {} sh -c "aws --endpoint ${NRP_ENDPOINT} s3 ls --recursive '{}' | \
    awk -v path='{}' '{start = index(\$0, \$4); filename = substr(\$0, start); sub(/s3:\/\//, \"\", path); print \$1\"T\"\$2\"+00:00,\\\"\"path filename\"\\\"\"}'" | \
    tee "${LOCAL_SCRATCH_DIR}/local_inventory.csv"
}

# Function to display processing progress
function track_progress {
    local I=0
    while read; do
        printf "Processed: $((++I))\r";
    done
    echo ""
}

# Function to upload file to S3 with retries
function upload_with_retry {
    local attempts=0
    local max_attempts=10
    while [[ $attempts -lt $max_attempts ]]; do
        # Attempt to gzip and upload the file
        gzip -c "${LOCAL_SCRATCH_DIR}/local_inventory.csv" | \
        aws --endpoint ${NRP_ENDPOINT} s3 cp - "${PRIMARY_INVENTORY_PATH}local_inventory.csv.gz" && {
            echo "Saved: ${PRIMARY_INVENTORY_PATH}local_inventory.csv.gz"
            return
        }
        # Increment attempt counter and log retry attempt
        ((attempts++))
        echo "Attempt $attempts of $max_attempts failed, retrying in 5 seconds..."
        sleep 5
    done
    echo "Failed to upload after $max_attempts attempts."
}

# Main function to orchestrate the workflow
function main {
    generate_inventory_csv | track_progress
    upload_with_retry
}

# Execute the main function
main


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
    echo "Parsing data-lifecycle.yaml for S3 paths..."

    # Extract S3 paths from YAML
    s3_paths=$(yq eval '.backup.include_paths[]' data-lifecycle.yaml)

    # Extract unique buckets
    buckets=$(echo "$s3_paths" | sed -E 's|s3://([^/]+).*|\1|' | sort -u)

    echo "Found the following buckets:"
    echo "$buckets" | sed 's/^/ - /'

    # Prepare inventory output
    : > "${LOCAL_SCRATCH_DIR}/local_inventory.csv"

    # Loop through each S3 path
    echo "$s3_paths" | while read -r s3_path; do
        bucket=$(echo "$s3_path" | sed -E 's|s3://([^/]+).*|\1|')
        prefix=$(echo "$s3_path" | sed -E 's|s3://[^/]+/?(.*)|\1|')

        # Use s3west:bucket/prefix syntax
        remote_path="s3west:${bucket}/${prefix}"

        echo "Processing bucket: $bucket"
        [ -n "$prefix" ] && echo " → Prefix: $prefix"

        rclone lsf --recursive --fast-list --progress "$remote_path" 2> >(tee -a "${LOCAL_SCRATCH_DIR}/rclone_errors.log" >&2) | \
        while read -r path; do
            echo "UNKNOWN_DATE,\"s3://${bucket}/${prefix:+${prefix}/}${path}\""
        done >> "${LOCAL_SCRATCH_DIR}/local_inventory.csv"
    done
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


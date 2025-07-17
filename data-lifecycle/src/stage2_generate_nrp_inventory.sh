function generate_inventory_csv {
    echo "Parsing data-lifecycle.yaml for S3 paths..."

    # Extract S3 paths from YAML
    s3_paths=$(yq eval '.backup.include_paths[]' data-lifecycle.yaml)

    # Extract unique buckets
    buckets=$(echo "$s3_paths" | sed -E 's|s3://([^/]+).*|\1|' | sort -u)

    echo "Found the following buckets:"
    echo "$buckets" | sed 's/^/ - /'

    : > "${LOCAL_SCRATCH_DIR}/local_inventory.csv"
    error_log="${LOCAL_SCRATCH_DIR}/rclone_errors.log"
    : > "$error_log"

    echo "Starting inventory scan..."

    echo "$s3_paths" | while read -r s3_path; do
        bucket=$(echo "$s3_path" | sed -E 's|s3://([^/]+).*|\1|')
        prefix=$(echo "$s3_path" | sed -E 's|s3://[^/]+/?(.*)|\1|')
        remote_path="s3west:${bucket}/${prefix}"

        echo "🟢 Scanning: $remote_path"
        count=0

        rclone lsf --recursive --fast-list --progress "$remote_path" 2> >(tee -a "$error_log" >&2) | \
        while read -r path; do
            ((count++))
            echo "Processed: $count"
            echo "UNKNOWN_DATE,\"s3://${bucket}/${prefix:+${prefix}/}${path}\""
        done >> "${LOCAL_SCRATCH_DIR}/local_inventory.csv"

        echo "✅ Completed: $remote_path — $count objects"
    done

    echo "Inventory scan complete. CSV saved to: ${LOCAL_SCRATCH_DIR}/local_inventory.csv"
    echo "Any rclone errors logged to: $error_log"
}

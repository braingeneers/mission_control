#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_LIFECYCLE_CONFIG_PATH="${DATA_LIFECYCLE_CONFIG_PATH:-${SCRIPT_DIR}/data-lifecycle.yaml}"

#####################################################################################
## Stage 3:
## Run python script to generate PUTS and DELETES based on the two inventory files.
#####################################################################################

echo ""
echo "#"
echo "# Stage 3: Generate PUTS, DELETES, and NOTIFICATIONS."
echo "#"
echo "📂 Stage 3 artifacts will be written to:"
echo " - PUT list:                   ${LOCAL_SCRATCH_DIR}/puts.txt"
echo " - DELETE list:                ${LOCAL_SCRATCH_DIR}/deletes.txt"
echo " - BADKEYS list:               ${LOCAL_SCRATCH_DIR}/badkeys.tsv"
echo " - Notifications CSV:          ${LOCAL_SCRATCH_DIR}/notifications.csv"
echo " - Cleanup window CSV:         ${LOCAL_SCRATCH_DIR}/cleanup_within_notification_window.csv"
echo " - Cleanup summary CSV:        ${LOCAL_SCRATCH_DIR}/cleanup_within_notification_window_summary.csv"
echo " - Cleanup Slack text:         ${LOCAL_SCRATCH_DIR}/cleanup_within_notification_window_slack.txt"
echo " - Comparison summary JSON:    ${LOCAL_SCRATCH_DIR}/comparison-summary.json"
echo " - Upload activity log:        ${LOCAL_SCRATCH_DIR}/activity.log"
python -u "${SCRIPT_DIR}/generate_puts_deletes.py" \
  --config "${DATA_LIFECYCLE_CONFIG_PATH}" \
  --prp-inventory ${LOCAL_SCRATCH_DIR}/local_inventory.csv \
  --aws-inventory ${LOCAL_SCRATCH_DIR}/glacier_inventory.csv \
  --puts-output ${LOCAL_SCRATCH_DIR}/puts.txt \
  --deletes-output ${LOCAL_SCRATCH_DIR}/deletes.txt \
  --badkeys-output ${LOCAL_SCRATCH_DIR}/badkeys.tsv \
  --notifications-output ${LOCAL_SCRATCH_DIR}/notifications.csv \
  --cleanup-window-output ${LOCAL_SCRATCH_DIR}/cleanup_within_notification_window.csv \
  --cleanup-summary-output ${LOCAL_SCRATCH_DIR}/cleanup_within_notification_window_summary.csv \
  --cleanup-slack-message-output ${LOCAL_SCRATCH_DIR}/cleanup_within_notification_window_slack.txt \
  --comparison-summary-output ${LOCAL_SCRATCH_DIR}/comparison-summary.json

echo ""
echo "#"
echo "# Stage 3: Upload notification artifacts."
echo "#"

upload_artifact_with_retries() {
  local source_file="$1"
  local destination_file="$2"
  local attempts=0
  local max_attempts=10

  while [[ $attempts -lt $max_attempts ]]; do
    if aws --endpoint "${NRP_ENDPOINT}" s3 cp "${source_file}" "${destination_file}"; then
      echo "Uploaded ${source_file} to ${destination_file}"
      return 0
    fi
    ((attempts++))
    echo "Upload failed for ${source_file} (attempt ${attempts}/${max_attempts}). Retrying in 5 seconds..."
    sleep 5
  done

  echo "WARNING: Failed to upload ${source_file} to ${destination_file} after ${max_attempts} attempts."
  return 1
}

cleanup_artifacts=(
  "${LOCAL_SCRATCH_DIR}/badkeys.tsv"
  "${LOCAL_SCRATCH_DIR}/notifications.csv"
  "${LOCAL_SCRATCH_DIR}/cleanup_within_notification_window_summary.csv"
  "${LOCAL_SCRATCH_DIR}/cleanup_within_notification_window_slack.txt"
)

for artifact in "${cleanup_artifacts[@]}"; do
  if [[ ! -f "${artifact}" ]]; then
    echo "WARNING: Missing expected cleanup artifact: ${artifact}"
    continue
  fi
  destination_path="${PRIMARY_INVENTORY_PATH}$(basename "${artifact}")"
  if ! upload_artifact_with_retries "${artifact}" "${destination_path}"; then
    echo "WARNING: Continuing pipeline despite cleanup artifact upload failure."
  fi
done

#!/usr/bin/env bash
set -e

export HDF5_PLUGIN_PATH=/opt/conda/lib/python3.10/site-packages/braingeneers/data/mxw_h5_plugin/Linux/

while true; do
  export FILE=$(python get_task.py)
  export BASE_DIR=$(dirname ${FILE})
  export BASE_FILE=$(basename ${FILE})
  export ROWMAJOR_FILE="${BASE_FILE%%.*}.rowmajor.h5"

  if [ "${FILE}" == "END" ]; then
    echo "Queue empty, exiting successfully."
    break
  fi

  echo "Checking if romajor file exists already: ${BASE_DIR}/${ROWMAJOR_FILE}"
  if ! aws --endpoint ${ENDPOINT} s3 ls ${BASE_DIR}/${ROWMAJOR_FILE}; then
    echo "Downloading file: ${FILE}"
    aws --endpoint ${ENDPOINT} s3 cp "${FILE}" "/tmp/"
    h5repack -v -l "/data_store/data0000/groups/routed/raw:CHUNK=1x30000" -i "/tmp/${BASE_FILE}" -o "/tmp/${ROWMAJOR_FILE}"
    echo "Uploading file: ${BASE_DIR}/${BASE_FILE%%.*}.rowmajor.h5"
    aws --endpoint ${ENDPOINT} s3 cp "/tmp/${BASE_FILE%%.*}.rowmajor.h5" "${BASE_DIR}/"
    # todo delete old file, currently not implemented for safety during testing phase
    # python update_metadata.py  # todo add after testing
    rm /tmp/${BASE_FILE}

  else
    echo "File already exists, exiting: ${ROWMAJOR_FILE}"
    break

  fi
done
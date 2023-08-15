#!/usr/bin/env bash
set -e
set -x
echo "DEBUG> v3"

# optional random delay to avoid thundering heard problem
if [[ "$1" == "--random-delay" ]]; then
  DELAY_SEC=$(( RANDOM % $2 ))
  echo "Sleeping $DELAY_SEC seconds"
  sleep $DELAY_SEC
fi

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

    # Run h5repack for V2 format or (||) V1 format (if V2 format attempt failed,
    # note the use of short circuit evaluation, h5repack will fail quickly if V2 format is not detected)
    echo "Running h5repack operation"
    (h5repack -v -l "/data_store/data0000/groups/routed/raw:CHUNK=1x30000" -i "/tmp/${BASE_FILE}" -o "/tmp/${ROWMAJOR_FILE}" || \
      h5repack -v -l "sig:CHUNK=1x30000" -i "/tmp/${BASE_FILE}" -o "/tmp/${ROWMAJOR_FILE}")

    echo "Uploading file: ${BASE_DIR}/${BASE_FILE%%.*}.rowmajor.h5"
    aws --endpoint ${ENDPOINT} s3 cp "/tmp/${BASE_FILE%%.*}.rowmajor.h5" "${BASE_DIR}/"

    # Clear local working space
    rm /tmp/${BASE_FILE}

    # todo enable metadata update and deletion after testing
    # echo "Updating metadata"
    # python update_metadata.py --uuid ${UUID} --file ${FILE} --rowmajor_file ${ROWMAJOR_FILE}
    # echo "Deleting file: ${BASE_DIR}/${BASE_FILE}"

  else
    echo "File already exists, exiting successfully: ${ROWMAJOR_FILE}"
    break

  fi
done
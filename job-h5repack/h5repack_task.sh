#!/usr/bin/env bash
set -e

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

  echo "===================="
  echo UUID: ${UUID}
  echo FILE: ${FILE}
  echo BASE_DIR: ${BASE_DIR}
  echo BASE_FILE: ${BASE_FILE}
  echo ROWMAJOR_FILE: ${ROWMAJOR_FILE}
  echo "===================="

  if [ "${FILE}" == "END" ]; then
    echo "Queue empty, exiting successfully."
    break
  fi

  echo "Checking if romajor file exists already: ${BASE_DIR}/${ROWMAJOR_FILE}"
  if aws --endpoint ${ENDPOINT} s3 ls ${BASE_DIR}/${ROWMAJOR_FILE}; then
    echo "File already exists, continuing successfully: ${ROWMAJOR_FILE}"
  else
    echo "Downloading file: ${FILE}"
    aws --endpoint ${ENDPOINT} s3 cp "${FILE}" "/tmp/"

    # Run h5repack for V2 format or (||) V1 format (if V2 format attempt failed)
    # note the use of short circuit evaluation, h5repack will fail quickly if V2 format is not detected)
    echo "Running h5repack operation"
    (h5repack -v -l "/data_store/data0000/groups/routed/raw:CHUNK=1x30000" -i "/tmp/${BASE_FILE}" -o "/tmp/${ROWMAJOR_FILE}" || \
      h5repack -v -l "sig:CHUNK=1x30000" -i "/tmp/${BASE_FILE}" -o "/tmp/${ROWMAJOR_FILE}")

    echo "Uploading file: ${BASE_DIR}/${BASE_FILE%%.*}.rowmajor.h5"
    aws --endpoint ${ENDPOINT} s3 cp "/tmp/${BASE_FILE%%.*}.rowmajor.h5" "${BASE_DIR}/"

    # Clear local working space
    rm /tmp/${BASE_FILE}

    # Delete the original file
    # echo "Deleting file: ${BASE_DIR}/${BASE_FILE}"
    # todo

  fi

  # We update metadata in any case because the update metadata will skip the update if the metadata is already set
  # if for some reason the file was created but the metadata didn't get updated this will update it still.
  echo "Verifying or updating metadata with parameters: --uuid ${UUID} --file original/data/${FILE} --rowmajor-file original/data/${ROWMAJOR_FILE}"
  python update_metadata.py --uuid "${UUID}" --file "original/data/${BASE_FILE}" --rowmajor-file "original/data/${ROWMAJOR_FILE}"

done
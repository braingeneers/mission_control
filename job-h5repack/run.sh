#!/usr/bin/env bash

echo "Running job: $JOB_NAME"
echo "UUID: $UUID"

if [ "$JOB_NAME" == "h5-repack-init" ]; then
  # We are running as an init instance
  echo "Running as init instance"
  python -u init.py
elif [ "$JOB_NAME" == "h5-repack-workers" ]; then
  # We are running as a worker instance
  echo "Running as worker instance"
  sleep $(( $(shuf -i 1-120 -n 1) ))  # Sleep for a random amount of time to avoid thundering herd
  python -u h5repack_task.py
elif [ "$JOB_NAME" == "h5-repack-finalize" ]; then
  # We are running the finalization step
  echo "Running finalization step"
  python -u update_metadata.py
else
  echo "Unrecognized JOB_NAME: $JOB_NAME"
fi

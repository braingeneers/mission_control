#!/usr/bin/env bash

# Determine if we are running as init (a $UUID variable exists) or as workers (no UUID variable exists)

if [ -z "$UUID" ]; then
  # We are running as a worker instance
  echo "Running as worker instance"
  python -u h5repack_task.py
else
  # We are running as init
  echo "Running as init instance"
  python -u init.py
fi

# todo we need a third job that runs update_metadata.py

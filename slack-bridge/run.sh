#!/bin/bash

# Wait until the credentials file in /secrets/credentials is available
echo "Checking if credentials file exists"
while [ ! -f "/secrets/prp-s3-credentials/credentials" ]; do
    echo "Waiting for credentials file to be downloaded by secret-fetcher..."
    sleep 5
done

mkdir -p /home/jovyan/.aws
cp /secrets/prp-s3-credentials/credentials /home/jovyan/.aws/credentials
python /app/slack_bridge.py

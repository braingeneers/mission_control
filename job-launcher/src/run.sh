#!/bin/bash
set -e

# sanity check
ping -c 1 mqtt.braingeneers.gi.ucsc.edu

mkdir -p ~/.aws
cp /secrets/prp-s3-credentials/credentials ~/.aws/credentials
mkdir -p ~/.kube
cp /secrets/kube-config/config ~/.kube/config

echo "Starting application"
python -u /app/k8s_job_creator.py

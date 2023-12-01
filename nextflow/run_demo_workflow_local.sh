#!/usr/bin/env bash

# This script is used to deploy a workflow on kubernetes, it defaults to workflow demo_workflow.nf if none
# is specified on the command line. Usage example:
#
#   ./run_demo_workflow_local.sh workflows/demo/main.nf
#

WORKFLOW_NAME=${1:-demo/main.nf}

docker run --rm -t \
  --volume $(pwd)/workflows/:/workflows/ \
  --volume ~/.aws/:/root/.aws/ \
  --volume ~/.kube/:/root/.kube/ \
  --volume ~/.local/bin/:/usr/local/sbin/ \
  nextflow/nextflow:latest \
  nextflow run /workflows/${WORKFLOW_NAME} \
  --xyz 1970-01-01-e-demo

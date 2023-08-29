#!/usr/bin/env bash

# This script is used to deploy a workflow on kubernetes, it defaults to workflow demo_workflow.nf if none
# is specified on the command line. Usage example:
#
#   ./run_demo_workflow_local.sh demo_workflow.nf
#

WORKFLOW_NAME=${1:-demo_workflow.nf}

docker run --rm -it \
  --volume $(pwd)/workflows/:/workflows/ \
  --volume ~/.aws/credentials:/root/.aws/credentials \
  --volume ~/.aws/config:/root/.aws/config \
  --volume ~/.kube/config:/root/.kube/config \
  nextflow/nextflow:latest \
  nextflow run /workflows/${WORKFLOW_NAME} \
  --xyz 1970-01-01-e-demo

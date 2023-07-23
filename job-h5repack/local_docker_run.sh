#!/bin/bash

# This is only meant to simplify debugging
# Starts the docker container for debugging, includes a UUID environment variable as
# would be passed in when run as a job and includes the necessary volume mounts.

docker run --rm -it \
  -v /home/${USER}/.aws:/home/jovyan/.aws \
  -v /home/${USER}/.kube:/home/jovyan/.kube:ro \
  -v .:/mission_control/ \
  --env "UUID=2023-04-17-e-causal_v1" \
  braingeneers/braingeneers:latest \
  bash

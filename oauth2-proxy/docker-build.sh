#!/usr/bin/env bash
set -e

docker build -f Dockerfile -t braingeneers/oauth2-proxy:latest .
docker push braingeneers/oauth2-proxy:latest

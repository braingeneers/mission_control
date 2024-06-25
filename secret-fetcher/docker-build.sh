#!/usr/bin/env bash
set -e

docker build -f Dockerfile -t braingeneers/secret-fetcher:latest .
docker push braingeneers/secret-fetcher:latest

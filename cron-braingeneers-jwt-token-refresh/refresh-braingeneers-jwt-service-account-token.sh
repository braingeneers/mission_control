#!/usr/bin/env bash
# This script will update a service-account token in our kubernetes namespace daily.
#

set -euo pipefail

while true; do
  # Get a new JWT service account token (this will only work without authentication from within the braingeneers network)
  curl -fsS https://service-accounts.braingeneers.gi.ucsc.edu/generate_token > /config.json

  # Update the JWT token in the kubernetes secrets in braingeneers namespace
  kubectl -n braingeneers delete secret braingeneers-jwt-service-account-token --ignore-not-found
  kubectl -n braingeneers create secret generic braingeneers-jwt-service-account-token --from-file=config.json

  # Sleep for 1 day
  sleep 86400
done

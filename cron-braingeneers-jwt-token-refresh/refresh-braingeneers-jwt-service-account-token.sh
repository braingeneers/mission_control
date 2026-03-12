#!/usr/bin/env bash
# This script will update a service-account token in our kubernetes namespace daily.
#

set -euo pipefail

SERVICE_ACCOUNTS_URL="${SERVICE_ACCOUNTS_URL:-http://service-accounts/generate_token}"

while true; do
  # Use the internal Docker DNS name so this stays on braingeneers-net and does not hit
  # the authenticated public edge proxy.
  http_status="$(curl -sS -o /config.json -w '%{http_code}' "${SERVICE_ACCOUNTS_URL}")"
  if [[ "${http_status}" != "200" ]]; then
    echo "Unexpected HTTP status from ${SERVICE_ACCOUNTS_URL}: ${http_status}" >&2
    cat /config.json >&2
    exit 1
  fi

  # Update the JWT token in the kubernetes secrets in braingeneers namespace
  kubectl -n braingeneers delete secret braingeneers-jwt-service-account-token --ignore-not-found
  kubectl -n braingeneers create secret generic braingeneers-jwt-service-account-token --from-file=config.json

  # Sleep for 1 day
  echo "Sleeping for 1 day."
  sleep 86400
done

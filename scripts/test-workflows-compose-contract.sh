#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="${repo_dir}/docker-compose.yaml"
compose_json="$(docker compose -f "${compose_file}" config --format json)"

fail() {
    echo "$1" >&2
    exit 1
}

service_value() {
    local service="$1"
    local expression="$2"
    jq -r --arg service "${service}" ".services[\$service]${expression}" \
        <<<"${compose_json}"
}

assert_equal() {
    local actual="$1"
    local expected="$2"
    local message="$3"
    if [[ "${actual}" != "${expected}" ]]; then
        fail "${message}: expected ${expected}, got ${actual}"
    fi
}

backend_image="$(service_value workflows-backend '.image')"
frontend_image="$(service_value workflows '.image')"
backend_tag="${backend_image##*:}"
frontend_tag="${frontend_image##*:}"

if [[ ! "${backend_image}" =~ ^braingeneers/workflows-backend:[0-9]{8}-[0-9a-f]{12}$ ]]; then
    fail "workflows-backend must use an immutable date/SHA image, got ${backend_image}"
fi
if [[ ! "${frontend_image}" =~ ^braingeneers/workflows-frontend:[0-9]{8}-[0-9a-f]{12}$ ]]; then
    fail "workflows must use an immutable date/SHA image, got ${frontend_image}"
fi
assert_equal "${backend_tag}" "${frontend_tag}" "Workflows backend/frontend image tags"
assert_equal \
    "$(service_value workflows-backend '.environment.COLLECTED_RUNS_ROOT')" \
    "/local/workflows/runs" \
    "Collected run root"
assert_equal \
    "$(service_value workflows-backend '.volumes[] | select(.target == "/local") | .source')" \
    "local" \
    "Workflows local volume source"
assert_equal \
    "$(service_value workflows-backend '.volumes | map(select(.source == "replicated")) | length')" \
    "0" \
    "Workflows replicated volume mount count"
assert_equal \
    "$(service_value workflows-backend '.depends_on["mqtt"] // empty')" \
    "" \
    "Workflows optional MQTT startup dependency"
assert_equal \
    "$(service_value workflows-backend '.depends_on["notification-service"] // empty')" \
    "" \
    "Workflows optional notification startup dependency"
assert_equal \
    "$(service_value workflows-backend '.environment.NOTIFICATION_SERVICE_URL')" \
    "http://notification-service:8000" \
    "Workflows notification service URL"

echo "Workflows Compose contracts are valid."

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

assert_immutable_uploader_image() {
    local service="$1"
    local image
    image="$(service_value "${service}" ".image")"
    if [[ ! "${image}" =~ ^braingeneers/braingeneers-data-uploader:[0-9]{8}-[0-9a-f]{12}$ ]]; then
        fail "${service} must use an immutable date/SHA uploader image, got ${image}"
    fi
}

assert_equal \
    "$(service_value uploader '.environment.PROD')" \
    "true" \
    "Production uploader bucket mode"
assert_equal \
    "$(service_value uploader '.environment.VIRTUAL_HOST')" \
    "uploader.braingeneers.gi.ucsc.edu" \
    "Production uploader hostname"
assert_equal \
    "$(service_value uploader '.environment.LETSENCRYPT_HOST')" \
    "uploader.braingeneers.gi.ucsc.edu" \
    "Production uploader TLS hostname"
assert_equal \
    "$(service_value uploader '.container_name')" \
    "null" \
    "Production uploader explicit container name"
assert_immutable_uploader_image uploader

assert_equal "$(service_value uploader-dev '')" \
    "null" "Retired uploader-dev service must be absent"
assert_equal "$(service_value uploader '.environment.METADATA_TEMPLATE_DIR')" \
    "/replicated/uploader-dev/metadata-templates" "Presets survive promotion to uploader"
assert_equal "$(service_value uploader '.environment.WHATS_NEW_DIR')" \
    "/replicated/uploader-dev/whats-new" "Announcement state survives promotion to uploader"
assert_equal "$(service_value uploader '.volumes[] | select(.target == "/replicated") | .source')" \
    "replicated" "Uploader presets and announcement state are backed up"
assert_equal "$(service_value uploader '.environment.NRP_LLM_API_KEY_FILE')" \
    "/secrets/nrp-llm-api-key" "Uploader retains AI prefill credentials"

assert_equal "$(service_value uploader '.environment.WORKFLOWS_API_URL')" \
    "http://workflows-backend:8000" "Uploader internal Recipe API"
assert_equal "$(service_value uploader '.environment.WORKFLOWS_PUBLIC_URL')" \
    "https://workflows.braingeneers.gi.ucsc.edu" "Uploader public Recipe links"
assert_equal "$(service_value uploader '.environment.MQTT_BROKER_HOST')" \
    "null" "Uploader no longer publishes MQTT"
assert_equal "$(service_value uploader '.depends_on["workflows-backend"] // empty')" \
    "" "Recipe processing must not be a startup dependency"

echo "Uploader Compose contracts are valid."

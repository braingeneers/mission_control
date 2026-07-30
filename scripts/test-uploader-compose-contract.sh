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
    "$(service_value uploader '.container_name')" \
    "null" \
    "Production uploader explicit container name"
assert_immutable_uploader_image uploader

assert_equal \
    "$(service_value uploader-dev '.environment.PROD')" \
    "false" \
    "Acceptance uploader bucket mode"
assert_equal \
    "$(service_value uploader-dev '.environment.VIRTUAL_HOST')" \
    "uploader-dev.braingeneers.gi.ucsc.edu" \
    "Acceptance uploader hostname"
assert_equal \
    "$(service_value uploader-dev '.container_name')" \
    "uploader-dev" \
    "Acceptance uploader explicit container name"
assert_immutable_uploader_image uploader-dev

echo "Uploader Compose contracts are valid."

#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_json="$(docker compose -f "${repo_dir}/docker-compose.yaml" config --format json)"

fail() {
    echo "$1" >&2
    exit 1
}

service_value() {
    local expression="$1"
    jq -r ".services[\"data-explorer\"]${expression}" <<<"${compose_json}"
}

image="$(service_value '.image')"
[[ "${image}" =~ ^braingeneers/data-explorer:[0-9]{8}-[0-9a-f]{12}$ ]] \
    || fail "data-explorer must use an immutable date/SHA image, got ${image}"
[[ "$(service_value '.volumes[] | select(.target == "/local") | .source')" == "local" ]] \
    || fail "data-explorer must persist its disposable indexes on the local volume"
[[ "$(service_value '.environment.DATA_EXPLORER_LIFECYCLE_INDEX_PATH')" == "/local/data-explorer/lifecycle-index.sqlite3" ]] \
    || fail "data-explorer lifecycle index path must use the local volume"
[[ "$(service_value '.environment.DATA_EXPLORER_LIFECYCLE_MANIFEST_URI')" == "s3://braingeneers/services/data-lifecycle/latest-backup-state.json" ]] \
    || fail "data-explorer must use the completed backup-state pointer"
[[ "$(service_value '.environment.DATA_EXPLORER_LIFECYCLE_REPORT_POINTER_URI')" == "s3://braingeneers/services/data-lifecycle/latest-cleanup-report.json" ]] \
    || fail "data-explorer must validate report deep links against the completed report pointer"
[[ "$(service_value '.depends_on["data-lifecycle"] // empty')" == "" ]] \
    || fail "data-explorer must not depend on the legacy lifecycle website"

legacy_image="$(jq -r '.services["data-lifecycle"].image' <<<"${compose_json}")"
[[ "${legacy_image}" =~ ^braingeneers/data-lifecycle-deletion-web:[0-9]{8}-[0-9a-f]{12}$ ]] \
    || fail "legacy lifecycle cutover service must use an immutable date/SHA image, got ${legacy_image}"

echo "Data Explorer Compose contracts are valid."

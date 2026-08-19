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
    local expression="$1"
    jq -r ".services[\"replicated-volume-backup\"]${expression}" \
        <<<"${compose_json}"
}

image="$(service_value '.image')"
if [[ ! "${image}" =~ ^braingeneers/replicated-volume-backup:[0-9]{8}-[0-9a-f]{12}$ ]]; then
    fail "replicated-volume-backup must use an immutable date/SHA image, got ${image}"
fi

[[ "$(service_value '.container_name')" == 'replicated-volume-backup' ]] || \
    fail 'replicated-volume-backup container name must match its service name'
[[ "$(service_value '.depends_on["secret-fetcher"].condition')" == 'service_healthy' ]] || \
    fail 'replicated-volume-backup must wait for healthy secret-fetcher'
[[ "$(service_value '.volumes[] | select(.target == "/replicated") | .source')" == 'replicated' ]] || \
    fail 'replicated-volume-backup must mount the shared replicated volume'
[[ "$(service_value '.volumes[] | select(.target == "/replicated") | .read_only')" == 'true' ]] || \
    fail 'replicated-volume-backup replicated mount must be read-only'
[[ "$(service_value '.volumes[] | select(.target == "/local") | .source')" == 'local' ]] || \
    fail 'replicated-volume-backup must mount the shared local volume'
[[ "$(service_value '.volumes[] | select(.target == "/secrets") | .source')" == 'secrets' ]] || \
    fail 'replicated-volume-backup must mount fetched secrets'
[[ "$(service_value ' | (.ports // []) | length')" == '0' ]] || \
    fail 'replicated-volume-backup must not publish ports'
[[ "$(service_value ' | (.expose // []) | length')" == '0' ]] || \
    fail 'replicated-volume-backup must not expose web ports'
[[ "$(service_value ' | (.environment.VIRTUAL_HOST // "")')" == '' ]] || \
    fail 'replicated-volume-backup must not use web proxy routing'

if jq -e '.services["data-lifecycle-backup"]' <<<"${compose_json}" >/dev/null; then
    fail 'legacy data-lifecycle-backup service must be removed'
fi

echo 'replicated-volume-backup Compose contracts are valid.'

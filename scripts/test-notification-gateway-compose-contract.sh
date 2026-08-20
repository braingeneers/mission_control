#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_json="$(docker compose -f "${repo_dir}/docker-compose.yaml" config --format json)"
proxy_file="${repo_dir}/service-proxy/notifications.braingeneers.gi.ucsc.edu"

fail() {
    echo "$1" >&2
    exit 1
}

service_value() {
    local service="$1"
    local expression="$2"
    jq -r --arg service "${service}" ".services[\$service]${expression}" <<<"${compose_json}"
}

gateway_image="$(service_value notification-gateway '.image')"
[[ "${gateway_image}" =~ ^braingeneers/notification-gateway:[0-9]+\.[0-9]+\.[0-9]+$ ]] \
    || fail "notification-gateway must use an immutable release image, got ${gateway_image}"
[[ "$(service_value notification-gateway '.build // empty')" == "" ]] \
    || fail "notification-gateway must not build on the production server"
[[ "$(service_value notification-gateway '.ports | length')" == "0" ]] \
    || fail "notification-gateway must not publish its application port directly"
[[ "$(service_value notification-gateway '.volumes[] | select(.target == "/secrets") | .source')" == "secrets" ]] \
    || fail "notification-gateway must mount the fetched secrets volume"
[[ "$(service_value notification-gateway '.depends_on["sql-db"].condition')" == "service_healthy" ]] \
    || fail "notification-gateway must wait for sql-db health"
[[ "$(service_value notification-gateway '.environment.MQTT_ENABLED')" == "false" ]] \
    || fail "notification-gateway MQTT must stay disabled until producer topic ACLs are enforced"
[[ "$(service_value notification-gateway '.depends_on["mqtt"] // empty')" == "" ]] \
    || fail "notification-gateway must not depend on MQTT while its MQTT adapter is disabled"
[[ "$(service_value workflows-backend '.environment.NOTIFICATION_DISPATCH_ENABLED // empty')" == "" ]] \
    || fail "Workflows notification dispatch must remain disabled until explicitly adopted"
[[ "$(service_value workflows-backend '.depends_on["notification-gateway"] // empty')" == "" ]] \
    || fail "Workflows must start independently of the optional notification gateway"

grep -Eq '^[[:space:]]*auth_request[[:space:]]+off;' "${proxy_file}" \
    || fail "notification gateway proxy must bypass browser authentication"
grep -Eq '^[[:space:]]*proxy_set_header[[:space:]]+Authorization[[:space:]]+\$http_authorization;' "${proxy_file}" \
    || fail "notification gateway proxy must preserve bearer authentication"
grep -Eq '^[[:space:]]*client_max_body_size[[:space:]]+64k;' "${proxy_file}" \
    || fail "notification gateway proxy must enforce the bounded request size"
for header in X-User X-Email X-Groups X-Name X-Given-Name X-Family-Name X-Preferred-Username X-Subject; do
    grep -Eq "^[[:space:]]*proxy_set_header[[:space:]]+${header}[[:space:]]+\"\";" "${proxy_file}" \
        || fail "notification gateway proxy must strip ${header}"
done

echo "Notification gateway Compose and proxy contracts are valid."

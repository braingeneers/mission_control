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

api_image="$(service_value notification-service '.image')"
relay_image="$(service_value notification-mail-relay '.image')"
[[ "${api_image}" =~ ^braingeneers/notification-service:[0-9]+\.[0-9]+\.[0-9]+$ ]] \
    || fail "notification-service must use an immutable release image, got ${api_image}"
[[ "${relay_image}" =~ ^braingeneers/notification-mail-relay:[0-9]+\.[0-9]+\.[0-9]+$ ]] \
    || fail "notification-mail-relay must use an immutable release image, got ${relay_image}"

for service in notification-service notification-mail-relay; do
    [[ "$(service_value "${service}" '.build // empty')" == "" ]] \
        || fail "${service} must not build on the production server"
    [[ "$(service_value "${service}" '.ports | length')" == "0" ]] \
        || fail "${service} must not publish ports directly"
    [[ "$(service_value "${service}" '.volumes[] | select(.target == "/secrets") | .source')" == "secrets" ]] \
        || fail "${service} must mount the fetched secrets volume"
done

[[ "$(service_value notification-service '.depends_on["sql-db"] // empty')" == "" ]] \
    || fail "notification-service must not depend on sql-db"
[[ "$(service_value notification-service '.depends_on["mqtt"] // empty')" == "" ]] \
    || fail "notification-service must not depend on MQTT"
[[ "$(service_value notification-service '.depends_on["notification-mail-relay"].condition')" == "service_started" ]] \
    || fail "notification-service must start its mail component without coupling readiness"
[[ "$(service_value notification-service '.environment.SLACK_BOT_TOKEN_FILE')" \
    == "/secrets/slack-token-braingeneersbot-gi/slack-token-braingeneersbot-gi" ]] \
    || fail "notification-service must read the operator-owned braingeneersbot token path"
[[ "$(service_value notification-mail-relay '.networks | keys | sort | join(",")')" == "notification-mail-net" ]] \
    || fail "notification-mail-relay must be isolated from shared service networks"
[[ "$(service_value notification-mail-relay '.volumes[] | select(.target == "/local") | .source')" == "local" ]] \
    || fail "notification-mail-relay must persist its Postfix queue under local"
[[ "$(service_value notification-mail-relay '.environment.POSTFIX_QUEUE_DIR')" == "/local/notification-service/postfix" ]] \
    || fail "notification-mail-relay must store its Postfix queue in the shared local volume"
[[ "$(service_value workflows-backend '.depends_on["notification-service"] // empty')" == "" ]] \
    || fail "Workflows must not depend on notification-service before adoption"
[[ "$(service_value workflows-backend '.depends_on["mqtt"] // empty')" == "" ]] \
    || fail "Workflows optional MQTT ingress must not be a startup dependency"
[[ "$(service_value workflows-backend '.environment.NOTIFICATION_DISPATCH_ENABLED // empty')" == "" ]] \
    || fail "Workflows must not carry speculative notification configuration"

grep -Eq '^[[:space:]]*include[[:space:]]+/etc/nginx/vhost.d/default;' "${proxy_file}" \
    || fail "notification proxy must include standard authenticated proxy behavior"
if grep -Eq '^[[:space:]]*auth_request[[:space:]]+off;' "${proxy_file}"; then
    fail "notification proxy must not bypass standard authentication"
fi
if grep -Eq '^[[:space:]]*proxy_set_header[[:space:]]+Authorization' "${proxy_file}"; then
    fail "notification proxy must inherit downstream Authorization stripping"
fi
grep -Eq '^[[:space:]]*client_max_body_size[[:space:]]+12m;' "${proxy_file}" \
    || fail "notification proxy must enforce the 12 MiB request limit"

echo "Notification service Compose and proxy contracts are valid."

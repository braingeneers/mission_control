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
[[ "$(service_value '.environment.DATA_EXPLORER_DATABASE_SCHEMA')" == "data_explorer" ]] \
    || fail "data-explorer must own the data_explorer PostgreSQL schema"
[[ "$(service_value '.environment.DATA_EXPLORER_AUTO_CREATE_TABLES')" == "false" ]] \
    || fail "hosted data-explorer must use Alembic rather than SQLAlchemy table auto-create"
[[ "$(service_value '.environment.DATA_EXPLORER_DATABASE_URL')" == *"@sql-db:5432/services"* ]] \
    || fail "data-explorer publication state must use the shared sql-db service"
[[ "$(service_value '.command | join(" ")')" == *"alembic upgrade head && uvicorn"* ]] \
    || fail "data-explorer must apply Alembic migrations before application startup"
[[ "$(service_value '.healthcheck.test | join(" ")')" == *"/api/config"* ]] \
    || fail "data-explorer process health must not depend on live S3 availability"
[[ "$(service_value '.environment.DATA_EXPLORER_DANDI_INSTANCE')" == "sandbox" ]] \
    || fail "data-explorer publication must default to DANDI Sandbox"
[[ "$(service_value '.environment.DATA_EXPLORER_DANDI_MANIFEST_PREFIX')" == "s3://braingeneers/services/data-explorer/dandi/sandbox/" ]] \
    || fail "data-explorer publication manifests must use the approved immutable S3 namespace"
[[ "$(service_value '.environment.DATA_EXPLORER_DANDI_WORKFLOW_ID')" == "dandi-publication" ]] \
    || fail "data-explorer must launch the cataloged DANDI publication workflow"
[[ "$(service_value '.environment.DATA_EXPLORER_MQTT_TOPIC')" == "workflows/launch" ]] \
    || fail "data-explorer must use the generic Workflows MQTT launch ingress"
[[ "$(service_value '.environment.DATA_EXPLORER_DANDI_DISPATCH_GRACE_SECONDS')" == "300" ]] \
    || fail "data-explorer must reconcile ambiguous MQTT acknowledgement before retry"
[[ "$(service_value '.depends_on["sql-db"].condition')" == "service_healthy" ]] \
    || fail "data-explorer must wait for shared sql-db health"
[[ "$(service_value '.depends_on["mqtt"] // empty')" == "" ]] \
    || fail "data-explorer must remain startable while the optional MQTT integration is unavailable"
[[ "$(service_value '.depends_on["workflows-backend"] // empty')" == "" ]] \
    || fail "data-explorer must not use Workflows status integration as a startup dependency"
[[ "$(service_value '.depends_on["data-lifecycle"] // empty')" == "" ]] \
    || fail "data-explorer must not depend on the retired lifecycle website"

if jq -e '.services["data-lifecycle"]' <<<"${compose_json}" >/dev/null; then
    fail "retired data-lifecycle web service must be absent"
fi

echo "Data Explorer Compose contracts are valid."

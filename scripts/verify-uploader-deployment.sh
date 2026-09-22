#!/usr/bin/env bash
set -euo pipefail

service="${1:-}"
case "${service}" in
    uploader|uploader-dev) ;;
    *)
        echo "Usage: $0 uploader|uploader-dev" >&2
        exit 2
        ;;
esac

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="${repo_dir}/docker-compose.yaml"
compose_json="$(docker compose -f "${compose_file}" config --format json)"

fail() {
    echo "$1" >&2
    exit 1
}

expected_image="$(
    jq -r --arg service "${service}" '.services[$service].image' <<<"${compose_json}"
)"
expected_prod="$(
    jq -r --arg service "${service}" '.services[$service].environment.PROD' \
        <<<"${compose_json}"
)"
expected_version="${expected_image##*:}"
container_id="$(docker compose -f "${compose_file}" ps -q "${service}")"

[[ -n "${container_id}" ]] || fail "${service} is not running."

running_config_image="$(docker inspect --format '{{.Config.Image}}' "${container_id}")"
asserted_image_id="$(docker image inspect --format '{{.Id}}' "${expected_image}" 2>/dev/null)" \
    || fail "${expected_image} is not pulled locally."
running_image_id="$(docker inspect --format '{{.Image}}' "${container_id}")"
running_version="$(
    docker compose -f "${compose_file}" exec -T "${service}" printenv APP_VERSION
)"
running_prod="$(
    docker compose -f "${compose_file}" exec -T "${service}" printenv PROD
)"

[[ "${running_config_image}" == "${expected_image}" ]] \
    || fail "${service} container uses ${running_config_image}; Compose expects ${expected_image}."
[[ "${running_image_id}" == "${asserted_image_id}" ]] \
    || fail "${service} is running an older image ID; force-recreate the service."
[[ "${running_version}" == "${expected_version}" ]] \
    || fail "${service} reports APP_VERSION=${running_version}; expected ${expected_version}."
[[ "${running_prod}" == "${expected_prod}" ]] \
    || fail "${service} reports PROD=${running_prod}; expected ${expected_prod}."

# Check the live edge contract too: a current app container can still sit behind
# stale bind-mounted proxy configuration that redirects API requests to login.
api_url="https://${service}.braingeneers.gi.ucsc.edu/api/version"
api_response="$(curl -q --silent --show-error --connect-timeout 5 --max-time 15 \
    --proto '=https' --max-redirs 0 --max-filesize 16384 --include --suppress-connect-headers \
    --write-out $'\n%{http_code}' "${api_url}")" \
    || fail "${service} public API authentication check could not reach ${api_url}; check HTTPS connectivity and retry."
api_status="${api_response##*$'\n'}"
api_body="${api_response%$'\n'*}"

auth_failure() {
    fail "${service} public API authentication check failed: $1. Pull the updated proxy configuration, recreate service-proxy, and rerun this verifier."
}

[[ "${api_status}" == "401" ]] \
    || auth_failure "expected HTTP 401 at ${api_url}, received ${api_status}"
# Keep this small anonymous response in memory. Skip informational header blocks
# such as HTTP 103 so only the final response determines the authentication result.
while true; do
    [[ "${api_body}" == HTTP/* && "${api_body}" == *$'\r\n\r\n'* ]] \
        || auth_failure "incomplete response headers"
    api_headers="${api_body%%$'\r\n\r\n'*}"
    api_body="${api_body#*$'\r\n\r\n'}"
    status_line="${api_headers%%$'\r\n'*}"
    [[ "${status_line}" =~ ^HTTP/[^[:space:]]+[[:space:]]+1[0-9][0-9]([[:space:]]|$) ]] || break
done
# Header names are case-insensitive, and curl preserves CRLF response endings.
awk 'tolower($0) ~ /^location[[:space:]]*:/ { found=1 } END { exit !found }' \
    <<<"${api_headers}" && auth_failure "anonymous API response contains a login redirect"
awk 'tolower($0) ~ /^content-type:[[:space:]]*application\/json([;[:space:]]|$)/ { found=1 } END { exit !found }' \
    <<<"${api_headers}" || auth_failure "anonymous API response is not JSON"
awk 'tolower($0) ~ /^x-request-id:[[:space:]]*[^[:space:]]/ { found=1 } END { exit !found }' \
    <<<"${api_headers}" || auth_failure "anonymous API response has no request ID"
jq -e '.detail.code == "authentication_required"' <<<"${api_body}" >/dev/null 2>&1 \
    || auth_failure "anonymous API response does not contain the authentication-required error"

echo "${service} deployment matches ${expected_image} with PROD=${expected_prod}; public API authentication is correct."

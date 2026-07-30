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

echo "${service} deployment matches ${expected_image} with PROD=${expected_prod}."

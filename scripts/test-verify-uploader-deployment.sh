#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
verifier="${repo_dir}/scripts/verify-uploader-deployment.sh"
temp_dir="$(mktemp -d)"

cleanup() {
    trash "${temp_dir}"
}
trap cleanup EXIT

mkdir -p "${temp_dir}/bin"
cat >"${temp_dir}/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

expected_image="braingeneers/braingeneers-data-uploader:20260730-abcdef123456"
expected_version="${expected_image##*:}"

if [[ "$1" == "compose" ]]; then
    case " $* " in
        *" config --format json "*)
            printf '%s\n' \
                '{"services":{"uploader":{"image":"'"${expected_image}"'","environment":{"PROD":"true"}},"uploader-dev":{"image":"'"${expected_image}"'","environment":{"PROD":"true"}}}}'
            ;;
        *" ps -q uploader "*|*" ps -q uploader-dev "*)
            printf '%s\n' "fake-container"
            ;;
        *" exec -T uploader printenv APP_VERSION "*|*" exec -T uploader-dev printenv APP_VERSION "*)
            printf '%s\n' "${FAKE_APP_VERSION:-${expected_version}}"
            ;;
        *" exec -T uploader printenv PROD "*)
            printf '%s\n' "${FAKE_PROD:-true}"
            ;;
        *" exec -T uploader-dev printenv PROD "*)
            printf '%s\n' "${FAKE_PROD:-true}"
            ;;
        *)
            echo "Unexpected fake docker compose command: $*" >&2
            exit 2
            ;;
    esac
elif [[ "$1 $2" == "inspect --format" ]]; then
    case "$3" in
        "{{.Config.Image}}")
            printf '%s\n' "${FAKE_CONFIG_IMAGE:-${expected_image}}"
            ;;
        "{{.Image}}")
            printf '%s\n' "${FAKE_RUNNING_IMAGE_ID:-sha256:current}"
            ;;
        *)
            echo "Unexpected fake docker inspect format: $3" >&2
            exit 2
            ;;
    esac
elif [[ "$1 $2 $3" == "image inspect --format" ]]; then
    printf '%s\n' "${FAKE_PULLED_IMAGE_ID:-sha256:current}"
else
    echo "Unexpected fake docker command: $*" >&2
    exit 2
fi
EOF
chmod +x "${temp_dir}/bin/docker"

cat >"${temp_dir}/bin/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
[[ "$1" == "-q" ]] || { echo "Verifier must ignore user curl configuration." >&2; exit 2; }
url=""
while (($#)); do
    case "$1" in
        --connect-timeout|--max-time|--max-redirs|--max-filesize|--proto|--write-out) shift 2 ;;
        -q|--silent|--show-error|--include|--suppress-connect-headers) shift ;;
        https://*) url="$1"; shift ;;
        *) echo "Unexpected or credential-bearing curl argument: $1" >&2; exit 2 ;;
    esac
done
[[ "${url}" == "https://${FAKE_SERVICE:-uploader-dev}.braingeneers.gi.ucsc.edu/api/version" ]] \
    || { echo "Verifier used the wrong service endpoint." >&2; exit 2; }
[[ "${FAKE_CURL_FAILURE:-false}" == "false" ]] || exit 7
if [[ "${FAKE_API_INTERIM:-false}" == "true" ]]; then
    printf 'HTTP/2 103\r\nLink: </style.css>; rel=preload\r\n\r\n'
fi
printf 'HTTP/2 %s\r\n' "${FAKE_API_STATUS:-401}"
printf 'content-type: %s\r\n' "${FAKE_API_CONTENT_TYPE:-application/json; charset=utf-8}"
if [[ "${FAKE_MISSING_REQUEST_ID:-false}" == "false" ]]; then
    printf 'x-request-id: %s\r\n' "${FAKE_API_REQUEST_ID-0123456789abcdef0123456789abcdef}"
fi
if [[ "${FAKE_API_LOCATION:-false}" == "true" ]]; then
    printf 'Location: https://auth.example.test/oauth2/start\r\n'
fi
if [[ "${FAKE_INCOMPLETE_HEADERS:-false}" == "false" ]]; then
    printf '\r\n'
fi
if [[ -v FAKE_API_BODY ]]; then
    printf '%s' "${FAKE_API_BODY}"
else
    printf '%s' '{"detail":{"code":"authentication_required","message":"Sign in again."}}'
fi
printf '\n%s' "${FAKE_API_STATUS:-401}"
EOF
chmod +x "${temp_dir}/bin/curl"

fake_path="${temp_dir}/bin:${PATH}"

PATH="${fake_path}" FAKE_SERVICE=uploader "${verifier}" uploader >/dev/null
PATH="${fake_path}" "${verifier}" uploader-dev >/dev/null
PATH="${fake_path}" FAKE_API_INTERIM=true "${verifier}" uploader-dev >/dev/null
PATH="${fake_path}" FAKE_API_CONTENT_TYPE='Application/JSON' "${verifier}" uploader-dev >/dev/null

if PATH="${fake_path}" FAKE_RUNNING_IMAGE_ID="sha256:stale" \
    "${verifier}" uploader-dev >/dev/null 2>&1; then
    echo "Verifier accepted a stale running image ID." >&2
    exit 1
fi

if PATH="${fake_path}" FAKE_APP_VERSION="older-version" \
    "${verifier}" uploader-dev >/dev/null 2>&1; then
    echo "Verifier accepted a mismatched APP_VERSION." >&2
    exit 1
fi

expect_api_failure() {
    local expected_message="$1"
    shift
    local output
    if output="$(env PATH="${fake_path}" "$@" "${verifier}" uploader-dev 2>&1)"; then
        echo "Verifier accepted an invalid public API response: $*" >&2
        exit 1
    fi
    [[ "${output}" == *"${expected_message}"* ]] || {
        echo "Verifier failure did not explain the public API problem: ${output}" >&2
        exit 1
    }
}

expect_api_failure "expected HTTP 401" FAKE_API_STATUS=302 FAKE_API_LOCATION=true
expect_api_failure "expected HTTP 401" FAKE_API_STATUS=200
expect_api_failure "contains a login redirect" FAKE_API_LOCATION=true
expect_api_failure "is not JSON" FAKE_API_CONTENT_TYPE=text/html
expect_api_failure "has no request ID" FAKE_MISSING_REQUEST_ID=true
expect_api_failure "has no request ID" FAKE_API_REQUEST_ID=
expect_api_failure "incomplete response headers" FAKE_INCOMPLETE_HEADERS=true
expect_api_failure "authentication-required error" FAKE_API_BODY='<html>Sign in</html>'
expect_api_failure "authentication-required error" FAKE_API_BODY='{"detail":{"code":"other_error"}}'
expect_api_failure "could not reach" FAKE_CURL_FAILURE=true

echo "Uploader deployment verifier tests passed."

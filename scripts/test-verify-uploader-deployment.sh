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

fake_path="${temp_dir}/bin:${PATH}"

PATH="${fake_path}" "${verifier}" uploader >/dev/null
PATH="${fake_path}" "${verifier}" uploader-dev >/dev/null

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

echo "Uploader deployment verifier tests passed."

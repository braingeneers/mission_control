#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if ! docker compose -f "${repo_dir}/docker-compose.yaml" config --format json |
    jq -e '.services["lit-map"] |
        .entrypoint == null and .command == null and
        .environment.AWS_SHARED_CREDENTIALS_FILE == "/secrets/prp-s3-credentials/credentials" and
        .environment.NRP_LLM_API_KEY_FILE == "/secrets/nrp-llm-api-key/nrp_llm_api_key" and
        any(.volumes[]; .source == "secrets" and .target == "/secrets" and .read_only == true)' > /dev/null; then
    echo "Lit-Map must use its image startup command and read credentials from the mounted secrets volume." >&2
    exit 1
fi
echo "Lit-Map Compose startup and credential paths are valid."

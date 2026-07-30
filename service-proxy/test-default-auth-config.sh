#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
default_config="${script_dir}/default"

fail() {
    echo "$1" >&2
    exit 1
}

awk '
    /^location = \/_oauth2_proxy_auth \{/ {
        in_auth_location = 1
        found_auth_location = 1
        next
    }
    in_auth_location && /^[[:space:]]*proxy_pass_request_body[[:space:]]+off;/ {
        found_body_off = 1
    }
    in_auth_location && /^[[:space:]]*proxy_set_header[[:space:]]+Content-Length[[:space:]]+"";/ {
        found_empty_content_length = 1
    }
    in_auth_location && /^}/ {
        in_auth_location = 0
    }
    END {
        if (!found_auth_location) {
            print "Missing /_oauth2_proxy_auth location." > "/dev/stderr"
            exit 1
        }
        if (!found_body_off) {
            print "Auth subrequest must set proxy_pass_request_body off." > "/dev/stderr"
            exit 1
        }
        if (!found_empty_content_length) {
            print "Auth subrequest must clear Content-Length." > "/dev/stderr"
            exit 1
        }
    }
' "${default_config}"

grep -Eq \
    '^[[:space:]]*proxy_set_header[[:space:]]+X-Email[[:space:]]+\$email;' \
    "${default_config}" \
    || fail "Authenticated proxy config must overwrite X-Email."
grep -Eq \
    '^[[:space:]]*proxy_set_header[[:space:]]+Authorization[[:space:]]+"";' \
    "${default_config}" \
    || fail "Authenticated proxy config must strip downstream Authorization."

for hostname in \
    uploader.braingeneers.gi.ucsc.edu \
    uploader-dev.braingeneers.gi.ucsc.edu
do
    vhost_config="${script_dir}/${hostname}"
    location_config="${vhost_config}_location"

    grep -Eq \
        '^[[:space:]]*include[[:space:]]+/etc/nginx/vhost.d/default;' \
        "${vhost_config}" \
        || fail "${hostname} must include the authenticated default config."
    grep -Eq \
        '^[[:space:]]*proxy_set_header[[:space:]]+Upgrade[[:space:]]+\$http_upgrade;' \
        "${vhost_config}" \
        || fail "${hostname} must configure websocket Upgrade at vhost scope."
    grep -Eq \
        '^[[:space:]]*proxy_set_header[[:space:]]+Connection[[:space:]]+\$http_connection;' \
        "${vhost_config}" \
        || fail "${hostname} must configure websocket Connection at vhost scope."
    if grep -Eq '^[[:space:]]*proxy_set_header[[:space:]]+' "${location_config}"; then
        fail "${hostname}_location must not override inherited proxy headers."
    fi
done

docker run --rm \
    --entrypoint nginx \
    --add-host oauth2-proxy:127.0.0.1 \
    --volume "${default_config}:/test/default:ro" \
    --volume "${script_dir}/test-nginx.conf:/test/nginx.conf:ro" \
    nginxproxy/nginx-proxy:latest \
    -t -c /test/nginx.conf

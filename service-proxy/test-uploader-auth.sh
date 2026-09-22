#!/usr/bin/env sh
set -eu
nginx -t -c /test/test-uploader-auth.conf
nginx -c /test/test-uploader-auth.conf
trap 'nginx -s quit -c /test/test-uploader-auth.conf' EXIT
for port in 8080 8081; do
    base="http://127.0.0.1:${port}"
    status=$(curl -sS --max-time 5 -D /tmp/headers -o /tmp/body -w '%{http_code}' \
        -d 'test-body' "${base}/api/metadata/assist")
    test "$status" = 401
    grep -q 'authentication_required' /tmp/body
    grep -qi '^Content-Type: application/json' /tmp/headers
    grep -qi '^Cache-Control: no-store' /tmp/headers
    grep -Eqi '^X-Request-ID: [a-f0-9]{32}' /tmp/headers
    ! grep -qi '^Location:' /tmp/headers
    status=$(curl -sS --max-time 5 -D /tmp/headers -o /tmp/body -w '%{http_code}' "${base}/")
    test "$status" = 302
    grep -qi '^Location: https://auth.braingeneers.gi.ucsc.edu/oauth2/start' /tmp/headers
    status=$(curl -sS --max-time 5 -D /tmp/headers -o /tmp/body -w '%{http_code}' \
        -H 'Authorization: Bearer test-auth' -H 'X-Email: spoofed@example.org' \
        -d 'test-body' "${base}/api/metadata/assist")
    test "$status" = 200
    grep -q 'backend reached' /tmp/body
    grep -qi '^Observed-Email: fixture@example.org' /tmp/headers
    grep -qi '^Observed-Length: 9' /tmp/headers
    ! grep -qi '^Observed-Authorization:' /tmp/headers
done
echo 'Uploader API authentication, page redirects, and proxy identity verified.'

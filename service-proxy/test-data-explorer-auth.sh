#!/usr/bin/env sh
set -eu
nginx -t -c /test/test-data-explorer-auth.conf
nginx -c /test/test-data-explorer-auth.conf
trap 'nginx -s quit -c /test/test-data-explorer-auth.conf' EXIT
for path in /internal/dandi/admit /internal/dandi/unknown /internal/dandi%2fadmit; do
    for token in '' 'Bearer test-auth'; do
        status=$(curl -sS --max-time 5 -o /tmp/body -w '%{http_code}' -H "Authorization: ${token}" -d '{}' "http://127.0.0.1:8080${path}")
        test "$status" = 404
    done
done
status=$(curl -sS --max-time 5 -o /tmp/body -w '%{http_code}' http://127.0.0.1:8080/api/config)
test "$status" = 302
status=$(curl -sS --max-time 5 -o /tmp/body -w '%{http_code}' -H 'Authorization: Bearer test-auth' http://127.0.0.1:8080/api/config)
test "$status" = 200
echo 'Data Explorer admission denied at edge; ordinary routes retain authentication.'

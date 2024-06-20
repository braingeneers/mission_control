#!/bin/bash
set -e

# Wait until the certificate is generated, only after that can we enable the https configuration
# The https configuration is enabled by simply copying the static_https.conf file to the include directory
(
    echo "Checking if certificate exists, LETSENCRYPT_TEST=$LETSENCRYPT_TEST"
    while [ ! -f "/etc/nginx/certs/braingeneers.gi.ucsc.edu.crt" ]; do
        echo "Waiting for certificate to be generated..."
        sleep 5
    done
    sleep 2  # allow time for nginx to load first in case the cert already existed

    # Now we are sure the certificate is there, enable the https configuration
    echo "Enabling HTTPS and reloading nginx"
    mkdir -p /etc/nginx/conf.d/include
    cp /app/static_https.conf /etc/nginx/conf.d/include/
    service nginx reload
) &

echo "Starting nginx via docker-entrypoint.sh: $@"
/bin/bash /app/docker-entrypoint.sh "$@"

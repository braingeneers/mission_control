#!/usr/bin/env sh
set -v

echo "Verifying secrets are available..."
#until (cat /secrets/ci-logon-auth/cilogon-client-id && cat /secrets/ci-logon-auth/cilogon-client-secret) >/dev/null 2>&1; do
until cat /secrets/ci-logon-auth/cilogon-client-id && cat /secrets/ci-logon-auth/cilogon-client-secret; do
  echo 'Waiting for secrets to become available...';
  sleep 5;
done;

echo "Checking if certificate exists, LETSENCRYPT_TEST=$LETSENCRYPT_TEST"
while [ ! -f "/etc/ssl/certs/auth.braingeneers.gi.ucsc.edu.crt" ]; do
    echo "Waiting for auth certificate to be generated..."
    sleep 5
done
sleep 2  # allow time for nginx to load first in case the cert already existed (this may be unnecessary, added just in case)

echo "Copying cilogon.org certificates to /etc/ssl/certs/"
cp /tmp/cilogon-basic.pem /etc/ssl/certs/cilogon-basic.crt
cp /tmp/cilogon-openid.pem /etc/ssl/certs/cilogon-openid.crt
cat /etc/ssl/certs/*.crt > /etc/ssl/certs/ca-certificates.crt
update-ca-certificates

export OAUTH2_PROXY_PROVIDER=oidc
export OAUTH2_PROXY_OIDC_ISSUER_URL=https://cilogon.org/oidc
export OAUTH2_PROXY_LOGIN_URL=https://cilogon.org/authorize
export OAUTH2_PROXY_EMAIL_DOMAINS=*
export OAUTH2_PROXY_COOKIE_REFRESH=120h
export OAUTH2_PROXY_COOKIE_EXPIRE=168h
export OAUTH2_PROXY_CLIENT_ID_FILE=/secrets/ci-logon-auth/cilogon-client-id
export OAUTH2_PROXY_CLIENT_SECRET_FILE=/secrets/ci-logon-auth/cilogon-client-secret

export OAUTH2_PROXY_CLIENT_ID=$(cat $OAUTH2_PROXY_CLIENT_ID_FILE);
export OAUTH2_PROXY_CLIENT_SECRET=$(cat $OAUTH2_PROXY_CLIENT_SECRET_FILE);
export OAUTH2_PROXY_COOKIE_SECRET=$(head -c24 /dev/urandom | base64);

echo oauth2 proxy file: "$OAUTH2_PROXY_CLIENT_ID_FILE"
echo Email domain: "$OAUTH2_PROXY_EMAIL_DOMAINS"
echo client-id: $(cat /secrets/ci-logon-auth/cilogon-client-id)

echo "Starting oauth2-proxy"
/bin/oauth2-proxy --http-address ":80"

sleep 6000
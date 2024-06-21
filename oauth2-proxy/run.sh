#!/usr/bin/env sh
set -v

echo "Verifying secrets are available..."
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
update-ca-certificates

export OAUTH2_PROXY_PROVIDER=oidc
export OAUTH2_PROXY_OIDC_ISSUER_URL=https://cilogon.org
export OAUTH2_PROXY_LOGIN_URL=https://cilogon.org/authorize
export OAUTH2_PROXY_EMAIL_DOMAINS=*
export OAUTH2_PROXY_CLIENT_ID_FILE=/secrets/ci-logon-auth/cilogon-client-id
export OAUTH2_PROXY_CLIENT_SECRET_FILE=/secrets/ci-logon-auth/cilogon-client-secret
export OAUTH2_PROXY_COOKIE_SECRET_FILE=/secrets/ci-logon-auth/cilogon-cookie-secret

export OAUTH2_PROXY_CLIENT_ID=$(cat $OAUTH2_PROXY_CLIENT_ID_FILE);
export OAUTH2_PROXY_CLIENT_SECRET=$(cat $OAUTH2_PROXY_CLIENT_SECRET_FILE);
export OAUTH2_PROXY_COOKIE_SECRET=$(cat $OAUTH2_PROXY_COOKIE_SECRET_FILE);

echo "Debug> OAUTH2_PROXY_COOKIE_SECRET=${OAUTH2_PROXY_COOKIE_SECRET}"
echo "Encoded secret length: ${#OAUTH2_PROXY_COOKIE_SECRET}"
echo "Decoded secret length: $(echo -n $OAUTH2_PROXY_COOKIE_SECRET | base64 -d | wc -c)"

# Add this line to get the external port from an environment variable, defaulting to 8443
EXTERNAL_PORT=${EXTERNAL_PORT:-8443}

echo "Starting oauth2-proxy"
/bin/oauth2-proxy \
  --http-address ":80" \
  --reverse-proxy=true \
  --pass-host-header \
  --set-authorization-header=true \
  --scope="org.cilogon.userinfo email openid" \
  --pass-access-token \
  --whitelist-domain=".braingeneers.gi.ucsc.edu" \
  --redirect-url="https://auth.braingeneers.gi.ucsc.edu:${EXTERNAL_PORT}/oauth2/callback" \
  --skip-provider-button \
  --request-logging=true \
  --auth-logging=true \
  --standard-logging=true \
  --proxy-prefix="/oauth2" \
  --cookie-name="_oauth2_proxy" \
  --cookie-domain=".braingeneers.gi.ucsc.edu" \
  --cookie-secure=true \
  --cookie-httponly=true \
  --cookie-refresh="120h" \
  --cookie-expire="168h" \
  --cookie-path="/" \
  --set-xauthrequest=true \
  --provider="oidc" \
  --oidc-issuer-url="https://cilogon.org" \
  --login-url="https://cilogon.org/authorize" \
  --email-domain="*" \
  --skip-auth-regex="^/oauth2" \
  --pass-authorization-header=true \
  --pass-user-headers=true \
  --real-client-ip-header="X-Forwarded-For" \
  --code-challenge-method="S256" \
  --set-xauthrequest=true

sleep 6000  # avoid fast crash loop and allow for debugging

#!/usr/bin/env sh

until cat /secrets/cilogon-client-id && cat /secrets/cilogon-client-secret; do
  echo 'Waiting for secrets...';
  sleep 5;
done;

export OAUTH2_PROXY_CLIENT_ID=$(cat $OAUTH2_PROXY_CLIENT_ID_FILE);
export OAUTH2_PROXY_CLIENT_SECRET=$(cat $OAUTH2_PROXY_CLIENT_SECRET_FILE);
export OAUTH2_PROXY_COOKIE_SECRET=$(head -c24 /dev/urandom | base64);

echo oauth2 proxy file: "$OAUTH2_PROXY_CLIENT_ID_FILE"
echo Email domain: "$OAUTH2_PROXY_EMAIL_DOMAINS"
echo client-id: $(cat /secrets/cilogon-client-id)

/bin/oauth2-proxy

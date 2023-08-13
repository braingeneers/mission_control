#!/bin/bash

# Create secrets directory
mkdir -p /secrets

# Get secrets
secrets=$(kubectl get secrets -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | awk NF)

echo "Fetching secrets..."

for secret in $secrets; do

  echo "Processing secret: $secret"

  # Create directory for the secret
  mkdir -p "/secrets/$secret"

  # Get .data
  data=$(kubectl get secret $secret -o json)

  # Get keys
  keys=$(echo "$data" | jq -r '.data | keys[]')

  # Process each key
  for key in $keys; do

    echo "Fetching key: $key from secret: $secret"

    # Run the fetching, decoding, and saving operations in the background
    (
      # Get data for each key using jq
      data_key=$(echo "$data" | jq -r ".data[\"$key\"]")

      # Decode and save data
      echo "$data_key" | base64 --decode > "/secrets/$secret/$key"
    ) &

  done

  # Wait for all background processes to finish before processing the next secret
  wait

done

# Make entrypoint-setup.sh available in the secrets volume
cp /entrypoint-secrets-setup.sh /secrets/entrypoint-secrets-setup.sh

# List the contents of /secrets directory
echo "Listing all fetched secrets..."
ls -lR /secrets

echo "Task complete, main process sleeping so healthcheck can continue."
touch /tmp/SECRET_FETCHER_COMPLETE_TOKEN
sleep infinity

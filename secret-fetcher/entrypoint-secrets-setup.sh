#!/bin/sh
#
# This script wraps the original entrypoint.
# It allows for copying files from the dynamic secrets volume to the correct location.
#
# Usage example in docker-compose.yaml:
#
#    In this example the S3 credentials files is copied to the location it's expected in the container, then the
#    original entrypoint is executed with the original command and arguments as defined in `command`.
#
#    services:
#      your-service:
#        image: your-image:latest
#        entrypoint: /secrets/entrypoint-setup.sh
#        command: ["--copy", "/secrets/prp-s3-credentials/credentials:/root/.aws/credentials", "original-entrypoint-command", "arg1", "arg2"]
#        volumes:
#          - secrets:/secrets
#        depends_on:
#          # This dependency ensures the secrets volume has been populated before starting your-service.
#          secret-fetcher:
#            condition: service_healthy
#
#    volumes:
#      # A shared volume for secrets only in-memory for security this is populated by the secret-fetcher service
#      secrets:
#        driver_opts:
#          type: tmpfs
#          device: tmpfs



# Loop through arguments and copy as defined, and export environment variables from a file
while [ "$#" -gt 0 ]; do
  case "$1" in
    --copy)
      arg="$2"
      COPYFROM="${arg%%:*}"
      COPYTO="${arg##*:}"
      mkdir -p "$(dirname "$COPYTO")"
      cp "$COPYFROM" "$COPYTO"
      shift 2
      ;;
    --env)
      # Export environment variables from the specified file, excluding lines that start with #
      export $(grep -v '^#' "$2" | xargs)
      shift 2
      ;;
    *)
      break
      ;;
  esac
done

# Execute the remaining arguments as the command
exec "$@"

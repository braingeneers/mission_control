#!/bin/sh
echo "Secret Fetcher: Setting up secrets"

ENV_VARS=""

# Loop through arguments and perform copy and env operations
while [ "$#" -gt 0 ]; do
  case "$1" in
    --copy)
      arg="$2"
      COPYFROM="${arg%%:*}"
      COPYTO="${arg##*:}"
      mkdir -p "$(dirname "$COPYTO")"
      cp "$COPYFROM" "$COPYTO"
      echo "Secret Fetcher: copied $COPYFROM to $COPYTO"
      shift 2
      ;;
    --env)
      # Add environment variables from the specified file to ENV_VARS
      ENV_VARS="$ENV_VARS $(grep -v '^#' "$2" | xargs)"
      echo "Secret Fetcher: added environment variables from $2"
      shift 2
      ;;
    *)
      break
      ;;
  esac
done

# Execute the remaining arguments as the command, with environment variables
echo "Executing command: $@"
exec env $ENV_VARS "$@"

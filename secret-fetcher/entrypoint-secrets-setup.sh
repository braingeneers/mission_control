#!/bin/bash

ENV_VARS=""

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
      # Add environment variables from the specified file to ENV_VARS
      ENV_VARS="$ENV_VARS $(grep -v '^#' "$2" | xargs)"
      shift 2
      ;;
    *)
      break
      ;;
  esac
done

# todo remove debug line
echo "DEBUG> APP_KEYS: $APP_KEYS"

# Execute the remaining arguments as the command, with environment variables
echo "Executing command: $@"
exec env $ENV_VARS "$@"

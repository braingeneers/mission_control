#!/usr/bin/env bash
set -euo pipefail

watch 'wc -l /tmp/rclone_list/braingeneers/* | awk '\''{ sub(".*/", "", $2); print $1, $2 }'\'' | sort -nr'

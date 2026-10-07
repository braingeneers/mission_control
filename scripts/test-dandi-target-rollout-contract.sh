#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash -n scripts/deploy-dandi-target.sh
config=$(docker compose -f docker-compose.yaml -f docs/dandi-target-transition.compose.yaml config --format json)
jq -e '
  .services["workflows-backend"].environment.WORKFLOW_REPO_SYNC_ENABLED == "false"
  and (.services["workflows-backend"].image | test("^braingeneers/workflows-backend:[0-9]{8}-[0-9a-f]{12}$"))
  and (.services.workflows.image | test("^braingeneers/workflows-frontend:[0-9]{8}-[0-9a-f]{12}$"))
  and ((.services["workflows-backend"].image | split(":")[1]) == (.services.workflows.image | split(":")[1]))
' <<<"$config" >/dev/null
echo 'DANDI transition pins and source synchronization contract passed'

# Uploader-dev Recipes rollout — September 25, 2026

This release replaces the candidate uploader's MQTT publisher with the Workflows HTTP API.
The main `uploader` service stays on its existing image and MQTT configuration. Both uploaders
still use production data (`PROD=true`). No scientific workflow source or parameters change.

Published services: Workflows backend/frontend `20260925-f860b5615638`, notification-service
`1.2.0`, and uploader-dev `20260925-09b03bc43b5d`, pinned in `docker-compose.yaml`.

Run these commands **on the server, from its Mission Control checkout**, outside active
uploader-dev uploads. Uploader sessions/multipart bookkeeping are in memory and cannot survive
recreation. No shared database, broker, proxy or mail-relay restart is required.

```bash
git pull --ff-only
docker compose pull notification-service workflows-backend workflows uploader-dev
docker compose up -d --no-deps --wait notification-service
docker compose up -d --no-deps --wait workflows-backend
docker compose exec -T workflows-backend alembic current
docker compose up -d --no-deps workflows
```

Expect Alembic head `0021_http_launch_requests`. Backend startup applies the additive migration.
Existing standalone/MQTT runs retain their existing behavior; accepted HTTP requests and their
notification rows are committed before asynchronous Kubernetes submission.

Enable the three existing Ephys recipes and set Standard as the lab default. This script uses
review/edit APIs and current revisions, verifies that every scientific setting is unchanged, and
prints the recipe names it enabled. It creates no runs and sends no notifications. This setup is
one-time; rerunning its default-setting step later would replace an administrator's newer choice.

```bash
read -r -p 'Your lab email for the audit log: ' LAB_EMAIL
docker compose exec -T workflows-backend python scripts/enable-uploader-recipes.py \
  --actor "$LAB_EMAIL" \
  --recipe-id 08ee876f-0972-4fe3-ab20-9d1eced743f6 \
  --recipe-id 62508f74-35b7-4319-8cee-3ff1b7d90235 \
  --recipe-id 507d4627-454d-48e6-9933-017175b8872c \
  --default-recipe-id 08ee876f-0972-4fe3-ab20-9d1eced743f6
unset LAB_EMAIL
docker compose up -d --no-deps --wait uploader-dev
make verify-uploader-deployment SERVICE=uploader-dev
docker compose ps notification-service workflows-backend workflows uploader-dev
```

Visit uploader-dev with a fresh browser preference: Section 5 should show Ephys Pipeline Standard,
the other two enabled recipes, Upload only, and Notify me. No Processing dropdown or parameters.
`/admin` controls the shared default. Existing explicit browser choices override it until
**Use lab default** in Recipe help. Hidden/archived remembered recipes require an explicit new
selection. Create/Edit Recipe has **Make available in uploader** beside name and purpose.

Slack exact email lookup requires the bot scope `users:read.email`. If absent, the Slack app operator
must grant it and reauthorize/reinstall the app, updating the operator-owned token only if needed.
Do not change Kubernetes Secrets as part of this release. Missing scope, no matching active human,
or lookup outage leaves email notifications enabled and records a run event. No credentials are
shared with the uploader or Workflows. No real email or Slack messages were sent during validation.

After deployment, use an operator-selected small upload to check production identity, processing
run link and terminal email/Slack delivery. Notify me can be unchecked for an initial processing
check; recipients can also be removed in Workflows while the run is active. A processing submission
failure must still leave upload status successful and offer a retry without uploading again.
A recipe/source revision change during upload instead requires reviewing the current recipe in
Workflows; the service never silently changes the saved processing settings.

Rollback the uploader-dev image **and its transport environment** together to the previous
`20260924-0f638311e794` pin and MQTT settings if necessary, again outside active uploads.
The Workflows migration is additive; leave it applied. Do not delete its HTTP request ledger,
which prevents accepted launches from being duplicated after retries or run deletion.

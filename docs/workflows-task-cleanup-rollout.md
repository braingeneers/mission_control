# Workflows task cleanup release

The paired images are `braingeneers/workflows-backend:20261012-817dc2b9c82b`
and `braingeneers/workflows-frontend:20261012-817dc2b9c82b`, from Workflows
commit `817dc2b9c82bbe34f6f220b2da81237c09d5ac2a`.
Both versioned tags and `latest` were published successfully. Registry digests:

- Backend: `sha256:b74b8bd35edd9692ef41d74a40aefacb998d1190902f982c9491230cb47b45fa`
- Frontend: `sha256:c9fd4c8f0b8997ab00aa584f6562092858eb7972fc5110d55f92f4e848128cd2`

Hosted recreation is pending operator evidence.

New launcher failures and explicit Stop requests use a durable RunEvent cleanup
checkpoint. Before stopping verified native Nextflow Jobs, the worker captures
bounded diagnostics and commits Job UID intent. It uses normal foreground
deletion, complete paginated inventories, 30-second polling and a 15-minute
budget. Unknown ownership or node termination blocks cleanup and keeps admission
capacity reserved. Same-UID node recovery can be verified on an explicit Stop
retry; disappearance alone is insufficient. Pods are never force-deleted.

Failed/cancelled runs retain their outcome and offer **Stop remaining tasks**.
Archive requires fresh shutdown evidence. Running drivers retain bounded redacted
Nextflow log/trace snapshots; native task identities preserve log access without
a terminal trace. No automatic workflow relaunch or historical failure sweep is
added. Existing application/task retries and manual Clone remain unchanged.

The database stays at `0022_cluster_admission`; no new migration, worker image,
Secret, quota, proxy or notification-service update is required. DANDI recovery
support from the October 9 release is retained.

## Validation

Docker validation passed the full backend suite (585 tests, including disposable
PostgreSQL), followed by 125 relevant regression tests after the final diagnostic
concurrency fix. PostgreSQL used the actual Alembic schema through migration 0022.
The frontend passed 181 tests, its production build, the cleanup browser audit at
desktop/mobile widths, and the existing Runs layout audit at six widths. Production
dependency audit and Kubernetes manifest rendering also passed. Each production
backend build validates the packaged workflow catalog.
The exact backend image also passed startup/readiness, cleanup API schema and
Grant 0.8.8 catalog checks against a freshly migrated disposable PostgreSQL
database, with background workers disabled. Test fixtures were excluded.

## Operator recreation

On **braingeneers.gi.ucsc.edu**, in the existing **mission_control** checkout,
check that the working tree is clean before pulling. If it has local changes,
stop and share `git status --short` before proceeding.

```bash
git status --short
git pull --ff-only
docker compose pull workflows-backend workflows
docker compose up -d --no-deps --force-recreate --wait workflows-backend workflows
docker compose ps workflows-backend workflows
docker inspect --format '{{.Name}} {{.Config.Image}} {{.State.Status}}' workflows-backend workflows
docker compose exec -T workflows-backend curl -fsS http://localhost:8000/readyz
```

Expected evidence: both containers use the `20261012-817dc2b9c82b` images,
backend is healthy, frontend is running, and readiness returns `{"status":"ready"}`.
Share the output before treating hosted deployment as verified. Then verify the
authenticated run API exposes `cleanup`, both Runs and run-detail routes load,
the Grant catalog remains version 0.8.8, and the weekly schedule remains unchanged.
Do not induce a production failure or relaunch a workflow to test cleanup.

## Incident recovery

Original grant run `b448950b-ac56-4ccc-b2b5-4ccfdaba6cdd` was cloned to
`93127ab7-5bcf-4144-996d-3211b344d2ed`. The surviving evaluator was stopped by
UID-guarded foreground Job deletion after capturing 646/674 assessments. Fresh
namespace enumeration verified its Job/Pod had gone before the original was
archived at 20:48 UTC on October 12. The replacement retained the launch settings,
notifications and workflow version 0.8.8; its initial admission wait was namespace
pod capacity. Schedules and admission ceilings were not changed. The available
mount/network warnings do not establish the driver's exact terminal cause.

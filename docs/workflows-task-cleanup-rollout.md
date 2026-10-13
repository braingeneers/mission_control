# Workflows task cleanup release

The paired images are `braingeneers/workflows-backend:20261012-817dc2b9c82b`
and `braingeneers/workflows-frontend:20261012-817dc2b9c82b`, from Workflows
commit `817dc2b9c82bbe34f6f220b2da81237c09d5ac2a`.
Both versioned tags and `latest` were published successfully. Registry digests:

- Backend: `sha256:b74b8bd35edd9692ef41d74a40aefacb998d1190902f982c9491230cb47b45fa`
- Frontend: `sha256:c9fd4c8f0b8997ab00aa584f6562092858eb7972fc5110d55f92f4e848128cd2`

The operator reported restarting both services on October 12. Authenticated
HTTPS checks at 21:40 UTC returned `{"status":"ready"}`, exposed the new Run
`cleanup` field, and served `/assets/index-DGOY9G33.js` with SHA-256
`f3bc6655e9e6b9cdfc9e17092c86c61ee3d4aae0fab6c7f9ee9d7ff2b7fabb06`, matching
the published frontend image exactly. These checks verify hosted feature
availability and the frontend bundle; container image IDs were not supplied.
The weekly Grant schedule remained enabled and unchanged, with its next
occurrence on October 19 at 14:00 UTC.

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
After recreation, the clone waited for capacity: namespace quota showed 200/200
Pods used by other batches, while Workflows observed additional committed capacity
for unscheduled Jobs. Separate RTsort validation Jobs carrying Workflows ownership
labels temporarily added an unreserved-workflow admission wait. The operator asked
that these independent workloads remain running. No external Job, quota or
admission policy was changed.

Capacity drained and the clone was admitted at 23:43 UTC on October 12, about
3 hours 23 minutes after creation. It succeeded at 00:20 UTC on October 13, about
37 minutes after admission. The collected trace records all six processes as
`COMPLETED`, exit zero, with one task each; no active run Pods remained. The live
diagnostic snapshots were available on the hosted backend. Rendering peaked at
3.1 GB RSS in the trace; a same-UID read-only cgroup check observed about 3.2 GiB
within the 4 GiB limit before it finished successfully.
The final fresh admission observation showed zero reserved runs, reserved task
slots and queued runs, with no hold. The weekly schedule still had its unchanged
October 12 14:00 update timestamp and next occurrence on October 19 at 14:00 UTC.

The evaluator completed all 674 selected opportunities: 646 cached assessments
were reused and 28 were new. Three invalid model responses were recovered within
31 API attempts. Ingestion pinned the evaluation date to October 12 even though
evaluation finished after midnight UTC. The immutable publication is
`s3://braingeneers/workflows/grant-opportunities-report/runs/2026-10-13T00-18-14Z/`.
Independent streamed GETs verified all 13 file sizes and SHA-256 digests against
the completion marker, including both PDFs, HTML, CSV, source/audit exports and
provenance. The shared `state/latest.json` matched the published `next-state.json`
digest. Workflows records both email notifications and the Slack notification as
delivered on their first attempts; the notification service accepted delivery.
This confirms submission, not receipt or reading in recipients' inboxes.

The audit remains `traceable_with_warnings`: 39 assessments require evidence
review, with zero incomplete evaluations. Foundation discovery enrolled four
sources, quarantined 95 and rejected one; it included no opportunities and logged
13 source warnings. NIH recurring-deadline extraction also recorded warnings.
Execution and file integrity are verified; comprehensive grant coverage and the
correctness of individual recommendations require review. This successful run did
not exercise cleanup after a new production failure; failure-path confidence
continues to come from the regression and isolated image checks above.

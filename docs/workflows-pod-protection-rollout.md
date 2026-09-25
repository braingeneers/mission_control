# Workflows pod protection rollout — September 25, 2026

Release: `20260925-56427ead0824` for both Workflows images, from Workflows
commit `56427ead0824`. The backend retains Alembic `0022_cluster_admission`.
The existing Compose command applies migrations before starting Uvicorn.
This correction includes the published Braindance v0.4 source in its image fallback.

The operator restarted initial protection release `20260925-a63af1265893` and
the live admission API verified fresh observations. Braindance v0.4 / Maxwell
v0.1.15 were then published and the catalog reloaded. Fresh NRP canary
`7656596f-01a5-4833-b745-919e3c55eb10` completed with eight successful task Jobs,
at most two concurrent task Pods and three task submissions per rolling minute.
Its scientific outputs, manifests, exact recovery bytes and linked replacements
were verified.

That canary exposed an ignored `k8s.labels` option: task Pods were counted as
external work. This correction assigns the immutable `workflows_<run UUID>`
Nextflow name and uses the native `nextflow.io/runName` label on Jobs and Pods.
The complete backend suite and real nf-k8s manifest capture with both parsers
passed; Secret and scratch settings remain intact. The operator confirmed the
targeted corrective recreation, and the live checks below verified the corrected
behavior. No schema change was required beyond 0022.

## Completed deployment procedure

These are the operator commands supplied for the completed deployment, retained
as a reference. No further restart is needed for the verification-note update.
On **braingeneers.gi.ucsc.edu**, from the existing **mission_control** checkout:

```bash
git pull --ff-only
docker compose pull workflows-backend workflows
docker compose up -d --no-deps --force-recreate workflows-backend workflows
docker compose ps workflows-backend workflows
docker compose exec -T workflows-backend alembic current
docker compose logs --tail=80 workflows-backend workflows
```

Expected: both services run image `20260925-56427ead0824`, the migration reports
`0022_cluster_admission (head)`, and startup succeeds. Stop here on migration,
startup or observation errors; preserve the output for diagnosis. Do not restart
the database, proxy, uploader or any unrelated service. Server execution remains
operator-owned.

Afterward, verify the authenticated
`https://workflows.braingeneers.gi.ucsc.edu/api/settings/admission` endpoint and
Settings → Cluster launch protection. Expect a fresh observation (15-second
polling, 45-second freshness bound) and defaults of 150 namespace pods, four runs,
20 task slots/run, five task submissions/minute/run, 30 total managed Job
submissions/minute, and two collectors. NRP's namespace quota is 200 pods;
zero-pod quotas scoped to banned priority classes are not namespace budgets.

Existing unbounded runs are allowed to finish and prevent new admission until
they drain. Previously accepted, unsubmitted launch snapshots require Stop and
Clone. No running workflow is cancelled automatically. An NRP low-utilization
rejection creates a durable hold for review in Settings; a fresh rejected attempt
re-latches it after clearance. Pausing new starts retains accepted work in the
database and leaves bounded artifact collection available.

## Completed production verification

After the corrective restart, reuse canary
`86e70394-484c-4fb4-9d4f-fdae39fdc31a` completed at 21:25:27 UTC on September 25.
The driver used its immutable Nextflow name; all four successful task Jobs and
Pods carried the matching native ownership label. No raw or derived conversion
ran again. Peak task concurrency was one Pod and the maximum was two task Job
creations per rolling minute. Downloaded NWB, LINDI, validation and linked-source
bytes were unchanged; original recovery bytes, eight complete manifests and the
unrelated source object were verified again.

The live ledger counted the owned task within its reservation rather than as
external activity. After completion and cooldown, the authenticated admission
endpoint reported fresh observations, zero run/task-slot/task-rate/helper
reservations, two external pods, no hold and no queued runs. This verifies live
API and Kubernetes behavior; the UI walkthrough below used the local production
image because production browser access was unavailable.

Braindance v0.4/Maxwell v0.1.15 are published. Retain the default budgets for a
bounded-subset rollout before one dataset at a time. Measure large-recording
memory, scratch and throughput; these tiny NRP fixtures do not establish that
headroom. Defaults are not an NRP-approved allocation, and direct submissions
remain outside website admission control.

Local evidence before publication: complete backend regression suite; frontend
unit/build checks and desktop/mobile production-image walkthrough; PostgreSQL
migration and simultaneous reservation tests; both Nextflow parser modes and
measured 5/min task limiting; read-only live namespace observation. Scientific
fixture checks cover standalone/fused equality, interrupted upload recovery,
fresh and reused paired NWBs, selective derived rebuild, manifests, exact recovery
bytes and linked-source replacement. Both subsequent NRP canaries are described
above; large-recording resource headroom remains a separate measurement. Full
implementation and evidence are in the
[Workflows report](https://github.com/braingeneers/workflows/blob/main/docs/pod-efficiency.md).

If application rollback becomes necessary, retain the additive database table;
do not downgrade/drop it while any reservations exist. Reverting to the previous
backend disables these launch protections, so pause automated producers first
and treat rollback as a separate operator decision.

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
passed; Secret and scratch settings remain intact. One targeted recreation is
required to run the corrected backend. No schema change is required beyond 0022.

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

Then run the bounded reuse canary and verify native ownership before broad
launches. Braindance v0.4/Maxwell v0.1.15 are already published. Check actual task
rates/peak pod counts, source/output verification, memory and scratch, and full
reuse. Do not interpret a local fixture test as proof of full-dataset throughput.

Local evidence before publication: complete backend regression suite; frontend
unit/build checks and desktop/mobile production-image walkthrough; PostgreSQL
migration and simultaneous reservation tests; both Nextflow parser modes and
measured 5/min task limiting; read-only live namespace observation. Scientific
fixture checks cover standalone/fused equality, interrupted upload recovery,
fresh and reused paired NWBs, selective derived rebuild, manifests, exact recovery
bytes and linked-source replacement. The subsequent fresh NRP canary is described
above; large-recording resource headroom remains a separate measurement.

If application rollback becomes necessary, retain the additive database table;
do not downgrade/drop it while any reservations exist. Reverting to the previous
backend disables these launch protections, so pause automated producers first
and treat rollback as a separate operator decision.

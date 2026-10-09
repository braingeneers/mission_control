# Human-reviewed DANDI upload recovery release

The October 9 release adds recovery for interrupted shared `sync_collection`
uploads. Checks read DANDI and immutable journals. A signed-in researcher reviews
and approves the exact check in Data Explorer; fresh verification then imports
proven ownership and releases the collection gate atomically. Original conflict
jobs and results remain unchanged. Uploads require a fresh plan and normal review.
Agents may prepare checks and share links, but must never approve for a human.

## Published artifacts

| Component | Image | Contract |
| --- | --- | --- |
| Data Explorer | `braingeneers/data-explorer:20261009-9cba05309fb5` | Additive migration `0006_dandi_recovery` |
| Workflows backend | `braingeneers/workflows-backend:20261009-0810a9ee6375` | Fresh writer-quiescence API; no new migration |
| Workflows frontend | `braingeneers/workflows-frontend:20261009-0810a9ee6375` | Paired with backend; Compose service is `workflows` |
| DANDI worker | `braingeneers/dandi-publication:0.5.0` | Schema-four read-only recovery; workflow `0.6.0` |

Service images also publish `latest`; production uses the immutable tags above.
Existing target selection, DANDI credentials, namespaces and scientific data are
preserved. Installing the release does not clear gates or resume work.
The Workflows image also retains the upstream Braindance sorting/conversion
changes already on main; the recovery change is committed independently.

## Operator sequence

Run these commands on **braingeneers.gi.ucsc.edu**, from the existing Mission
Control checkout. Pause new DANDI launches for this short update. Confirm the
checkout is clean before pulling. Existing interrupted-upload gates must remain;
do not clear them as a rollout prerequisite.

```bash
git status --short
git pull --ff-only
docker compose pull workflows-backend workflows data-explorer
docker compose up -d --no-deps --force-recreate --wait workflows-backend workflows
docker compose ps workflows-backend workflows
```

Provide the output. Before Data Explorer recreation, verify the HTTPS quiescence
route and `dandi-publication` catalog version `0.6.0`, target selector, worker
`0.5.0` and fixed origins. The Workflows startup reloads its catalog; use its
authenticated catalog-reload API if necessary. Do not proceed if Workflows is
unhealthy or still has the old contract.

Archive the Data Explorer schema using the existing verified dump procedure,
then recreate only Data Explorer:

```bash
docker compose exec -T sql-db sh -ceu '
  umask 077
  archive_path="/replicated/sql-db/postgres/data-explorer-before-dandi-recovery-$(date -u +%Y%m%dT%H%M%SZ).dump"
  archive_tmp_path="${archive_path%/*}/.${archive_path##*/}.tmp"
  test ! -e "$archive_path"
  test ! -e "$archive_tmp_path"
  pg_dump -U services -d services --schema=data_explorer -Fc -f "$archive_tmp_path"
  pg_restore --list "$archive_tmp_path" >/dev/null
  mv "$archive_tmp_path" "$archive_path"
  printf "Verified archive: %s\n" "$archive_path"
'
docker compose up -d --no-deps --force-recreate --wait data-explorer
docker compose ps data-explorer
docker compose images workflows-backend workflows data-explorer
```

Its entrypoint upgrades to `0006_dandi_recovery` before serving. Verify protected
HTTPS `/healthz.publication_database`: `verified: true`, schema `data_explorer`,
revision `0006_dandi_recovery`, and a new startup timestamp. Check API discovery,
the human-only approval denial for a service account, and unchanged existing
conflict gates. Publishing images, Compose pins and health checks alone do not
prove this acceptance. Do not restart unrelated services or change Secrets.

## Acceptance and researcher handoff

Use a representative Sandbox interrupted shared-upload case first. An agent
may prepare its recovery, poll read-only status and share the returned URL.
Only a signed-in researcher may acknowledge and approve it in Data Explorer.
Verify applied provenance, the new reconciliation receipt, preserved original
conflict and a fresh upload plan. No scientific upload is part of recovery.

Then prepare independent production reviews for:

| Collection | Dandiset | Original conflict job |
| --- | --- | --- |
| braindance-raw | 001962 | `ee10f6f9-aa59-4525-a18b-0fc5cd7f48e3` |
| braindance-sorted | 001963 | `fa2d9dca-f58c-4098-94eb-0ee0d6353d27` |
| ephys-raw | 002007 | `4287d02f-e6fb-488a-80f2-961f72187a08` |

The historical immutable journals reconstruct 307, 383 and 23 confirmed uploads
respectively, with one unresolved attempt absent in each recorded draft. This
proves historical compatibility, not that live DANDI still matches. Fresh worker
observations and human approval remain mandatory. Coordinate external DANDI
writers; Data Explorer cannot fence their edits. Missing evidence, active writers,
unresolved retirements, changed ownership or unexplained inventory/access/metadata
changes remain gated. Verification snapshots expire after five minutes.

See the [application recovery procedure](https://github.com/braingeneers/data-explorer/blob/main/docs/dandi-recovery-rollout.md)
and [agent collection guidance](https://github.com/braingeneers/data-explorer/blob/main/skills/data-explorer-cli-access/references/dandi-collections.md).

## Rollback

Preserve schema `0006_dandi_recovery`, its audit rows and immutable evidence.
Prefer a corrected compatible image. An older app cannot accept the new migration
head; disable publication before attempting an older application, and verify its
startup separately. Never downgrade the schema or clear gates with SQL.

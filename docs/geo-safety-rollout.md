# Combined collection and GEO safety rollout

The safety release binds FTP confirmation to the reviewed package, pins S3
scientific inputs, and resumes only transfers with durable per-file evidence.
Deploying it does not save dataset metadata, build a production package, push to
GEO, submit a spreadsheet, or record an accession.

This cutover also includes the companion general DANDI collection release;
source commits and published images do not establish that the hosted services
have been recreated.

## Release contracts

- Mission Control pins official immutable date/SHA Data Explorer and matching
  Workflows backend/frontend images. The loaded `geo-publication` definition and
  image-pinned fallback both use workflow 0.2.0 and
  `braingeneers/geo-publication:0.2.0`.
- Deploy the companion Uploader image with independent collection details and
  retain the promoted state volumes. Persist collection details at
  `COLLECTION_METADATA_DIR=/replicated/uploader/collection-metadata`; preserve
  `METADATA_TEMPLATE_DIR=/replicated/uploader-dev/metadata-templates` and
  `WHATS_NEW_DIR=/replicated/uploader-dev/whats-new` separately. Uploader requires
  no database migration.
- Preserve the combined Compose wiring: Data Explorer reads saved collection
  revisions through `DATA_EXPLORER_UPLOADER_API_URL=http://uploader:8000`, and
  Uploader reads verified inspection seeds through
  `DATA_EXPLORER_INTERNAL_URL=http://data-explorer:8000`. These integrations are
  optional at startup; do not add reciprocal service startup dependencies.
- Data Explorer advances to `0005_general_dandi_collections`, preserving legacy
  publication records and both environment histories. Deploy both DANDI workflow
  definitions at 0.5.0 with `braingeneers/dandi-publication:0.4.0` before starting
  the new Data Explorer image. Workflows remains at `0022_cluster_admission`;
  the GEO safety changes add no migration or status constraint. Follow the
  [collection rollout contract](https://github.com/braingeneers/data-explorer/blob/main/docs/dandi-collections-rollout.md)
  alongside this combined cutover.
- The existing NRP `braingeneers/geo-ftp` Secret must have `username`, `password`,
  and `upload_dir`; credentials remain exclusive to the FTP task. No Secret
  mutation is required.
- Historical packages remain readable. Packages without version-2 provenance
  require a new package before FTP. Missing/stale review tokens are rejected.

Hosted Data Explorer health was verified at `0004_geo_publications` on
September 30, 2026 at 20:52 UTC. That is the observed pre-cutover schema, not
evidence of the new `0005` deployment. Verify the running images, loaded workflow
definitions, and post-cutover startup health separately.

## Operator cutover

Run these commands only on `braingeneers.gi.ucsc.edu`, from the Mission Control
checkout. Coordinate a maintenance window with no new upload or publication
requests. Agents do not SSH to the server or recreate its services.

1. Inspect publication gates before replacing Data Explorer. The active-work
   queries below must return zero rows. Preserve and reconcile unresolved
   requests through the owning service; never edit SQL status values to clear
   a gate.

   ```bash
   docker compose exec -T sql-db psql -U services -d services -v ON_ERROR_STOP=1 -c \
     "SELECT id,status FROM data_explorer.dandi_publication_jobs WHERE status IN ('preparing','dispatching','queued','submitted','launching','running','conflict');"
   docker compose exec -T sql-db psql -U services -d services -v ON_ERROR_STOP=1 -c \
     'SELECT target_key,dandi_instance,active_job_id FROM data_explorer.dandi_collection_targets WHERE active_job_id IS NOT NULL;'
   docker compose exec -T sql-db psql -U services -d services -v ON_ERROR_STOP=1 -c \
     "SELECT id,status,request_id FROM data_explorer.geo_jobs WHERE status IN ('queued','running');"
   ```

   Separately inspect historical GEO conflicts and confirm their upstream runs
   are terminal before proceeding:

   ```bash
   docker compose exec -T sql-db psql -U services -d services -v ON_ERROR_STOP=1 -c \
     "SELECT id,request_id,run_id FROM data_explorer.geo_jobs WHERE status = 'conflict';"
   ```

   A terminal GEO conflict with unknown remote effects remains blocked for
   reconciliation; a fresh reviewed package/folder is the recovery path. Do not manufacture a new
   request UUID for the old operation. The older application hides GEO reads
   when its feature flag is off, so reconcile existing work before disabling it.
   The corrected application keeps authenticated history/reconciliation reads
   available with mutations disabled.

2. Pull the committed pins, stop intake, and make a verified schema archive.
   Keep the archive path in the deployment record.

   ```bash
   git pull --ff-only
   docker compose pull data-explorer workflows-backend workflows uploader
   docker compose stop data-explorer
   docker compose exec -T sql-db sh -ceu '
     umask 077
     archive_path="/replicated/sql-db/postgres/data-explorer-before-geo-safety-$(date -u +%Y%m%dT%H%M%SZ).dump"
     archive_tmp_path="${archive_path%/*}/.${archive_path##*/}.tmp"
     test ! -e "$archive_path"
     test ! -e "$archive_tmp_path"
     pg_dump -U services -d services --schema=data_explorer -Fc -f "$archive_tmp_path"
     pg_restore --list "$archive_tmp_path" >/dev/null
     mv "$archive_tmp_path" "$archive_path"
     printf "Verified archive: %s\n" "$archive_path"
   '
   ```

   Recheck the three gates after stopping intake. If new work appeared, restore
   the current service for reconciliation and postpone the cutover.

3. Recreate and verify Workflows and the companion Uploader before starting
   Data Explorer on migration 0005. Remain within the maintenance window with
   no new upload or publication requests.

   ```bash
   docker compose up -d --no-deps --force-recreate --wait workflows-backend workflows
   docker compose up -d --no-deps --force-recreate --wait uploader
   make verify-uploader-deployment SERVICE=uploader
   ```

   Verify Workflows readiness and the actual admin catalog: `geo-publication`
   0.2.0, official worker 0.2.0, and the expected source revision. Both DANDI
   definitions must be 0.5.0 with worker `braingeneers/dandi-publication:0.4.0`.
   Use the authenticated Operations reload if the managed catalog needs refresh;
   no host Workflows source checkout is mounted. Preserve historical launch
   snapshots and do not clone old immutable publication requests. Stop here if
   any loaded workflow or worker differs from the release contract.

   Verify Uploader's running version and the persistent collection-details,
   template, and announcement paths. Saving collection details does not update
   DANDI; its inspection integration can reconnect once Data Explorer starts.

4. Install Data Explorer with GEO mutations disabled. Keep publication storage
   enabled so startup verifies the database and authenticated history remains
   readable. The temporary override contains no credentials.

   ```bash
   cat > .geo-intake-disabled.yaml <<'YAML'
   services:
     data-explorer:
       environment:
         DATA_EXPLORER_PUBLICATION_ENABLED: "true"
         DATA_EXPLORER_GEO_ENABLED: "false"
   YAML
   docker compose -f docker-compose.yaml -f .geo-intake-disabled.yaml up -d --no-deps --force-recreate --wait data-explorer
   ```

   Through authenticated HTTPS, verify Data Explorer's startup health reports
   verified schema `data_explorer`, revision `0005_general_dandi_collections`,
   migrations mode, and a new startup verification timestamp. Confirm historical publication
   records and both environment registries remain available and all GEO mutation
   actions are disabled. Publication remains enabled during this phase, so the
   maintenance window must continue to exclude new DANDI requests. Setting
   `DATA_EXPLORER_PUBLICATION_ENABLED=false` would skip startup database
   verification and hide publication history; it is not this verification mode.
   Confirm collection revision reads and inspection seed reads through the
   paired services without saving metadata or launching a publication.

   ```bash
   docker compose ps data-explorer workflows-backend workflows uploader
   docker compose logs --tail=80 data-explorer workflows-backend uploader
   ```

5. After the image, health, catalog, history, and companion-service checks pass,
   recreate Data Explorer from the base Compose file to restore GEO intake.
   Keep the override until the enabled service is verified.

   ```bash
   docker compose -f docker-compose.yaml up -d --no-deps --force-recreate --wait data-explorer
   ```

   Confirm `/api/config` reports GEO enabled; missing/stale confirmation tokens
   and legacy unpinned packages must still be refused. The source release's
   Docker tests cover these refusal cases without a real FTP push.

   ```bash
   trash .geo-intake-disabled.yaml
   ```

## Dataset follow-up and recovery

Production metadata writes and packaging are separate reviewed actions. Save
the approved post-review metadata through Uploader to create history, then build
a new package through Data Explorer. Compare its spreadsheet, library selection,
counts, pinned sources, and checksums; Hunter reviews that exact package before
authorizing FTP. GEO website submission and GSE recording remain human steps.

Upload receipts prove a previous checked source transfer and remote size; they
are not a server-side checksum or protection against an outside same-size
overwrite. Treat submission folders as worker-managed during transfer. Unproven
files, unfinished intents, changed remote sizes, or unknown effects require
reconciliation/new package; never automatically delete, overwrite, or append.

Rollback keeps GEO disabled using the override. An older application can emit
unbound requests and an older backend can restore an unsafe fallback worker;
neither may re-enable GEO FTP. Preserve all database/S3 evidence, do not downgrade
`0005` after general collection state exists, and do not restore the pre-cutover
archive over newer history. Prefer a forward correction.

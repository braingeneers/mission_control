# Agent Notes for `mission_control/data-lifecycle`

## Scope and ownership

These instructions apply to this directory. Mission Control owns the task
image and policy here; the sibling `workflows` repository owns the Nextflow
source and catalog definitions. The legacy deletion website and standalone
scheduler are retired and must not be restored here or in Compose.

## Working rules

1. Keep code, defaults, policy, workflow pins, and docs aligned.
2. Preserve stage-by-stage compatibility across Stage 0 through Stage 4.
3. Update this README whenever entrypoints, defaults, image workflows,
   artifacts, inventory formats, or operator behavior change.
4. Run `bash -n` for changed shell scripts and `python -m py_compile` for
   changed Python modules before finishing.
5. Bump `VERSION`, publish both `braingeneers/data-lifecycle:vN` and `latest`,
   and synchronize both lifecycle workflows when releasing image changes.

## Runtime contracts

1. Keep the image workdir and task paths at `/data_lifecycle` and
   `/data_lifecycle/src`.
2. Endpoint resolution must remain `NRP_ENDPOINT`, then `ENDPOINT`, then
   `https://s3.braingeneers.gi.ucsc.edu`; stage scripts export both endpoint
   variables to the resolved value.
3. Keep `GLACIER_PROFILE` on unset-only default expansion so an explicitly
   empty value selects the default AWS credential chain.
4. Stage 2 and Stage 3 resolve `DATA_LIFECYCLE_CONFIG_PATH` explicitly and
   default to `src/data-lifecycle.yaml` beside the scripts.
5. The workflow publishes immutable per-run audit bundles without replacing
   the shared inventory prefix and advances latest-state pointers only after
   durable outputs are complete.

## Stage 2 inventory policy

1. Keep listing centered on `rclone`; tune retries, workers, or request shape
   before considering another implementation.
2. Do not add boto3 or AWS CLI fallback listing without strong manually
   verified evidence that rclone cannot handle the failure mode.
3. Keep shard filenames sanitized and hash-suffixed to avoid collisions.

## Stage 3 comparison policy

1. Required config key is `deletion.cold_storage_expire_days`.
2. Before set operations, translate rclone `．` and `．．` to `.` and `..`,
   repair embedded `s3:/` to `s3://`, and strip carriage-return artifacts.
3. Run Python unbuffered and retain the phase/memory heartbeat; a production
   comparison of 12,070,479 rows and 1.96 GB CSV was previously OOM-killed at
   4 GiB after 1h41m with only its initial banner retained.
4. Publish `comparison-summary.json` with distinct eligible-local and
   pending-PUT counts. Validate any upload-fraction guard against `puts.txt`
   before constructing upload clients.

## Stage 4 upload policy

1. Keep the destination `HeadObject` precheck for scientific objects to avoid
   duplicate Glacier uploads from lagging inventories.
2. Retention markers bypass that precheck so newer tiny markers overwrite the
   backup copy; scientific objects are never self-copied.
3. Keep `activity.log` append-only and keyed by canonical bucket/object paths.
   `already_present_skipped` is the durable inventory-lag signal.
4. Recoverable per-file failures do not make the stage exit nonzero after the
   main loop.
5. Preserve smart_open multipart uploads with 64 MiB parts and 1 MiB writes.
6. Exit 44 is reserved for the strict greater-than upload-fraction guard;
   exactly 50 percent is allowed by the production workflow.

Detailed upload experiments are in
`docs/multipart_root_cause_analysis.md`. The successful shape was multipart
with relatively small request bodies; large single-request PutObject uploads
failed across tested client families.

## Retention and report policy

1. Use only zero-byte `DATA_LIFECYCLE_RETENTION` marker LastModified values for
   renewal and `<folder>/NOBACKUP` for reversible exclusion.
2. The current Ceph marker is authoritative. A Glacier marker is only a backup
   copy and must not extend retention after current-marker removal.
3. Keep report presentation independent from deletion execution state. Reports
   describe scheduled deletion dates without an enabled/disabled disclaimer;
   preserve existing machine-readable deletion fields until an explicit
   deletion-execution migration changes their contract.
4. Keep atomic datasets grouped using the latest effective timestamp across
   their scientific objects and current marker.

## AWS inventory inspection

Use the local AWS CLI profile `aws-braingeneers-backups` for Braingeneers
backup inventory buckets. Default AWS credentials may be stale or invalid for
`s3://braingeneers-backups-inventory/`.

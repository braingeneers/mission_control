# Data Lifecycle Workflow Image

This directory owns the image and policy used by the Braingeneers Data
Lifecycle Backup and Data Retention Policy Report workflows. The Nextflow
source and portal definitions remain in the sibling
[`workflows`](https://github.com/braingeneers/workflows/tree/main/workflow-sources)
repository.

The former deletion-review website and standalone scheduler are retired.
Data Explorer now provides the small user-facing storage-protection controls,
and Workflows owns all backup and report execution. Report generation remains
independent from deletion execution.

## Runtime contract

The published image is `braingeneers/data-lifecycle:vN`, where `N` comes from
[`VERSION`](VERSION). Workflows pins an immutable version. Keep these paths
stable because they are workflow parameters:

```text
/data_lifecycle/src
/data_lifecycle/src/data-lifecycle.yaml
```

The active policy is [`src/data-lifecycle.yaml`](src/data-lifecycle.yaml). It
defines backup prefixes, atomic dataset patterns, and scheduled retention
windows. Repository documentation, defaults, tests, and workflow pins must be
updated together when this policy or image behavior changes.

Backup evidence is stored under:

```text
s3://braingeneers/services/data-lifecycle/inventory/
s3://braingeneers/services/data-lifecycle/runs/<workflow-run-id>/
s3://braingeneers/services/data-lifecycle/latest-backup-state.json
```

Reports are stored under:

```text
s3://braingeneers/services/data-lifecycle/cleanup-reports/<workflow-run-id>/
s3://braingeneers/services/data-lifecycle/latest-cleanup-report.json
```

The latest pointers advance only after the corresponding immutable run bundle
is complete.

Each report bundle contains interactive HTML, printable PDF, machine-readable
CSV and JSON, and a bounded Slack-mrkdwn text summary. The workflow only
publishes these artifacts; selecting and delivering an artifact through Slack
or email belongs to the Workflows website.

## Backup stages

The image retains standalone stage entrypoints for local diagnosis, while the
production Nextflow workflow launches the stages as separate Kubernetes tasks:

1. `stage0_prep_environment_vars.sh` resolves runtime defaults.
2. `stage1_prep_inventory_files.sh` downloads the latest AWS inventory.
3. `stage2_generate_nrp_inventory.sh` inventories configured Ceph prefixes with
   parallel `rclone` shards.
4. `stage3_generate_puts_deletes.sh` compares canonicalized inventories and
   produces report and pending-upload artifacts.
5. `stage4_process_puts_deletes.py` uploads missing objects to Glacier with a
   destination `HeadObject` precheck and append-only activity log.

Endpoint resolution remains `NRP_ENDPOINT`, then `ENDPOINT`, then
`https://s3.braingeneers.gi.ucsc.edu`. Stage 2 and Stage 3 resolve
`DATA_LIFECYCLE_CONFIG_PATH`; their default is the policy beside the scripts.
An explicitly empty `GLACIER_PROFILE` selects the default AWS credential chain.

## Retention controls

The current Ceph `LastModified` timestamp on a zero-byte marker is the sole
renewal signal:

```text
<atomic-dataset>/DATA_LIFECYCLE_RETENTION
<file>.DATA_LIFECYCLE_RETENTION
```

`<folder>/NOBACKUP` excludes a prefix from future backups and can be removed to
re-include it. Scientific objects are never self-copied to renew retention.
Markers are copied to Glacier for backup completeness, but a stale Glacier
marker does not extend retention after its current Ceph marker is removed.

## Build, test, and publish

Run image operations from the Mission Control repository root:

```bash
make data-lifecycle-build
make data-lifecycle-test
make data-lifecycle-push
make data-lifecycle-shell
make data-lifecycle-run-local
```

`data-lifecycle-push` publishes both the immutable version from `VERSION` and
`latest`. Bump `VERSION` in the same change as a new release, publish the image,
then update every backup/report workflow image pin and its tests.

The Stage 4 multipart reproduction harness remains available for controlled
development-bucket testing:

```bash
make data-lifecycle-stage4-upload-repro \
  DATA_LIFECYCLE_STAGE4_POC_SOURCE_FILE=/tmp/HET3-6.raw.h5
```

See [`docs/multipart_root_cause_analysis.md`](docs/multipart_root_cause_analysis.md)
before changing upload request shape.

## Operational validation

The backup reprocess-check tooling is under
[`skills/backup-reprocess-check/`](skills/backup-reprocess-check/). It waits for
an AWS inventory, runs the same pinned image twice, and reports duplicate or
steady-state failure patterns. Use the local AWS CLI profile
`aws-braingeneers-backups` when inspecting backup inventory buckets; default
AWS credentials may not be valid for that account.

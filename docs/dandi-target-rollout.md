# One DANDI workflow with an explicit target

The final catalog has `dandi-publication` version **0.5.12**, with `target=sandbox`
or `target=production`. Standalone defaults remain Sandbox; hosted Data Explorer
keeps its Production default and sends the chosen target in both dataset and
collection launch envelopes. Worker `hschweiger15/dandi-publication:0.4.11`,
Secrets, request/result schemas, storage namespaces and database migrations are
unchanged. Existing runs keep their recorded source and launch specification.

| Stage | Workflows backend/frontend | Data Explorer |
| --- | --- | --- |
| Transition | `20261007-a0afdb335df1` | Existing running image |
| Data Explorer switch | Transition images | `20261007-bc0615849651` |
| Final catalog | `20261007-20f6b9acf8bf` | `20261007-bc0615849651` |

The transition backend disables workflow-source synchronization so fetching final
`main` cannot remove the production entry early. Final recreation restores normal
source synchronization. The transition entry has a fixed production target; it
continues accepting the earlier Data Explorer envelopes.

## Operator commands

Run on **braingeneers.gi.ucsc.edu**, from the existing Mission Control checkout.
Confirm this is a clean checkout before updating it. Review the script before
running; it recreates only Workflows and Data Explorer and stops on a failed
image, catalog, or database check.

```bash
git pull --ff-only
bash scripts/deploy-dandi-target.sh
```

Do not run this deployment script on the local workstation. It pulls immutable
images, performs the three ordered stages, verifies running image IDs, checks
both target routes, and verifies historical run reads and the retired Clone
error. It does not create a run or perform a DANDI operation. The Clone probe
only checks the error from a missing catalog entry and has no mutation effect.

The authenticated preflight on October 7, 2026 found Data Explorer already at
`0005_general_dandi_collections`, no DANDI schedules, and no active production-ID
runs among the 23 visible non-archived records. Recheck if rollout is delayed or
another caller is introduced. Known dataset and collection producers are updated;
unidentified callers of the retired ID receive a clear launch failure.

After the script succeeds, open the hosted Workflows catalog and confirm one
DANDI entry with both target choices. Open a historical production run, visit
its tabs, and confirm Clone shows an error while keeping the page readable.
Local browser regression evidence covers retired and changed workflows at
1440px and 390px. API checks and image publication do not establish hosted UI
verification. No upload, unembargo, or DOI publication is part of this rollout.

## Rollback

Restore the transition Workflows pair **before** reverting Data Explorer:

```bash
docker compose -f docker-compose.yaml -f docs/dandi-target-transition.compose.yaml pull workflows-backend workflows
docker compose -f docker-compose.yaml -f docs/dandi-target-transition.compose.yaml up -d --no-deps --force-recreate --wait workflows-backend workflows
```

If Data Explorer also needs rollback, use the exact image captured at the start
of the script (substitute the printed directory below):

```bash
docker compose -f docker-compose.yaml -f /tmp/dandi-target-rollout.DIRECTORY/data-explorer-before.compose.yaml pull data-explorer
docker compose -f docker-compose.yaml -f /tmp/dandi-target-rollout.DIRECTORY/data-explorer-before.compose.yaml up -d --no-deps --force-recreate --wait data-explorer
```

Keep the transition Workflows images until both old and new Data Explorer
launches are no longer needed. Do not roll back database revisions, publication
records, frozen launch requests, immutable S3 evidence, or DANDI state.

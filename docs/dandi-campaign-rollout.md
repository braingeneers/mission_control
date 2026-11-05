# Explicit automatic DANDI campaigns

Pinned releases:

- Data Explorer `20261105-d555fde172b0`, full runtime source
  `d555fde172b0499095ceeed8002ec3c6436ffb70`.
- Paired Workflows backend/frontend `20261105-26e2f36ae8c8`, source
  `26e2f36ae8c8ee6f10e3ce5d954eb2a909645f63`. This includes upstream's already
  accepted SpikeLab workflow commit 69ae82c6; DANDI behavior/dependencies are
  unchanged by that integration.

This release coordinates Data Explorer and the paired Workflows applications.
It adds Data Explorer migrations `0008_dandi_campaign_execution` and
`0009_dandi_continuation`. Startup checks the final head before running its
coordinator. No new worker/catalog, Notification Service, proxy or Secret change
is needed. Existing campaigns remain manual until a researcher explicitly opts
in. Production campaign `24020358-cf64-4ef1-8b2b-0a9b7e9546fc` is not activated by
deployment, and its recovery-only approval does not become continuation consent.

## Operator action

Agents do not SSH or restart production. On `braingeneers.gi.ucsc.edu`, in the
Mission Control checkout, choose an interval without in-flight DANDI launch or
recovery approval. Coordinate new intake and save/verify a `data_explorer` schema
archive using the existing [database backup procedure](../sql-db/README.md).
Keep target gates, approval history and original conflict evidence.

```sh
git pull --ff-only
docker compose pull workflows-backend workflows data-explorer
docker compose up -d --no-deps workflows-backend workflows
# Verify Workflows HTTPS readiness, release identity and capabilities first.
docker compose up -d --no-deps data-explorer
```

The Data Explorer entrypoint applies additive Alembic migrations. A plain restart
does not replace an image. Already admitted workers retain their frozen sources;
normal reconciliation resumes from durable state. No full-stack restart is needed.
Rollback must retain consent/history and the new schema; do not downgrade or
reset state. An old app may reject its schema-head check, so coordinate intake
rather than force an old version to run against a different head.

## Verification and researcher acceptance

Verify Workflows `/readyz`, `/api/admin/system-status.application_build`, and
frontend `/build-info.json` against the published pair. Its deployment verifier
checks these through authenticated HTTPS. `/api/capabilities` must advertise
`dandi_campaign_execution: 1` and `dandi_stop_intent: 1`. Verify Data Explorer
`/healthz.application_build` and `publication_database` for schema `data_explorer`,
head `0009_dandi_continuation`, `verified: true`. Compare pre-update gates and
manual approvals. Publishing images and pins is not hosted activation evidence.

Prepared Sandbox review:
[Two small additions in private Sandbox 218966](https://data-explorer.braingeneers.gi.ucsc.edu/?dandi_instance=sandbox&dandi_collection=collection-fd151492-0856-4c5e-b7e7-bb00c0bce159&dandi_campaign=a64607e4-4fb0-4920-ac20-55f9864c93ca).
It selects two derived NWBs from `2026-09-23-fly-odor-taxis`, totaling 3,859,059
source bytes in two batches limited to 3,000,000 bytes each. The preview records
two additions, three retained assets, no updates or retirements. No uploads were
started. After the new versions are verified, a signed-in researcher must review
and use **Approve and start**. Agents never approve or click for the researcher.
Verify both automatic batches, source/projection provenance, private access,
Valid draft and campaign completion before expanding. Notifications go to that
verified approving researcher; do not send test emails to arbitrary recipients.

Combined recovery remains separately human reviewed and freshly verified. It
freezes exact missing original files and grants one further attempt per unfinished
batch without resetting spent attempts. Pause/Revoke, expired consent or changed
evidence blocks application. Synthetic tests cover failures and drift; do not
manufacture a production failure for acceptance. Recovery-only retains its
historical behavior. Workflows subscriptions name individual checks/verification/
batches; Data Explorer owns whole-campaign milestone email.


## Local acceptance evidence

Data Explorer complete suite: 530 passed (56 optional integration skips), plus
155 selected cases against the exact published runtime image. Browser suite:
118 passed including desktop/mobile, deep links, lost approval responses,
legacy opt-in and combined public consent. Separate disposable PostgreSQL
acceptance: 15 passed; worker/registered-launch/parity contract: 19 passed.
JavaScript checks and this repository's `make test` passed. Workflows trusted
admission/MQTT/run notification contracts passed 66 cases in the resolved release
runtime. Image labels/build records and required staged DANDI recovery runtime
were inspected, with test sources excluded. The final image also validates all
36 production catalog entries. Unrelated upstream catalog integration had one
stale DANDI version assertion (0.7.5 vs approved 0.7.6); the oracle was corrected
and rechecked, preserving the initial failure. No scientific outputs were changed.

Local evidence is recorded in Data Explorer's
`docs/evidence/dandi-campaign-execution-20261105.md` and the ignored execution
handoff. These checks do not substitute for operator deployment verification or
the prepared real Sandbox acceptance described above.

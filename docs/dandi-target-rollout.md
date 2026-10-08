# One DANDI workflow with an explicit target

The final catalog has `dandi-publication` version **0.5.12**, with `target=sandbox`
or `target=production`. Standalone defaults remain Sandbox; hosted Data Explorer
keeps its Production default and sends the chosen target in both dataset and
collection launch envelopes. Worker `hschweiger15/dandi-publication:0.4.11`,
Secrets, request/result schemas, storage namespaces and database migrations are
unchanged. Existing runs keep their recorded source and launch specification.

Mission Control pins Workflows backend/frontend to `20261008-597c7dbf3328` and
Data Explorer to `20261007-bc0615849651`.

## Operator commands

Run on **braingeneers.gi.ucsc.edu**, from the existing Mission Control checkout.
Update the three services together during a brief window when nobody is launching
DANDI publications. Confirm this is a clean checkout before updating it.

```bash
git pull --ff-only
docker compose pull workflows-backend workflows data-explorer
docker compose up -d --no-deps --force-recreate --wait workflows-backend workflows data-explorer
```

These commands pull the published images and recreate only the three services;
`--wait` uses their existing health checks. A plain `docker compose restart` keeps
the existing images. New DANDI launches can fail during the brief mixed-version
window, which is why launches should pause until the update completes.

Afterward, open the hosted Workflows catalog and confirm one
DANDI entry with both target choices. Open a historical production run, visit
its tabs, and confirm Clone shows an error while keeping the page readable.

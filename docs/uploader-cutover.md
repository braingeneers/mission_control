# Uploader cutover — September 25, 2026

The former `uploader-dev` becomes the sole `uploader` service at
`https://uploader.braingeneers.gi.ucsc.edu`, replacing the older uploader.
The published image remains
`braingeneers/braingeneers-data-uploader:20260925-0e6fb4ee4e5f`.

The promoted service retains `PROD=true`, the Workflows Recipe API, AI prefill,
and the existing `replicated` volume. Keep both storage paths unchanged:

- `METADATA_TEMPLATE_DIR=/replicated/uploader-dev/metadata-templates`
- `WHATS_NEW_DIR=/replicated/uploader-dev/whats-new`

These historical directory names preserve presets, announcement content,
enabled/version settings and email-keyed dismissal receipts. No migration or
announcement reset is needed. Recipes and their lab default remain in Workflows.

Data Explorer's metadata-repair URL changes to the main uploader hostname;
recreate Data Explorer to load that environment setting. Its image pin is unchanged.
The existing main-host proxy configuration already supports the promoted image.
No proxy, Workflows, notification-service or database restart is required.
Retained legacy proxy overrides do not advertise the old hostname; it has no
replacement service or redirect.

## Operator commands

Run on `braingeneers.gi.ucsc.edu` from the Mission Control checkout after both
uploader services are stopped and uploads have finished:

```bash
git pull --ff-only
docker compose pull uploader data-explorer
docker container rm uploader-dev
docker compose up -d --no-deps --force-recreate --wait uploader data-explorer
make verify-uploader-deployment SERVICE=uploader
docker compose ps uploader data-explorer
```

The removal targets only the old, explicitly named `uploader-dev` container,
without removing volumes or forcing a running container to stop. Skip that line
if it was already removed. If it is still running, stop it before continuing.
Compose recreates the old `uploader` container with the promoted configuration.
Avoid global orphan removal because other retired containers may be unrelated.

The verifier must confirm the expected image, version and production bucket mode,
plus an anonymous HTTP 401 JSON response from `/api/version`. If verification
fails, inspect `docker compose logs --tail=100 uploader` before proceeding.
Open the main hostname and confirm the existing presets, Recipe choices, and
announcement settings in `/admin`; follow a Data Explorer metadata-repair link
and confirm it uses the main hostname. Existing bookmarks to the dev hostname
need updating, and browser-local preferences may differ between hostnames.

Local `make test` validates the configuration and proxy contracts. Production
cutover is complete only after the operator starts and verifies the services.

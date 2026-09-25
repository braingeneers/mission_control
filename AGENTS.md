# AGENTS.md

## File Operations

- Use `trash` instead of `rm`.

## Service Operations

- Keep Workflows on the explicit `flowforge-nextflow-work-west` workspace claim
  (`rook-cephfs`, 200Gi ReadWriteMany). Provision it before backend recreation;
  preserve the old central claim for historical runs and clone queued Jobs after
  the setting changes. S3 bucket location does not determine the workspace region.
- Workflows snapshots a 30-minute launcher mount timeout only into new runs;
  `LAUNCHER_MOUNT_TIMEOUT_SECONDS=0` disables new timeout decisions after backend
  recreation. Existing cleanup intents still finish, and older runs remain exempt.
- Do not create, update, patch, replace, or delete Kubernetes Secrets. Secret mutations are operator-owned; provide the required instructions and wait for the operator to apply them.
- Do not run production-style `mission_control` services locally unless the user explicitly asks for a local test.
- Services such as `mqtt-job-listener`, `maxwell-dashboard`, and other Docker Compose managed lab services are intended to run on `braingeneers.gi.ucsc.edu`.
- When service restart, pull, recreate, or deployment operations are needed, instruct the user to handle them on the `braingeneers` server instead of running them from a local workstation.
- Unless the user explicitly says otherwise, finish restart-required application changes by
  validating and publishing the affected images, updating and pushing their applicable Compose
  pins, and providing targeted pull/recreate/verify commands. Do not hand off a restart with only
  source-code changes pushed; server-side restarts remain operator-owned.
- Diagnose protected Braingeneers web-service APIs from the local workstation with the standard
  service-account JWT. Prefer the operator-managed
  `~/.ssh/braingeneers_jwt_token.json` when present; it contains `access_token` and
  `expires_at`, must have owner-only permissions, and must never be printed. Otherwise use the
  dynamic token-discovery workflow in
  `skills/mission-control-services-management/references/access-and-auth.md`. In either case,
  treat the embedded JWT `exp` as authoritative. Automatically renew a still-valid
  local token within seven days of expiry, replace the selected file, and notify
  the user afterward; no additional confirmation is needed. For interactive
  renewal, offer `https://service-accounts.braingeneers.gi.ucsc.edu/generate_token`
  directly as well as `python -m braingeneers.iot.authenticate`. The command
  writes the package credential, so it does not by itself update a selected
  `~/.ssh` file. Follow the reference for validation and atomic replacement.
- For semantic Data Explorer checks such as finding paths, confirming recent
  objects, searching, or downloading, use the `data-explorer-cli-access` skill
  and the authenticated HTTPS API. Force a fresh listing when new objects may
  be cached. Use browser control only when the requested evidence is visual or
  interactive, and report API and UI verification separately when both matter.
- Keep uploader `proxy_set_header` directives at vhost scope. Defining any in a
  generated `_location` prevents inheritance of the trusted identity-header
  overrides and downstream `Authorization` stripping from `service-proxy/default`.
- Uploader `_location` files select `@uploader_auth_required` for 401 responses. The
  uploader-only handler returns JSON for `/api/` paths while page navigation retains
  the normal login redirect; do not change the shared policy for other services.
  `service-proxy/test-uploader-auth.sh` exercises both actual uploader overrides with
  an isolated auth/backend stub, including POST bodies and trusted-header inheritance.
  Recreate `service-proxy` after these bind-mounted files change so it reads the new
  files rather than old inodes. Proxy logs include their request ID and the backend
  response's request ID to correlate copied uploader diagnostics.
- Keep `proxy_pass_request_body off` and an empty `Content-Length` header inside
  the `/_oauth2_proxy_auth` location in `service-proxy/default`. Authentication
  subrequests do not receive the original request body; forwarding its length
  makes authenticated POST, PUT, and PATCH requests wait indefinitely.
- Run `make test` after changing Compose or proxy configuration. It validates Compose, authenticated
  uploader proxy inheritance, production/acceptance uploader bucket and image contracts, and the
  stale-container deployment verifier.
- Keep Data Explorer's storage-protection index on `local:/local`, pin its
  immutable date/SHA image, and derive backup status only from the completed
  backup-state pointer plus current Ceph control markers. It must not depend on
  the retired lifecycle website. Do not restore the `data-lifecycle` Compose
  service; its user controls now live in Data Explorer.
- Keep Data Explorer DANDI publication state in its owned `data_explorer`
  PostgreSQL schema, run Alembic before startup, and keep hosted table
  auto-create disabled. Its MQTT and Workflows links are optional integrations,
  not Compose startup dependencies; the DANDI API key belongs only in the
  operator-owned NRP Secret consumed by the publication workflow.
- Pin Data Explorer's NWB materialization namespace to
  `s3://braingeneerscache/data-explorer/dandi/materialized/v1/`; canonical NWBs
  remain untouched and the bucket's 90-day lifecycle owns temporary-copy expiry.
  Sandbox workflow credentials use Secret `dandi-api-key`, data key
  `dandi-sandbox-api-key`. Local-source workflow revisions require a definition
  refresh after the workflows checkout updates, not a service restart.
- Data Explorer metadata-repair links currently target `uploader-dev` for
  acceptance, using `source`, `uuid`, and optional `field` parameters. Keep that
  destination on an editor image supporting deep links; the older main uploader
  image predates the existing-metadata URL handler. This routing choice does not
  change the production bucket used by `uploader-dev`.
- Mission Control owns the Data Lifecycle task image source under
  `data-lifecycle/`, while the catalog and Nextflow source remain in the
  sibling `workflows` repository. Keep the image's `/data_lifecycle/src`
  layout stable and keep workflow image pins synchronized with
  `data-lifecycle/VERSION`.
- Keep `notification-service` as the shared boundary for new outbound Slack and email integrations. Compose peers call it directly; external clients use the standard authenticated proxy and existing service-account JWTs. The application has no producer tokens, database, or MQTT adapter.
- Treat `/secrets/slack-token-braingeneersbot-gi` and `/secrets/notification-service` as operator-owned. Only the notification components read the `ucsc-gi` `braingeneersbot` token and DKIM private key; consumers never receive either credential.
- Keep `notification-mail-relay` outbound-only, unexposed, on the trusted `braingeneers-net`, and fixed to the aligned `notifications@braingeneers.gi.ucsc.edu` sender. Internal services are trusted, but callers should use `notification-service` rather than connect to Postfix directly. Email durability belongs to the persisted Postfix queue.
- Keep report workflows notification-neutral: publish channel-agnostic artifacts, including bounded Slack-ready text when useful, and leave recipient selection and delivery to the Workflows website. Do not add workflow-owned channel ids or completion-notification manifests.
- Keep Workflows independently startable when the optional MQTT launch broker is unavailable. More generally, use Compose `depends_on` only for genuine startup prerequisites, not to document optional integrations; add dependencies later when the runtime contract actually requires them.
- Leave `uploader` without `container_name` so Compose manages production naming. Set
  `uploader-dev` to `container_name: uploader-dev` so its operator log prefix matches the service
  name; keep contract tests for both choices.
- Keep both uploader services at `PROD=true`. Despite its acceptance hostname, `uploader-dev`
  discovers, updates, and uploads datasets in the production `braingeneers` bucket.
- After an operator updates either uploader service, run
  `make verify-uploader-deployment SERVICE=uploader` or
  `make verify-uploader-deployment SERVICE=uploader-dev` on the server. A pull plus restart does not
  replace an existing container; the verifier compares the configured and running image IDs.
  It also requires anonymous public `/api/version` to return HTTP 401 JSON with
  `authentication_required`, `X-Request-ID`, and no `Location`. Keep redirect,
  malformed-response, missing-request-ID, and HTTPS failure coverage: matching app
  images alone do not prove the bind-mounted proxy configuration was refreshed.
- Keep `replicated-volume-backup` additive: it copies new and changed files to
  `s3://braingeneersdev/services/replicated/` and must not delete remote
  objects. Keep its `replicated` mount read-only and exclude dot-prefixed and
  `*.tmp` incomplete files.
- The legacy Data Lifecycle web and scheduler containers are retired. Backup
  and advisory-report execution is owned exclusively by Workflows.
- The uploader-dev Recipe release uses Workflows over `http://workflows-backend:8000`, with
  the default Recipe stored in Workflows and managed through uploader `/admin`. Keep the
  main uploader image and MQTT wiring unchanged until explicitly promoting the candidate.
  Deploy notification-service then Workflows/migration, enable the initial Recipes/default
  through the API, and recreate uploader-dev only outside active uploads. Missing Slack
  `users:read.email` scope leaves email notifications working; scope/token updates are
  operator-owned.

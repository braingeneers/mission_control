# AGENTS.md

## File Operations

- Use `trash` instead of `rm`.

## Service Operations

- Do not create, update, patch, replace, or delete Kubernetes Secrets. Secret mutations are operator-owned; provide the required instructions and wait for the operator to apply them.
- Do not run production-style `mission_control` services locally unless the user explicitly asks for a local test.
- Services such as `mqtt-job-listener`, `maxwell-dashboard`, and other Docker Compose managed lab services are intended to run on `braingeneers.gi.ucsc.edu`.
- When service restart, pull, recreate, or deployment operations are needed, instruct the user to handle them on the `braingeneers` server instead of running them from a local workstation.
- Diagnose protected Braingeneers web-service APIs from the local workstation with the standard
  service-account JWT. Prefer the operator-managed
  `~/.ssh/braingeneers_jwt_token.json` when present; it contains `access_token` and
  `expires_at`, must have owner-only permissions, and must never be printed. Otherwise use the
  dynamic token-discovery workflow in
  `skills/mission-control-services-management/references/access-and-auth.md`. In either case,
  treat the embedded JWT `exp` as authoritative.
- For semantic Data Explorer checks such as finding paths, confirming recent
  objects, searching, or downloading, use the `data-explorer-cli-access` skill
  and the authenticated HTTPS API. Force a fresh listing when new objects may
  be cached. Use browser control only when the requested evidence is visual or
  interactive, and report API and UI verification separately when both matter.
- Keep uploader `proxy_set_header` directives at vhost scope. Defining any in a
  generated `_location` prevents inheritance of the trusted identity-header
  overrides and downstream `Authorization` stripping from `service-proxy/default`.
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
- Keep `replicated-volume-backup` additive: it copies new and changed files to
  `s3://braingeneersdev/services/replicated/` and must not delete remote
  objects. Keep its `replicated` mount read-only and exclude dot-prefixed and
  `*.tmp` incomplete files.
- The legacy Data Lifecycle web and scheduler containers are retired. Backup
  and advisory-report execution is owned exclusively by Workflows.

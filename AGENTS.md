# AGENTS.md

## File Operations

- Use `trash` instead of `rm`.

## Service Operations

- Do not create, update, patch, replace, or delete Kubernetes Secrets. Secret mutations are operator-owned; provide the required instructions and wait for the operator to apply them.
- Do not run production-style `mission_control` services locally unless the user explicitly asks for a local test.
- Services such as `mqtt-job-listener`, `maxwell-dashboard`, and other Docker Compose managed lab services are intended to run on `braingeneers.gi.ucsc.edu`.
- When service restart, pull, recreate, or deployment operations are needed, instruct the user to handle them on the `braingeneers` server instead of running them from a local workstation.
- Diagnose protected Braingeneers web-service APIs from the local workstation with the standard
  service-account JWT and the dynamic token-discovery workflow in
  `skills/mission-control-services-management/references/access-and-auth.md`; never hard-code a
  workstation-specific path or print the token value, and treat the embedded JWT `exp` as
  authoritative.
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
- Keep `notification-gateway` as the only new outbound Slack boundary. Callers use stable channel IDs and producer-specific credentials; they never receive the Slack bot token. Keep its public machine route out of browser auth, strip identity-looking headers, preserve `Authorization`, and retain the 64 KiB body limit.
- Keep notification-gateway MQTT intake disabled until the broker is pinned, authenticated, deny-by-default, and verified with producer-specific request/result topic ACLs. The current allow-all broker cannot authenticate producer identity from a topic name.
- Treat `/secrets/notification-gateway` as operator-owned. Verify the Slack token against the expected `ucsc-gi` team and `braingeneersbot` bot IDs without printing it; never fall back to the legacy Slack bridge credential.
- Keep Workflows notification dispatch disabled until it is deliberately adopted. Do not make Workflows—or any other optional consumer—depend on `notification-gateway` for Compose startup; add dependencies only for genuine hard runtime requirements. Notification failures must never affect consumer startup or primary outcomes.
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
- During the legacy cutover, keep the Data Lifecycle Nextflow schedule paused
  until `replicated-volume-backup` has completed a scheduled sync successfully
  and the old `data-lifecycle-backup` container is stopped.

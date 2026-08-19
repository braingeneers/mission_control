# Outbound Slack Notifications

Use the shared `notification-gateway` whenever a Braingeneers service,
workflow, or device needs to submit a Slack message. Do not add Slack SDKs or
Slack bot credentials to callers unless the user is deliberately building a
separate Slack application with a different trust boundary.

## Boundary And Contract

The gateway is outbound-only. It accepts one versioned request over HTTP and,
after broker hardening, MQTT; commits the request to PostgreSQL; delivers to
Slack with bounded retries; and exposes durable state. It does not mirror Slack
messages to MQTT, accept commands, upload embedded binary data, or translate
legacy Slack bridge topics.

The v1 JSON request contains:

- `schema_version: 1`
- caller-generated UUID `request_id`
- stable Slack `channel_id` (never a channel name or logical route)
- non-empty `text`
- optional Block Kit `blocks`, `thread_ts`, and `reply_broadcast`

Generate `request_id` once and reuse it only when retrying the identical
normalized payload. Publish files and reports to their durable owner first,
then send a link; never base64-encode artifacts into notification requests.

The gateway derives the producer from its transport credential and checks the
producer's explicit channel-ID allowlist. Keep routing policy out of callers and
do not allow arbitrary payload-supplied producer identities.

## Choose A Transport

Prefer internal HTTP for Compose services and workflow backends:

```text
POST http://notification-gateway:8000/v1/notifications
Authorization: Bearer <producer-specific-token>
```

The public machine endpoint is
`https://notifications.braingeneers.gi.ucsc.edu/v1/notifications`. The proxy
preserves bearer authentication, strips identity-looking headers, and does not
perform browser login. Treat `202 Accepted` as durable gateway ownership, not
as proof that Slack delivery is already complete. Query the matching GET route
when the caller needs final delivery state.

Use MQTT only for devices or broker-native services that materially benefit
from it. Requests use QoS 1, non-retained messages on
`notifications/v1/requests/<producer-id>`; state changes use QoS 1,
non-retained messages on
`notifications/v1/results/<producer-id>/<request-id>`. MQTT acknowledgement
means only broker receipt. The gateway's accepted result means PostgreSQL has
committed the request.

Mission Control currently keeps gateway MQTT disabled because the legacy broker
ACL allows broad topic access. Read `mqtt/notification-gateway-security.md` and
do not enable the adapter until authentication and exact producer topic ACLs
are verified.

## Slack Identity And Secrets

The Slack app is `braingeneersbot` in workspace `ucsc-gi`. The gateway reads
only `/secrets/notification-gateway`:

- `slack-bot-token`
- `expected-team-id`
- `expected-bot-id`
- `producers.json`
- `mqtt-username` and `mqtt-password` after broker hardening

Callers read only their dedicated producer token file. Workflows uses
`workflows-http-token`. Kubernetes Secret mutation is operator-owned.

Before launch, verify the new token with Slack `auth.test` and compare its team
and bot IDs to the expected files without logging either token or response
headers. Readiness fails closed on missing or mismatched IDs. Never use a token
from the former Braingeneers workspace or the legacy Slack bridge as fallback.
Resolve `#braingeneers-test` to its stable channel ID and use that channel for
an operator-approved smoke test. The app needs `chat:write` and must be invited
to each allowlisted channel unless operators intentionally grant
`chat:write.public`.

## Workflows

Workflow catalog notifications are opt-in:

```yaml
notifications:
  slack:
    channel_ids: ["C0123456789"]
    events: ["succeeded", "failed"]
```

Supported events are `succeeded`, `failed`, and `cancelled`. Workflows stores a
deterministic UUID request in its own database outbox after the run becomes
terminal, then retries HTTP submission independently. Notification failure must
never change the run status. The migration marks existing terminal runs as
evaluated, and every future terminal run evaluates its notification policy only
once, so deployment and later policy changes cannot replay old runs.

## Deployment And Retirement

The gateway owns PostgreSQL schema `notification_gateway`; an operator must
provision it before the image applies Alembic migrations. The service refuses
to migrate when `current_schema()` is not exactly that schema.

Deploy the gateway alongside the legacy `slack-bridge`. Migrate one producer at
a time, compare accepted/delivered/permanently-failed states, and observe for 30
days. Retire the bridge only after MQTT traffic confirms no old publishers or
inbound Slack consumers remain. Inbound Slack workflows require a separate
future design rather than silently expanding the outbound gateway.

Primary sources:

- Notification gateway repository `README.md`
- Mission Control `README.md`, `docker-compose.yaml`, and
  `service-proxy/notifications.braingeneers.gi.ucsc.edu`
- Wiki `api_data/notification-gateway.md` and `shared/mqtt.md`

# Outbound Slack And Email Notifications

Use `notification-service` when an adopted Braingeneers use case must send Slack
or email. It is a shared outbound API, not a workflow engine, database outbox,
or MQTT adapter.

- [Access boundary](#access-boundary)
- [Slack API](#slack-api)
- [Email API](#email-api)
- [Caller behavior](#caller-behavior)
- [Credentials and mail infrastructure](#credentials-and-mail-infrastructure)
- [Acceptance and troubleshooting](#acceptance-and-troubleshooting)

Do not add a speculative notification integration, distribute provider
credentials, or let notification failure replace a caller's primary result.

## Access Boundary

Compose peers on `braingeneers-net` use trusted internal HTTP:

```text
http://notification-service:8000
```

External clients use:

```text
https://notifications.braingeneers.gi.ucsc.edu
```

The external route uses standard private-web authentication. `oauth2-proxy`
accepts a browser session or standard Braingeneers service-account JWT and nginx
strips `Authorization` before forwarding. The application has no second bearer
scheme. For scripts, follow `access-and-auth.md`; a `302` means the proxy did
not accept the JWT.

Consumers call `notification-service`, never Postfix directly. They do not
mount the Slack token or DKIM key.

## Slack API

`POST /v1/slack` accepts JSON with exactly one destination:

```json
{
  "channel_id": "C0123456789",
  "text": "Analysis completed",
  "blocks": null,
  "thread_ts": null
}
```

Use `user_id` instead of `channel_id` for a direct message. Requirements:

- stable Slack IDs, never display names;
- required `text`, at most 4,000 characters;
- optional `blocks`, at most 50 Block Kit objects;
- optional `thread_ts` for an existing thread.

`GET /v1/slack/destinations` returns non-bot users and joined channels as
friendly picker entries:

```json
{"destinations":[{"type":"channel","id":"C0123456789","label":"#results"}]}
```

The directory is a convenience, not an authorization or availability
guarantee. Retain manual stable-ID entry and do not block unrelated email setup
when the directory is unavailable.

Success is synchronous:

```json
{"status":"delivered","channel_id":"C0123456789","ts":"1750000000.000001"}
```

The service does not store idempotency keys or retry Slack. Retrying a definite
failure is reasonable; automatically replaying an ambiguous timeout can create
a duplicate.

Internal example:

```bash
curl --fail \
  -H 'Content-Type: application/json' \
  -d '{"channel_id":"C0123456789","text":"Analysis completed"}' \
  http://notification-service:8000/v1/slack
```

For an operator-approved production smoke test, use stable channel ID
`C0BQXR5NQ5D` (`#braingeneers-test`). The bot must be invited to a private target
channel.

Required directory/direct-message scopes include `users:read`, `channels:read`,
`groups:read`, and `im:write` in addition to posting scopes. Scope changes
require reinstalling the Slack app before the mounted token gains them.

## Email API

`POST /v1/email` uses `multipart/form-data`:

- repeat required `to` for 1–25 recipients;
- required `subject` and plain-text `text`;
- optional `html`, `reply_to`, and `from_name`;
- repeat `attachments` for at most 10 files totaling at most 10 MiB;
- no Cc, Bcc, or remote attachment URLs.

The envelope and header sender are fixed to
`notifications@braingeneers.gi.ucsc.edu`.

```bash
curl --fail \
  -F to=researcher@ucsc.edu \
  -F subject='Analysis completed' \
  -F text='The analysis completed successfully.' \
  -F attachments=@results.pdf \
  http://notification-service:8000/v1/email
```

The external proxy limit is 12 MiB, leaving multipart overhead above the
application's 10 MiB attachment limit.

Success is `202`:

```json
{"status":"queued","message_id":"<generated@braingeneers.gi.ucsc.edu>"}
```

Queued means Postfix accepted responsibility, not that the recipient received
the message. There is no delivery-status or bounce API. Postfix retries
temporary failures and persists its queue under
`/local/notification-service/postfix`.

## Caller Behavior

Expected errors:

- `400`: invalid request, address, field, or Slack destination;
- `413`: attachment limit exceeded;
- `502`: provider permanently rejected the request;
- `503`: channel unconfigured, mail relay unavailable, or temporary provider
  failure.

Notification failure must not roll back or replace the caller's primary result.
Choose retries, an outbox, or stronger idempotency only for an adopted use case
that needs those semantics. Do not add a platform-wide database, producer token,
or Compose dependency merely to document an optional integration.

## Credentials And Mail Infrastructure

Operator-owned credentials:

- Slack Secret `slack-token-braingeneersbot-gi`, key of the same name, for
  `braingeneersbot` in `ucsc-gi`.
- Mail Secret `notification-service`, key `dkim-private-key`, for selector
  `notifications` and domain `braingeneers.gi.ucsc.edu`.

Only notification components read these files. Secret creation and replacement
remain operator-owned. A missing Slack token disables only `/v1/slack`; the mail
relay waits for its DKIM key rather than sending unsigned mail.

`notification-mail-relay` is outbound-only, unexposed, on
`braingeneers-net`, and has no inbox, IMAP, webmail, or MX requirement. Its
identity must remain aligned:

- A and PTR identify `braingeneers.gi.ucsc.edu` / `128.114.198.51`;
- SMTP HELO is `braingeneers.gi.ucsc.edu`;
- SPF authorizes that address;
- DKIM uses `notifications._domainkey.braingeneers.gi.ucsc.edu`;
- DMARC exists at `_dmarc.braingeneers.gi.ucsc.edu`.

Before first deployment or after network changes, an operator must verify
outbound TCP 25. If institutional policy blocks it, choose an approved relay
rather than bypassing policy.

## Acceptance And Troubleshooting

Production acceptance requires operator approval for one Slack message to the
test channel and one email to a controlled recipient. Slack must return
`200 delivered`; email must return `202 queued`, arrive, and show SPF, DKIM, and
DMARC pass results.

- Slack `503`: have the operator confirm the mounted token file exists, refresh
  `secret-fetcher` if needed, and recreate only the API.
- Slack `502`: verify stable ID, bot membership, and relevant Slack scopes.
- External `302`: validate the bearer header and embedded JWT expiry through
  `access-and-auth.md`.
- Email `503`: inspect both notification containers and confirm the DKIM file
  exists without printing it.
- Email remains queued: inspect `postqueue -p` and relay logs for DNS, TLS, or
  recipient-MX errors; do not flush or delete mail without understanding it.
- DKIM or deliverability failure: verify A/PTR, HELO, SPF, DKIM, DMARC, and TLS
  before changing application behavior.

Primary sources are the notification-service README, Mission Control Compose
and proxy files, and wiki page `api_data/notification-service.md`.

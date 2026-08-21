# Outbound Slack And Email Notifications

Use `notification-service` when a concrete Braingeneers service, workflow, or
device needs to send Slack messages or email. It is a small shared outbound
boundary, not a workflow engine: Slack is synchronous and email durability is
provided by Postfix's normal queue.

Do not give callers the Slack bot token or DKIM key. Do not add a Compose
dependency, catalog field, database outbox, or other consumer integration until
that consumer has an adopted notification requirement.

## Access Boundary

Compose peers on `braingeneers-net` use trusted internal HTTP with no
application bearer token:

```text
http://notification-service:8000
```

External clients use:

```text
https://notifications.braingeneers.gi.ucsc.edu
```

That hostname includes `service-proxy/default`. The existing `oauth2-proxy`
validates a normal browser session or Braingeneers service-account JWT, and
nginx removes `Authorization` before forwarding. The application must not add a
second token scheme. For scripts, read `access-and-auth.md`, dynamically locate
and validate the existing JWT, then send it as `Authorization: Bearer` without
printing it. A `302` to the auth service means the proxy rejected or did not
receive the JWT.

## Slack Contract

`POST /v1/slack` uses JSON:

```json
{
  "channel_id": "C0123456789",
  "text": "Analysis completed",
  "blocks": null,
  "thread_ts": null
}
```

- `channel_id` is a stable Slack channel, group, or DM ID, never a display name.
- `text` is required and limited to 4,000 characters.
- `blocks` may contain up to 50 caller-supplied Block Kit objects.
- `thread_ts` optionally posts in an existing thread.

Success is synchronous:

```json
{"status":"delivered","channel_id":"C0123456789","ts":"1750000000.000001"}
```

The service does not store an idempotency key or retry Slack. The caller may
retry a definite failure; retrying after an uncertain timeout can duplicate a
message.

Internal curl:

```bash
curl --fail \
  -H 'Content-Type: application/json' \
  -d '{"channel_id":"C0123456789","text":"Analysis completed"}' \
  http://notification-service:8000/v1/slack
```

Internal Python:

```python
import httpx

response = httpx.post(
    "http://notification-service:8000/v1/slack",
    json={"channel_id": "C0123456789", "text": "Analysis completed"},
    timeout=30,
)
response.raise_for_status()
```

For an external call, first load `bearer_token` using the dynamic workflow in
`access-and-auth.md`, then use the same payload:

```bash
curl --fail --location --max-redirs 0 \
  -H "Authorization: Bearer ${bearer_token}" \
  -H 'Content-Type: application/json' \
  -d '{"channel_id":"C0123456789","text":"Analysis completed"}' \
  https://notifications.braingeneers.gi.ucsc.edu/v1/slack
unset bearer_token
```

Use stable channel ID `C0BQXR5NQ5D` for operator-approved smoke tests in
`#braingeneers-test`. `braingeneersbot` must be invited to a private target
channel unless its Slack scopes deliberately allow otherwise.

## Email Contract

`POST /v1/email` uses `multipart/form-data` for both messages with and without
attachments:

- Repeat required `to` for 1–25 recipients. Cc and Bcc are not supported.
- `subject` and plain-text `text` are required.
- `html`, `reply_to`, and `from_name` are optional.
- Repeat `attachments` for up to 10 uploaded files totaling at most 10 MiB.
- Remote attachment URLs are not accepted.
- The envelope and header sender are fixed to
  `notifications@braingeneers.gi.ucsc.edu`.

Internal curl:

```bash
curl --fail \
  -F to=researcher@ucsc.edu \
  -F to=collaborator@example.org \
  -F subject='Analysis completed' \
  -F text='The analysis completed successfully.' \
  -F html='<p>The analysis completed <strong>successfully</strong>.</p>' \
  -F reply_to=researcher@ucsc.edu \
  -F attachments=@results.pdf \
  http://notification-service:8000/v1/email
```

Internal Python:

```python
from pathlib import Path
import httpx

with Path("results.pdf").open("rb") as attachment:
    response = httpx.post(
        "http://notification-service:8000/v1/email",
        data=[
            ("to", "researcher@ucsc.edu"),
            ("subject", "Analysis completed"),
            ("text", "The analysis completed successfully."),
            ("html", "<p>The analysis completed <strong>successfully</strong>.</p>"),
        ],
        files={"attachments": ("results.pdf", attachment, "application/pdf")},
        timeout=45,
    )
response.raise_for_status()
```

For external curl, use the same multipart fields and add the dynamically loaded
`Authorization: Bearer ${bearer_token}` header. The proxy limit is 12 MiB; the
application's raw attachment limit is 10 MiB, leaving room for multipart
overhead.

Email success is `202`:

```json
{"status":"queued","message_id":"<generated@braingeneers.gi.ucsc.edu>"}
```

Queued means Postfix accepted responsibility, not that the recipient received
the message. There is no delivery-status or bounce API. Postfix retries
temporary SMTP failures and retains its queue under
`/local/notification-service/postfix` across container recreation.

## Errors And Caller Behavior

- `400`: invalid request, address, channel ID, or field.
- `413`: email attachments exceed the count or combined-size limit.
- `502`: provider permanently rejected the request.
- `503`: Slack is unconfigured, the mail relay is unavailable, or a provider
  reported a temporary failure.

Notification failure must not roll back or replace a caller's primary result.
Choose caller-side retry or an outbox only when that concrete use case requires
durability; do not make it a platform-wide default.

## Secrets, Postfix, And DNS

The operator-owned Kubernetes credentials are:

- Secret `slack-token-braingeneersbot-gi`, key
  `slack-token-braingeneersbot-gi`: `braingeneersbot` in workspace `ucsc-gi`.
  Mission Control reads it from
  `/secrets/slack-token-braingeneersbot-gi/slack-token-braingeneersbot-gi`.
- Secret `notification-service`, key `dkim-private-key`: a 2048-bit private key
  for selector `notifications` and domain `braingeneers.gi.ucsc.edu`.

Kubernetes Secret creation and replacement are operator-owned. The API remains
healthy without the Slack token and returns `503` only from `/v1/slack`. The
mail relay waits for its DKIM key instead of sending unsigned mail.

The outbound identity is:

- A: `braingeneers.gi.ucsc.edu` → `128.114.198.51`
- PTR: `128.114.198.51` → `braingeneers.gi.ucsc.edu`
- SMTP HELO: `braingeneers.gi.ucsc.edu`
- SPF at `braingeneers.gi.ucsc.edu`:
  `v=spf1 ip4:128.114.198.51 -all`
- DKIM at `notifications._domainkey.braingeneers.gi.ucsc.edu`, containing the
  public key matching the operator-owned private key
- DMARC at `_dmarc.braingeneers.gi.ucsc.edu`: `v=DMARC1; p=none`

The relay is outbound-only and has no published SMTP port, inboxes, IMAP, or
webmail. It does not need an MX record. Delayed bounce ingestion is out of scope.
It shares the trusted `braingeneers-net` with other Mission Control services;
`notification-service` remains the supported caller interface, while the relay
uses Docker subnet trust and does not add separate SMTP credentials or network
topology.
Before initial deployment or after network changes, have the operator verify
outbound TCP 25 from the server. If institutional filtering blocks it, stop and
choose an approved institutional or hosted relay rather than bypassing policy.
Verify the public identity without recording the rotatable DKIM key:

```bash
dig +noall +answer A braingeneers.gi.ucsc.edu
dig +noall +answer -x 128.114.198.51
dig +noall +answer TXT braingeneers.gi.ucsc.edu
dig +noall +answer TXT notifications._domainkey.braingeneers.gi.ucsc.edu
dig +noall +answer TXT _dmarc.braingeneers.gi.ucsc.edu
```

For production acceptance, send one operator-approved message to
`C0BQXR5NQ5D` and one email to a controlled recipient. Slack must return
`200 delivered`. Email must return `202 queued`, arrive, and show `spf=pass`,
`dkim=pass`, and `dmarc=pass` in the received `Authentication-Results` header.

## Troubleshooting

- Slack `503`: confirm
  `/secrets/slack-token-braingeneersbot-gi/slack-token-braingeneersbot-gi`
  exists, then recreate only the API after `secret-fetcher` refreshes.
- Slack `502`: verify the stable channel ID, bot membership, and Slack app scope.
- External `302`: follow `access-and-auth.md`, check the embedded JWT `exp`, and
  confirm the bearer header was sent. Never print the token.
- Email `503`: inspect both notification containers; confirm the DKIM key exists
  and the relay is healthy.
- Email remains queued: have the operator run `postqueue -p` inside
  `notification-mail-relay` and inspect its logs for DNS, TLS, or recipient MX
  errors. Do not flush or delete queued mail without understanding the failure.
- DKIM failure: verify the public selector record matches the operator-held
  private key and that the From domain remains fixed and aligned.
- Gmail spam or rejection: verify A/PTR, SPF, DKIM, DMARC, and TLS before
  changing application behavior.

The legacy MQTT↔Slack `slack-bridge` remains separate for existing MQTT
publishers and inbound Slack consumers. New direct senders use
`notification-service`; there is no scheduled bridge retirement.

Primary sources:

- Notification-service repository `README.md`
- Mission Control `README.md`, `docker-compose.yaml`, and
  `service-proxy/notifications.braingeneers.gi.ucsc.edu`
- Wiki `api_data/notification-service.md` and `shared/mqtt.md`

# Operations

Use this reference for day-two deployment, status checks, production
verification, and troubleshooting. Read `access-and-auth.md` instead for local
HTTPS API diagnosis.

## Operator Boundary

Never SSH to or execute commands on `braingeneers.gi.ucsc.edu`. For host and
service-management actions:

1. For routine updates, briefly ask the operator to restart/update the affected
   services and confirm that images are published and Compose pins are pushed.
   Use the existing update procedure; give the smallest exact command sequence
   directly in chat when needed or requested.
2. Name the host and working repository when context could be ambiguous.
3. State the expected evidence and any stopping condition.
4. Wait for the operator's output before diagnosing the next step or claiming
   success.

Do not turn a diagnostic request into a restart, pull, recreate, migration, or
notification without explicit authorization.

Workflow catalog reload is an authorized application/UI action rather than a
host operation or backend service restart. Agents may use **Reload definitions**
at `/ops/workflows` whenever useful without confirmation or operator handoff.
When the browser is unavailable, use its authenticated
`POST /api/admin/workflows/reload` action, then verify definitions and versions
with `GET /api/admin/workflows`. Reload published workflow changes yourself
before handing off any required application service restart.

Do not create a rollout document for routine updates. Add extra steps only for
concrete deployment dependencies or manual migrations, explaining the reason in
chat. Create a separate document only when requested or when the required
exceptional procedure is too complex for a short handoff.

## Targeted Service Operations

When commands are needed, prefer targeted operations from the server's Mission
Control checkout:

```bash
git pull --ff-only
docker compose pull SERVICE
docker compose up -d --no-deps --force-recreate SERVICE
docker compose ps SERVICE
docker compose logs --tail=200 SERVICE
```

Use `--pull always` when the intended tag may have moved. A pull or restart by
itself does not guarantee that an existing container was replaced. Use a
service-specific deployment verifier when the repository provides one.

For restart-required application changes, finish validation, image publication
and applicable Compose pin updates before handoff. State what is ready and what
still needs the operator. Add ordering, backups or checkpoints only when actual
deployment dependencies or manual migrations require them, and explain their
purpose.

Avoid `docker compose down` and whole-stack restarts during routine work. Proxy
changes may require targeted proxy recreation in addition to the application.

## Verification By Route

- **Private web:** HTTPS route, authentication behavior, backend port, expected
  identity fields when used, read-only API response, and relevant logs.
- **Public web:** anonymous reachability only on intended paths and no trusted
  identity assumptions.
- **Machine API:** backend bearer validation, denial without credentials,
  preserved `Authorization`, and cleared identity headers.
- **Headless:** required TCP/UDP reachability, protocol authentication, logs,
  and persistent-state or credential behavior.
- **MCP:** protected-resource metadata, issuer/audience validation, IAM deny by
  default, and an explicitly granted request.
- **Scheduled or backup service:** current container health, most recent
  attempt, most recent success, schedule continuity, destination evidence, and
  object-level confirmation when logs only show an exit status.

Distinguish evidence carefully: source inspection proves configuration, logs
prove observed execution, a health check proves the service's defined health
contract, and an API or destination listing proves resulting data.

## Change Gates

- Compose or proxy change: run `make test` locally.
- Custom image change: run its owning build and smoke/contract tests before
  publishing.
- Production rollout: pull and recreate only the changed service, then inspect
  status and logs.
- Browser UI change: verify the deployed route as well as local behavior.
- Secret-dependent change: have the operator confirm the expected mounted file
  exists without printing it; never mutate the Kubernetes Secret.

## Troubleshooting Order

Work from the boundary inward:

1. Confirm the configured image, networks, ports/expose, volumes, dependencies,
   and proxy mounts.
2. Confirm the running container and image match the intended deployment.
3. Check service health and bounded recent logs.
4. Check the edge route and authentication contract.
5. Use a read-only application API or protocol client to verify behavior.
6. Verify destination state when success depends on an external store or
   provider.

Common causes:

- Route missing: wrong host/port, service absent from `braingeneers-net`, or
  proxy override not mounted/reloaded.
- Authenticated request body hangs: auth subrequest forwards a non-empty
  `Content-Length`; read `service-routing.md`.
- Backend misses auth or identity: route classification or nginx header
  inheritance is wrong.
- Secret file missing: wrong secret/key path or stale `secret-fetcher`; read
  `secrets.md` and hand mutation or refresh work to the operator.
- Image appears unchanged: tag was not pulled or the container was not
  recreated.
- Successful sync has no expected data: inspect destination objects and source
  eligibility rather than treating exit code zero as content proof.

## Escalation

Escalate missing GI server, GitHub, NRP namespace, registry, Auth0/CILogon,
Keycloak, MCP audience, DNS, or secret-administration access. Do not work around
an ownership or authorization boundary.

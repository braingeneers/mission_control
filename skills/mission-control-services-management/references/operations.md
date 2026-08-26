# Operations

Use this reference for day-two deployment, status checks, production
verification, and troubleshooting. Read `access-and-auth.md` instead for local
HTTPS API diagnosis.

## Operator Boundary

Never SSH to or execute commands on `braingeneers.gi.ucsc.edu`. For every
server-side action:

1. Give the user the smallest exact command sequence.
2. Name the host and working repository when context could be ambiguous.
3. State the expected evidence and any stopping condition.
4. Wait for the operator's output before diagnosing the next step or claiming
   success.

Do not turn a diagnostic request into a restart, pull, recreate, migration, or
notification without explicit authorization.

## Targeted Service Operations

Prefer one-service operations:

```bash
docker compose pull SERVICE
docker compose up -d --force-recreate SERVICE
docker compose ps SERVICE
docker compose logs --tail=200 SERVICE
```

Use `--pull always` when the intended tag may have moved. A pull or restart by
itself does not guarantee that an existing container was replaced. Use a
service-specific deployment verifier when the repository provides one.

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

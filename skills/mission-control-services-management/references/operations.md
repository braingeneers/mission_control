# Operations

Use this reference for day-two service management and troubleshooting.

## Normal Service Operations

Prefer targeted operations:

- Pull one service image.
- Recreate one service.
- Inspect logs for one service.
- Check status for the affected services.

Avoid `docker compose down` for routine work. Whole-stack operations are for reboot recovery or planned broad maintenance.

Useful local source: `README.md`.

## Deployment Review Checklist

Before proposing or applying changes, check:

- Service branch is clear: private web, public web, headless, or MCP.
- Image is published to a registry or there is an explicit exception.
- Custom-image service has a repeatable `Makefile` or equivalent build notes.
- Compose service has correct `image`, ports or expose, env vars, volumes, `depends_on`, and network settings.
- Secrets are mounted through `/secrets`, not baked into images.
- Proxy overrides have matching bind mounts.
- Headless services do not accidentally receive web proxy settings.
- MCP services preserve `Authorization` and do backend token validation.

## Verification

Choose verification by service branch:

- Private web: confirm HTTPS route, browser auth, backend port, logs, and expected user identity headers if used.
- Public web: confirm route is reachable without browser login and only intended paths are public.
- Headless: confirm direct TCP or UDP ports, client auth, logs, and any persistent storage or secret-backed credentials.
- MCP: confirm health, protected-resource metadata, bearer-token preservation, IAM denial by default, and allowed access for a granted principal.

## Troubleshooting

Access problems:

- Missing GI server login: direct user to the wiki permissions page and cluster-admin request.
- Missing GitHub access: direct user to the lab Slack access workflow.
- Missing NRP namespace access: direct user to the wiki onboarding or PRP access workflow.
- Missing `kubelogin`: distinguish interactive user kubeconfig setup from the service-account kubeconfig used on the server.

Image problems:

- Image not found: wrong registry path or tag.
- Private image cannot pull: missing registry auth on the server.
- Rebuild fails after package changes: use a previously published image or fix the build in the service repo and push a new tag.

Proxy problems:

- Host does not route: missing `VIRTUAL_HOST`, wrong `VIRTUAL_PORT`, service not on `braingeneers-net`, or proxy not recreated.
- Override ignored: missing bind mount under the `service-proxy` service.
- Backend does not receive `Authorization`: default proxy strips it; use MCP-specific override only when backend is responsible for token validation.

Secret problems:

- Secret file missing: verify Kubernetes secret name and key, then refresh `secret-fetcher`.
- Service starts before secrets: missing `depends_on` condition.
- Runtime token stale: verify `service-account-jwt-token-refresh` and use `braingeneers-jwt-service-account-token`.

## Escalation

Escalate instead of guessing when the task requires:

- Kubernetes namespace administration.
- Auth0, CILogon, Keycloak, or MCP audience administration.
- Shared credential rotation.
- DNS changes outside wildcard `*.braingeneers.gi.ucsc.edu` routing.
- Registry permission changes.

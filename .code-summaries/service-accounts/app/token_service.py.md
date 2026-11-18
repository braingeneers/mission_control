# token_service.py

**Path:** `service-accounts/app/token_service.py`
**Module:** `service-accounts.app.token_service`
**Feature Area:** `service-accounts`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Flask microservice providing HTTP endpoints (`/token`, `/healthz`) to mint long-lived Auth0 service account JWT tokens for automated jobs and machine-to-machine integrations.

## Connections
- **Shared data:** Authenticates against Auth0 identity service.
- **Shared data:** Used by automated workflows and CLI clients needing machine access tokens.

## Dependencies
- `flask.Flask` — external or unresolved local import; source import evidence.
- `flask.jsonify` — external or unresolved local import; source import evidence.
- `flask.request` — external or unresolved local import; source import evidence.
- `requests` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
### `_utcnow() -> datetime`
> unclear — see source
> **Called by:** service-accounts/app/token_service.py:62 (named-call hint). **Side effects:** unclear — see source.
**Source:** `service-accounts/app/token_service.py:31`
### `_format_utc(dt: datetime) -> str`
> unclear — see source
> **Called by:** service-accounts/app/token_service.py:80 (named-call hint). **Side effects:** unclear — see source.
**Source:** `service-accounts/app/token_service.py:35`
### `_parse_requested_days() -> int`
> unclear — see source
> **Called by:** service-accounts/app/token_service.py:87 (named-call hint). **Side effects:** unclear — see source.
**Source:** `service-accounts/app/token_service.py:39`
### `_json_response(payload: dict[str, Any], *, status: int=200, cacheable: bool=False)`
> unclear — see source
> **Called by:** service-accounts/app/token_service.py:89 (named-call hint); service-accounts/app/token_service.py:93 (named-call hint); service-accounts/app/token_service.py:98 (named-call hint). **Side effects:** unclear — see source.
**Source:** `service-accounts/app/token_service.py:48`
### `_service_account_token(days: int) -> dict[str, Any]`
> Makes HTTP POST to Auth0 OAuth endpoint requesting client_credentials access token.
> **Called by:** service-accounts/app/token_service.py:87 (named-call hint). **Side effects:** unclear — see source.
**Source:** `service-accounts/app/token_service.py:61`
### `generate_token()`
> Route handler for `/token` (GET/POST) parsing expiration days and returning JWT payload.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `service-accounts/app/token_service.py:85`
### `healthz()`
> Health check route returning 200 OK.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `service-accounts/app/token_service.py:97`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env `AUTH0_CLIENT_ID`: OAuth client ID for Auth0 tenant. |
| Env `AUTH0_CLIENT_SECRET`: OAuth client secret. |
| Env `AUTH0_DOMAIN`: Auth0 domain (default: `dev-jkxyxuthob0qc1nw.us.auth0.com`). |
| Env `AUTH0_API_AUDIENCE`: Target API audience URI (default: `https://auth.braingeneers.gi.ucsc.edu/`). |
| Env `DEFAULT_EXPIRATION_DAYS`: Default token lifetime in days (default: 120). |

## Data Shapes
- Input: JSON POST `{"days": 90}` or query param `?days=90`.
- Output: JSON response `{"access_token": "...", "expires_in": 7776000, "expires_at": "...", "token_type": "Bearer"}`.

## Notes
- Invokes Auth0 OAuth `/oauth/token` using `client_credentials` grant type.
- Provides `/healthz` probe for Kubernetes liveness and readiness.

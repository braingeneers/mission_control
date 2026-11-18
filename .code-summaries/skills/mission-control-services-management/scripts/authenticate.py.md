# authenticate.py

**Path:** `skills/mission-control-services-management/scripts/authenticate.py`
**Module:** `skills.mission-control-services-management.scripts.authenticate`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
CLI utility for managing local Braingeneers service credentials, validating JWT token structure and expiration, opening browser sign-in if needed, and saving tokens with restrictive file permissions.

## Connections
- **Shared data:** Interacts with `service-accounts/app/token_service.py` to mint tokens.
- **Shared data:** Used by all CLI tools requiring Braingeneers IoT API authorization.

## Dependencies
None

## Classes
### SignInError(Exception)
> Exception raised on authentication failure or expired credentials.
**Source:** `skills/mission-control-services-management/scripts/authenticate.py:27`
**Kind:** class. **Instantiated by:** skills/mission-control-services-management/scripts/authenticate.py:102 (named-call hint); skills/mission-control-services-management/scripts/authenticate.py:104 (named-call hint); skills/mission-control-services-management/scripts/authenticate.py:115 (named-call hint); skills/mission-control-services-management/scripts/authenticate.py:163 (named-call hint); skills/mission-control-services-management/scripts/authenticate.py:187 (named-call hint); skills/mission-control-services-management/scripts/authenticate.py:68 (named-call hint); skills/mission-control-services-management/scripts/authenticate.py:70 (named-call hint); skills/mission-control-services-management/scripts/authenticate.py:78 (named-call hint); skills/mission-control-services-management/scripts/authenticate.py:85 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None

## Functions
### `select_path(explicit=None)`
> Resolves default token path in `~/.ssh/` or inside `braingeneers.iot` package.
> **Called by:** skills/mission-control-services-management/scripts/authenticate.py:176 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/mission-control-services-management/scripts/authenticate.py:31`
### `validate_response(raw)`
> unclear — see source
> **Called by:** skills/mission-control-services-management/scripts/authenticate.py:105 (named-call hint); skills/mission-control-services-management/scripts/authenticate.py:83 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/mission-control-services-management/scripts/authenticate.py:48`
### `load_response(path)`
> unclear — see source
> **Called by:** skills/mission-control-services-management/scripts/authenticate.py:105 (named-call hint); skills/mission-control-services-management/scripts/authenticate.py:184 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/mission-control-services-management/scripts/authenticate.py:74`
### `save_response(path, raw)`
> Writes token JSON atomically with chmod 0600 permissions.
> **Called by:** skills/mission-control-services-management/scripts/authenticate.py:203 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/mission-control-services-management/scripts/authenticate.py:82`
### `check_response(path)`
> Validates JSON structure and verifies JWT expiration timestamp against current UTC time.
> **Called by:** skills/mission-control-services-management/scripts/authenticate.py:181 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/mission-control-services-management/scripts/authenticate.py:100`
### `read_private_response(before_read)`
> Read multiline paste without terminal echo, including on agent PTYs.
> **Called by:** skills/mission-control-services-management/scripts/authenticate.py:201 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/mission-control-services-management/scripts/authenticate.py:108`
### `collect_response(read_char)`
> unclear — see source
> **Called by:** skills/mission-control-services-management/scripts/authenticate.py:126 (named-call hint); skills/mission-control-services-management/scripts/authenticate.py:140 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/mission-control-services-management/scripts/authenticate.py:145`
### `main(argv=None)`
> CLI driver executing sign-in check or browser authentication prompt.
> **Called by:** skills/mission-control-services-management/scripts/authenticate.py:222 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/mission-control-services-management/scripts/authenticate.py:166`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Default token path: `~/.ssh/braingeneers_jwt_token.json` |
| `LOGIN_URL`: `https://service-accounts.braingeneers.gi.ucsc.edu/generate_token` |
| `--path PATH`: Custom credential file location. |
| `--check`: Non-interactive exit-code check for valid, unexpired token. |
| `--force`: Re-authenticate even if existing token is valid. |

## Data Shapes
- Credential file JSON: `{"access_token": "<JWT>", "expires_at": "<ISO-8601>", "token_type": "Bearer"}`.

## Notes
- Standard library only; never prints or leaks token contents in error messages or logs.
- Enforces POSIX file permissions (0600) when saving token JSON.

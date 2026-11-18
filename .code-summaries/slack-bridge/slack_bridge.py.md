# slack_bridge.py

**Path:** `slack-bridge/slack_bridge.py`
**Module:** `slack-bridge.slack_bridge`
**Feature Area:** `slack-bridge`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Flask and MQTT bidirectional bridge microservice routing telemetry alerts and hardware messages from Braingeneers MQTT message broker to Slack channels, and forwarding Slack interactive events back to MQTT.

## Connections
- **Shared data:** Connects Braingeneers `MessageBroker` with Slack WebClient API.
- **Shared data:** Exposes `/slack/events` webhook endpoint and `/healthz` probe.

## Dependencies
- `braingeneers.iot.MessageBroker` — external or unresolved local import; source import evidence.
- `flask` — external or unresolved local import; source import evidence.
- `slack_sdk.WebClient` — external or unresolved local import; source import evidence.
- `slack_sdk.errors.SlackApiError` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
### `safe_publish(topic: str, payload: dict) -> None`
> Publishes messages to MQTT broker with error catching.
> **Called by:** slack-bridge/slack_bridge.py:200 (named-call hint); slack-bridge/slack_bridge.py:209 (named-call hint); slack-bridge/slack_bridge.py:286 (named-call hint); slack-bridge/slack_bridge.py:301 (named-call hint). **Side effects:** unclear — see source.
**Source:** `slack-bridge/slack_bridge.py:52`
### `get_channel_name(channel_id: str) -> Optional[str]`
> Resolves Slack channel ID to human-readable channel name.
> **Called by:** slack-bridge/slack_bridge.py:264 (named-call hint). **Side effects:** unclear — see source.
**Source:** `slack-bridge/slack_bridge.py:60`
### `_retry_after(e: SlackApiError) -> float`
> Get retry-after seconds if rate limited; else 0.
> **Called by:** slack-bridge/slack_bridge.py:111 (named-call hint); slack-bridge/slack_bridge.py:93 (named-call hint). **Side effects:** unclear — see source.
**Source:** `slack-bridge/slack_bridge.py:75`
### `_post_message_with_retry(**kwargs) -> None`
> Posts Slack message with rate limit retry handling.
> **Called by:** slack-bridge/slack_bridge.py:181 (named-call hint); slack-bridge/slack_bridge.py:187 (named-call hint); slack-bridge/slack_bridge.py:203 (named-call hint). **Side effects:** unclear — see source.
**Source:** `slack-bridge/slack_bridge.py:84`
### `_upload_file_with_retry(**kwargs) -> None`
> unclear — see source
> **Called by:** slack-bridge/slack_bridge.py:190 (named-call hint). **Side effects:** unclear — see source.
**Source:** `slack-bridge/slack_bridge.py:104`
### `mqtt_to_slack_callback(_topic: str, message: dict) -> None`
> MQTT subscription callback relaying alert messages into corresponding Slack channels.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `slack-bridge/slack_bridge.py:126`
### `handle_slack_event()`
> HTTP route handling Slack events, url_verification challenges, and button interactions.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `slack-bridge/slack_bridge.py:224`
### `healthz()`
> Health check route returning 200 OK.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `slack-bridge/slack_bridge.py:310`
### `_graceful_shutdown(signum, frame)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `slack-bridge/slack_bridge.py:320`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Reads Slack bot token from `/home/jovyan/.aws/credentials` (`[braingeneers-slack] token`). |
| Env `SLACK_SIGNING_SECRET`: Secret key for validating incoming Slack event webhook signatures. |
| Port: Runs Flask server on port 5000. |

## Data Shapes
- Input: MQTT messages on subscribed topics, Slack HTTP POST webhook JSON events.
- Output: Slack chat messages (`client.chat_postMessage`), file uploads (`client.files_upload_v2`), and published MQTT commands.

## Notes
- Verifies Slack HMAC-SHA256 signature on incoming requests.
- Handles Slack rate limits by parsing `Retry-After` headers and retrying requests.

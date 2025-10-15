import base64
import os
import signal
import sys
import configparser
import flask
import hmac
import hashlib
import logging
import time
import json
import threading
from typing import Optional, Tuple

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from braingeneers.iot import MessageBroker

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
app = flask.Flask(__name__)

# Log everything to TTY/stdout; no file handlers. Keep it simple & visible.
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
app.logger.handlers = []
app.logger.addHandler(_handler)
app.logger.setLevel(logging.DEBUG)
logging.getLogger('werkzeug').setLevel(logging.INFO)

# -----------------------------------------------------------------------------
# Config / Clients
# -----------------------------------------------------------------------------
config = configparser.ConfigParser()
config.read("/home/jovyan/.aws/credentials")

slack_token = config["braingeneers-slack"]["token"]
slack_signing_secret = config["braingeneers-slack"]["signing_secret"]

# Set a conservative timeout so Slack calls can't hang the process.
slack_client = WebClient(token=slack_token, timeout=30)

# Message broker
mb = MessageBroker()

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

def safe_publish(topic: str, payload: dict) -> None:
    """Publish to MQTT but never raise. Log and continue on error."""
    try:
        mb.publish_message(topic, payload)
    except Exception as e:  # noqa: BLE001
        app.logger.error("MQTT publish failed for %s: %s", topic, str(e))


def get_channel_name(channel_id: str) -> Optional[str]:
    app.logger.debug('channel_id> %s', channel_id)
    try:
        response = slack_client.conversations_info(channel=channel_id)
        app.logger.debug('conversations_info.response> %s', str(response))
        if response.get("ok"):
            return response["channel"].get("name")
        app.logger.error("Failed to get channel name for ID %s: %s", channel_id, str(response.get('error')))
    except SlackApiError as e:
        app.logger.error("Slack conversations_info error: %s", str(e))
    except Exception as e:  # noqa: BLE001
        app.logger.error("Unexpected error in get_channel_name: %s", str(e))
    return None


def _retry_after(e: SlackApiError) -> float:
    """Get retry-after seconds if rate limited; else 0."""
    try:
        headers = getattr(e.response, 'headers', {}) or {}
        return float(headers.get('Retry-After', 0))
    except Exception:  # noqa: BLE001
        return 0.0


def _post_message_with_retry(**kwargs) -> None:
    """Post a chat message with minimal backoff handling for rate-limits.
    Never propagates exceptions."""
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            slack_client.chat_postMessage(**kwargs)
            return
        except SlackApiError as e:
            wait = _retry_after(e)
            app.logger.error('chat_postMessage error (attempt %d/%d): %s', attempt, max_attempts, str(e))
            if wait > 0 and attempt < max_attempts:
                time.sleep(wait)
                continue
            break
        except Exception as e:  # noqa: BLE001
            app.logger.error('chat_postMessage unexpected error (attempt %d/%d): %s', attempt, max_attempts, str(e))
            break


def _upload_file_with_retry(**kwargs) -> None:
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            slack_client.files_upload(**kwargs)
            return
        except SlackApiError as e:
            wait = _retry_after(e)
            app.logger.error('files_upload error (attempt %d/%d): %s', attempt, max_attempts, str(e))
            if wait > 0 and attempt < max_attempts:
                time.sleep(wait)
                continue
            break
        except Exception as e:  # noqa: BLE001
            app.logger.error('files_upload unexpected error (attempt %d/%d): %s', attempt, max_attempts, str(e))
            break


# -----------------------------------------------------------------------------
# MQTT -> Slack
# -----------------------------------------------------------------------------

def mqtt_to_slack_callback(_topic: str, message: dict) -> None:
    """Robust MQTT-to-Slack bridge.
    - All exceptions are caught/logged; never block the broker thread.
    - Supports optional typing indicator, threads, text, and base64 file payloads.
    """
    try:
        channel = (_topic or '').split('/')[-1] or ''
        if not channel:
            app.logger.error("MQTT msg missing channel in topic: %s", _topic)
            return

        # Normalize payload
        if isinstance(message, (bytes, bytearray)):
            try:
                message = json.loads(message.decode('utf-8'))
            except Exception as e:  # noqa: BLE001
                app.logger.error("Ignoring non-JSON bytes MQTT message: %s", str(e))
                return
        elif isinstance(message, str):
            try:
                message = json.loads(message)
            except Exception as e:  # noqa: BLE001
                app.logger.error("Ignoring poorly formed JSON string: %s", str(e))
                return
        elif not isinstance(message, dict):
            app.logger.error("Ignoring message with unsupported type: %r", type(message))
            return

        text = message.get("message") or ""
        file_data = message.get("image")
        thread_ts = message.get("thread_ts")
        simulate_typing = bool(message.get("simulate_typing", False))
        filename = message.get("filename", "uploaded_file")

        # Typing indicator (best-effort)
        if simulate_typing:
            try:
                slack_client.api_call("typing", channel=channel)
                app.logger.debug('Sent typing indicator for channel: %s', channel)
                time.sleep(1)
            except SlackApiError as e:
                app.logger.error('Typing indicator error: %s', str(e))
            except Exception as e:  # noqa: BLE001
                app.logger.error('Typing indicator unexpected error: %s', str(e))

        # File upload path
        if file_data:
            try:
                # Accept both base64 payloads and raw bytes
                if isinstance(file_data, str):
                    try:
                        file_bytes = base64.b64decode(file_data, validate=True)
                    except Exception:
                        # If it wasn't base64, treat it as a raw string/URL and attach as text fallback
                        app.logger.warning('image field not base64; sending as text fallback')
                        _post_message_with_retry(channel=channel, text=f"{text}\n(attachment not base64)", thread_ts=thread_ts)
                        return
                elif isinstance(file_data, (bytes, bytearray)):
                    file_bytes = bytes(file_data)
                else:
                    app.logger.warning('Unsupported image type: %r', type(file_data))
                    _post_message_with_retry(channel=channel, text=f"{text}\n(unsupported attachment type)", thread_ts=thread_ts)
                    return

                _upload_file_with_retry(
                    channels=channel,
                    file=file_bytes,
                    filename=filename,
                    initial_comment=text or None,
                    thread_ts=thread_ts,
                )
                app.logger.debug('Uploaded file: %s to: %s in thread: %s', filename, channel, thread_ts)
            except Exception as e:  # noqa: BLE001
                app.logger.error('File upload unexpected error: %s', str(e))
                safe_publish("telemetry/slack/ERROR", {"error": str(e)})
        else:
            # Plain text path
            _post_message_with_retry(channel=channel, text=text or "", thread_ts=thread_ts)
            app.logger.debug('Message posted: %s to: %s in thread: %s', text, channel, thread_ts)

    except Exception as e:  # noqa: BLE001
        # Last-resort catch so the callback never crashes the broker thread
        app.logger.error('mqtt_to_slack_callback fatal handler error: %s', str(e))
        safe_publish("telemetry/slack/ERROR", {"error": str(e)})


# Subscribe once at import; broker should keep running even if callback throws.
try:
    mb.subscribe_message("telemetry/slack/TOSLACK/#", mqtt_to_slack_callback)
except Exception as e:  # noqa: BLE001
    app.logger.error("Failed to subscribe to MQTT topic: %s", str(e))


# -----------------------------------------------------------------------------
# Slack -> MQTT (Flask)
# -----------------------------------------------------------------------------

@app.route("/slack/events", methods=["POST"])
def handle_slack_event():
    """Handle Slack events and publish to MQTT.
    All failures return 200 when appropriate or 4xx/5xx with JSON but never crash the app.
    """
    try:
        data = flask.request.get_json(silent=True) or {}
        app.logger.debug('Incoming Slack data: %s', json.dumps(data)[:2000])

        # URL verification
        if data.get("type") == "url_verification":
            challenge = data.get("challenge")
            return flask.jsonify({"challenge": challenge})

        # Verify signature (best-effort; if headers missing -> 400)
        timestamp = flask.request.headers.get("X-Slack-Request-Timestamp")
        signature = flask.request.headers.get("X-Slack-Signature")
        if not timestamp or not signature:
            app.logger.warning("Missing Slack signature headers")
            return flask.jsonify({"error": "missing_signature"}), 400

        # prevent replay attacks: reject if older than 5 minutes
        try:
            if abs(time.time() - float(timestamp)) > 60 * 5:
                app.logger.warning("Stale Slack request: ts=%s", timestamp)
                return flask.jsonify({"error": "stale_request"}), 400
        except Exception:
            app.logger.warning("Non-numeric Slack timestamp: %r", timestamp)
            return flask.jsonify({"error": "bad_timestamp"}), 400

        req = str.encode(f"v0:{timestamp}:") + flask.request.get_data()
        request_hash = "v0=" + hmac.new(str.encode(slack_signing_secret), req, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(request_hash, signature):
            app.logger.warning("Bad Slack signature")
            return flask.jsonify({"error": "bad_signature"}), 403

        # Events API
        event = data.get('event') or {}
        if event.get("type") == "message":
            channel_id = event.get("channel")
            channel_name = get_channel_name(channel_id) or channel_id or "unknown"
            edited = bool(event.get("message", {}).get('edited'))
            text = event.get("message", {}).get('text') if edited else event.get("text")
            if text is None:
                text = '[Message deleted]'

            # Files (best-effort: just include file info name/URL if available)
            file_data = None
            filename = None
            try:
                files = event.get("files") or []
                if files:
                    file_info = files[0]
                    # We do not download here; just pass hint back to MQTT consumers
                    filename = file_info.get("name")
                    file_data = file_info.get("url_private")
            except Exception as e:  # noqa: BLE001
                app.logger.error("Error parsing file attachment: %s", str(e))

            thread_ts = event.get("thread_ts")
            user = event.get("user")

            safe_publish(f"telemetry/slack/FROMSLACK/{channel_name}", {
                "channel": channel_name,
                "message": text,
                "edited": edited,
                "filename": filename,
                "image": file_data,
                "thread_ts": thread_ts,
                "user": user,
            })

        # Always acknowledge to keep Slack happy
        return "", 200

    except Exception as e:  # noqa: BLE001
        app.logger.error('Flask /slack/events error: %s', str(e))
        safe_publish("telemetry/slack/ERROR", {"error": str(e)})
        # Return 200 to avoid Slack retry storms unless it's clearly our fault
        return flask.jsonify({"error": str(e)}), 500


# -----------------------------------------------------------------------------
# Health endpoint (simple liveness probe)
# -----------------------------------------------------------------------------
@app.route("/healthz", methods=["GET"])  # useful for k8s/docker health checks
def healthz():
    return flask.jsonify({"status": "ok"})


# -----------------------------------------------------------------------------
# Signal handling to avoid abrupt exits on SIGTERM/SIGINT
# -----------------------------------------------------------------------------
shutdown_flag = threading.Event()


def _graceful_shutdown(signum, frame):  # noqa: D401, ANN001, D401
    app.logger.info("Received signal %s; shutting down gracefully", signum)
    shutdown_flag.set()


signal.signal(signal.SIGINT, _graceful_shutdown)
signal.signal(signal.SIGTERM, _graceful_shutdown)


# -----------------------------------------------------------------------------
# Main entry
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Run Flask. Use threaded server so MQTT callbacks are not blocked.
    app.run(
        host='0.0.0.0',
        port=3000,
        threaded=True,
        ssl_context=(
            '/etc/nginx/certs/slack-bridge.braingeneers.gi.ucsc.edu/cert.pem',
            '/etc/nginx/certs/slack-bridge.braingeneers.gi.ucsc.edu/key.pem'
        )
    )

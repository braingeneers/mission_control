import base64
import os
import configparser
import flask
import hmac
import hashlib
import logging
import time

from typing import Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from braingeneers.iot import MessageBroker

app = flask.Flask(__name__)
app.logger.setLevel(logging.DEBUG)

# Read Slack credentials
config = configparser.ConfigParser()
config.read("/home/jovyan/.aws/credentials")

slack_token = config["braingeneers-slack"]["token"]
slack_signing_secret = config["braingeneers-slack"]["signing_secret"]

slack_client = WebClient(token=slack_token)
mb = MessageBroker()


def get_channel_name(channel_id: str) -> Optional[str]:
    app.logger.debug('DEBUG: channel_id> %s', channel_id)
    try:
        response = slack_client.conversations_info(channel=channel_id)
        app.logger.debug('DEBUG: slack_client.conversations_info.response> %s', str(response))
        if response["ok"]:
            return response["channel"]["name"]
        else:
            app.logger.error("Failed to get channel name for ID %s: %s", channel_id, str(response['error']))
    except SlackApiError as e:
        app.logger.error("Error getting channel name: %s", str(e))


def mqtt_to_slack_callback(_topic: str, message: dict):
    """ Callback function for MQTT messages. Posts the message to a Slack channel.
        If a thread timestamp is provided in the message, the message is posted as a reply in that thread.
        If the 'simulate_typing' flag is set in the message, a typing indicator is sent before posting.
    """
    channel = _topic.split('/')[-1]  # Get the channel name from the topic
    text = message.get("message")
    file_data = message.get("image")
    thread_ts = message.get("thread_ts")  # Get thread timestamp if available
    simulate_typing = message.get("simulate_typing", False)

    # If requested, send a typing indicator before sending the message.
    if simulate_typing:
        try:
            # Note: This uses an undocumented API method.
            slack_client.api_call("typing", channel=channel)
            app.logger.debug('DEBUG: Sent typing indicator for channel: %s', channel)
            # Optionally, wait a moment to simulate typing delay
            time.sleep(1)
        except SlackApiError as e:
            app.logger.error('ERROR: Typing indicator error: %s', str(e))

    # If there's a file, decode it from base64 and upload it to Slack
    if file_data:
        file_data = base64.b64decode(file_data)
        try:
            slack_client.files_upload(
                channels=channel,
                file=file_data,
                filename=message.get("filename", "uploaded_file"),
                initial_comment=text,
                thread_ts=thread_ts  # Post in thread if thread_ts is provided
            )
            app.logger.debug('DEBUG: Uploaded file: %s to: %s in thread: %s',
                             str(message.get("filename", "uploaded_file")), str(channel), thread_ts)
        except SlackApiError as e:
            app.logger.error('ERROR: File upload error: %s', str(e))
            mb.publish_message("telemetry/slack/ERROR", {"error": str(e)})
    else:
        try:
            slack_client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts  # Post as a thread reply if thread_ts is provided
            )
            app.logger.debug('DEBUG: Message posted: %s to: %s in thread: %s',
                             str(text), str(channel), thread_ts)
        except SlackApiError as e:
            mb.publish_message("telemetry/slack/ERROR", {"error": str(e)})
            app.logger.error('ERROR: Message posting error: %s', str(e))


# Subscribe to the MQTT topic
mb.subscribe_message("telemetry/slack/TOSLACK/#", mqtt_to_slack_callback)


@app.route("/slack/events", methods=["POST"])
def handle_slack_event():
    """ Handles a Slack event by publishing it to MQTT.
        This now includes checking for a thread timestamp and the sender's ID so that thread replies can be maintained.
    """
    try:
        data = flask.request.json
        app.logger.debug('DEBUG: Data: %s', str(data))

        # Handle URL verification
        if data.get("type") == "url_verification":
            return flask.jsonify({"challenge": data["challenge"]})

        # Verify the request
        timestamp = flask.request.headers.get("X-Slack-Request-Timestamp")
        signature = flask.request.headers.get("X-Slack-Signature")
        req = str.encode(f"v0:{timestamp}:") + flask.request.get_data()
        request_hash = "v0=" + hmac.new(str.encode(slack_signing_secret), req, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(request_hash, signature):
            flask.abort(403)

        # Handle different types of events (messages, thread replies, mentions)
        if 'event' in data and "type" in data["event"]:
            event_type = data["event"]["type"]
            if event_type == "message":
                channel_id = data["event"]["channel"]
                channel_name = get_channel_name(channel_id)
                edited = False
                file_data = None
                filename = None

                # Check for file attachment
                if "files" in data["event"]:
                    file_info = data["event"]["files"][0]
                    response = slack_client.files_info(file=file_info["id"])
                    if response["ok"]:
                        file_data = response["file"]["url_private"]
                        filename = response["file"]["name"]

                # Determine if message was edited
                if "message" in data["event"] and 'edited' in data["event"]["message"]:
                    text = data["event"]["message"].get('text', '[Message deleted]')
                    edited = True
                else:
                    text = data["event"].get("text", '[Message deleted]')

                # Get the thread timestamp if this message is part of a thread
                thread_ts = data["event"].get("thread_ts")

                # Get the sender's user id
                user = data["event"].get("user")

                mb.publish_message(f"telemetry/slack/FROMSLACK/{channel_name}", {
                    "channel": channel_name,
                    "message": text,
                    "edited": edited,
                    "filename": filename,
                    "image": file_data,
                    "thread_ts": thread_ts,  # Include thread_ts to keep thread context
                    "user": user         # Include sender's user id
                })

        return "", 200
    except Exception as e:
        mb.publish_message("telemetry/slack/ERROR", {"error": str(e)})
        app.logger.error('ERROR: Flask: %s', str(e))
        return flask.jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)

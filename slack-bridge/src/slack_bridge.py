import base64
import os
import configparser
import flask
import hmac
import hashlib
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from braingeneers.iot import MessageBroker

app = flask.Flask(__name__)

# Read Slack credentials
config = configparser.ConfigParser()
config.read(os.path.expanduser("/secrets/credentials"))

slack_token = config["braingeneers-slack"]["token"]
slack_signing_secret = config["braingeneers-slack"]["signing_secret"]

# Initialize the Slack WebClient
slack_client = WebClient(token=slack_token)

# Initialize Message Broker
mb = MessageBroker()


def mqtt_to_slack_callback(_topic: str, message: dict):
    """ Callback function for MQTT messages. Posts the message to a Slack channel. """
    channel = message.get("channel")
    text = message.get("message")
    file_data = message.get("file")

    # If there's a file, decode it from base64 and upload it to Slack
    if file_data is not None:
        file_data = base64.b64decode(file_data)
        try:
            slack_client.files_upload(
                channels=channel,
                file=file_data,
                initial_comment=text
            )
        except SlackApiError as e:
            # Post the error to the 'telemetry/slack/ERROR' MQTT topic
            mb.publish("telemetry/slack/ERROR", {"error": str(e)})
    else:
        try:
            slack_client.chat_postMessage(channel=channel, text=text)
        except SlackApiError as e:
            # Post the error to the 'telemetry/slack/ERROR' MQTT topic
            mb.publish("telemetry/slack/ERROR", {"error": str(e)})


# Subscribe to the MQTT topic
mb.subscribe_message("telemetry/slack/TOSLACK", mqtt_to_slack_callback)


@app.route("/slack/events", methods=["POST"])
def handle_slack_event():
    """ Handles a Slack event by publishing it to MQTT. """
    print('DEBUG> handle_slack_event')
    data = flask.request.json

    # Verify the request
    timestamp = flask.request.headers["X-Slack-Request-Timestamp"]
    signature = flask.request.headers["X-Slack-Signature"]
    req = str.encode(f"v0:{timestamp}:") + flask.request.get_data()
    request_hash = "v0=" + hmac.new(str.encode(slack_signing_secret), req, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(request_hash, signature):
        flask.abort(403)

    # TODO: Handle different types of events (messages, thread replies, mentions)
    event_type = data["event"]["type"]
    if event_type == "message":
        channel = data["event"]["channel"]
        text = data["event"]["text"]
        # TODO: Handle mentions and thread replies
        mb.publish("telemetry/slack/FROMSLACK", {"channel": channel, "message": text})

    return "", 200


if __name__ == "__main__":
    app.run(port=3000)  # replace with your preferred port

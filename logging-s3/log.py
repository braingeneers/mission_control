#!/usr/bin/env python3
"""
A service that subscribes to the "telemetry/#" topic and writes all received messages into a central s3 bucket.

Each log message is written as its own .csv file.  A separate service is intended to run as a cron job and
concatenate all logs files together periodically.
"""
import pytz
import json

from uuid import uuid4
from datetime import datetime
from braingeneers.utils import smart_open_braingeneers as smart_open
from braingeneers.iot import messaging


def main():
    """
    An infinite loop that keeps listening to the "telemetry/#" topic,
    writing all received messages to .csv files in s3.

    Topic format (where "a" and "b" are optional; "log" signifying the UUID end): `telemetry/a/<UUID>/log/b/cmnd`
    Specific example: `telemetry/2023-09-07-efi-mouse-2plex-official/log/zambezi-cam/cmnd`

    Log is saved here: `s3://braingeneers/logs/<UUID>/log.csv`
    Specific example: `s3://braingeneers/logs/2023-09-07-efi-mouse-2plex-official/log.csv`

    Note: All timestamps are written in UTC.

    Note: A MQTT device is recommended to produce a `<device-name>_<uuid>.log` of all jobs executed during
    the experiment with specific timestamps and any error messages it encounters.
    """
    mb = messaging.MessageBroker("mqtt-log-" + str(uuid4()))
    queue = mb.subscribe_message(topic="telemetry/#", callback=messaging.CallableQueue())
    while True:
        topic, message = queue.get()
        if '/log/' in topic:  # TODO: filter for this in subscribe_message()?
            uuid = topic.split('/log/')[0].split('/')[-1]  # cut out the uuid preceding "/log/"
            current_time = datetime.now(tz=pytz.timezone('UTC')).strftime('%Y-%m-%d_%H-%M-%S')

            # "1" signifies one message in the csv
            # concatenated files will have other markers (5m, 24h, etc.)
            log_path = f's3://braingeneers/logs/{uuid}/{current_time}.1.csv'

            with smart_open.open(log_path, 'w') as w:
                w.write(','.join([current_time, topic, json.dumps(message)]) + '\n')
            print(f'{topic}: {message}')


if __name__ == '__main__':
    main()

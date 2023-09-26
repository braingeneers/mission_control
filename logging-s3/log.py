#!/usr/bin/env python3
"""
A service that subscribes to the "telemetry/#" topic and writes all received messages into a central s3 bucket.

Each log message is written as its own .tsv file.  A separate service is intended to run as a cron job and
concatenate all logs files together periodically.
"""
import pytz
import sys
import time
import traceback
import os
import shutil

from uuid import uuid4
from datetime import datetime
from braingeneers.utils import smart_open_braingeneers as smart_open
from braingeneers.iot import messaging


def main():
    """
    An infinite loop that keeps listening to the "telemetry/#" topic,
    writing all received messages to .tsv files in s3.

    Topic format (where "a" and "b" are optional; "log" signifying the UUID end): `telemetry/a/<UUID>/log/b/cmnd`
    Specific example: `telemetry/2023-09-07-efi-mouse-2plex-official/log/zambezi-cam/cmnd`

    Log is saved here: `s3://braingeneers/logs/<UUID>/log.tsv`
    Specific example: `s3://braingeneers/logs/2023-09-07-efi-mouse-2plex-official/log.tsv`

    Note: All timestamps are written in UTC.

    Note: A MQTT device is recommended to produce a `<device-name>_<uuid>.log` of all jobs executed during
    the experiment with specific timestamps and any error messages it encounters.
    """
    print('Checking and moving credentials files...')
    src = '/secrets/prp-s3-credentials/credentials'
    dst = os.path.expanduser('~/.aws/credentials')
    if not os.path.exists(dst):
        if not os.path.exists(src):
            raise RuntimeError(f'{src} does not exist!  Are your secrets mounted?')
        os.makedirs(os.path.expanduser('~/.aws'), exist_ok=True)
        shutil.copyfile(src, dst)

    print('Starting the logging service...')
    mb = messaging.MessageBroker("mqtt-log-" + str(uuid4()))
    queue = mb.subscribe_message(topic="telemetry/#", callback=messaging.CallableQueue())
    while True:
        try:
            topic, message = queue.get()
            if '/log/' in topic:  # TODO: filter for this in subscribe_message()?
                uuid = topic.split('/log/')[0].split('/')[-1]  # cut out the uuid preceding "/log/"
                current_time = datetime.now(tz=pytz.timezone('UTC')).strftime('%Y-%m-%d_%H-%M-%S')

                # "1" signifies one message in the tsv
                # concatenated files will have other markers (100, 10000, etc.)
                with smart_open.open(f's3://braingeneers/logs/{uuid}/{current_time}.1.tsv', 'w') as w:
                    if isinstance(message, str):
                        message = {'': message}  # gotta have a key
                    unique_keys = sorted(set([k for k in message.keys()]))
                    line1 = ['_LOGTIMESTAMP', '_LOGTOPIC'] + [k.replace('\t', ' ') for k in unique_keys]
                    line2 = [current_time, topic] + [str(message.get(k, '')).replace('\t', ' ') for k in unique_keys]
                    file_contents = '\t'.join(line1) + '\n' + '\t'.join(line2)
                    w.write(file_contents)
                print(f'{topic}: {message}')
                print(f'WROTE:\n{file_contents}\n')
        except Exception as e:  # this is a long-lived logging service; never say die
            print(f'ERROR: {e}\n{traceback.format_exc()}', file=sys.stderr)
            time.sleep(1)


if __name__ == '__main__':
    main()

"""
Listens for MQTT topics with the convention:

  telemetry/workflow/log/START/<workflow-name> {"json": "params"}

And then triggers an appropriate nextflow workflow.
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
    An infinite loop that keeps listening to the "telemetry/workflow/log/START/<workflow-name>" topic,
    triggering workflows with the <workflow-name>.
    """
    print('Checking and moving credentials files...')
    src = '/secrets/prp-s3-credentials/credentials'
    dsts = ['/root/.aws/credentials', os.path.expanduser('~/.aws/credentials')]
    for dst in dsts:
        if not os.path.exists(dst):
            if not os.path.exists(src):
                raise RuntimeError(f'{src} does not exist!  Are your secrets mounted?')
            os.makedirs(dst[:-len('/credentials')], exist_ok=True)
            shutil.copyfile(src, dst)

    print('Starting the nextflow workflow launching service...')
    mb = messaging.MessageBroker("mqtt-nextflow-launcher-" + str(uuid4()))
    queue = mb.subscribe_message(topic="telemetry/workflow/log/START/#", callback=messaging.CallableQueue())
    while True:
        try:
            topic, message = queue.get()
            if '/log/' in topic:  # TODO: filter for this in subscribe_message()?
                workflow_name = topic.split('/START/')[-1]

                current_time = datetime.now(tz=pytz.timezone('UTC')).strftime('%Y-%m-%d_%H-%M-%S')

                # subprocess.run([cmd])
        except Exception as e:  # this is a long-lived logging service; never say die
            print(f'ERROR: {e}\n{traceback.format_exc()}', file=sys.stderr)
            time.sleep(1)


if __name__ == '__main__':
    main()

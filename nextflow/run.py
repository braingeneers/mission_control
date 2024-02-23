#!/usr/bin/env python3
"""
A service that subscribes to the "workflow/start/#" topic and launches workflows in the PRP.

Workflows are written in and launch with nextflow (or nextflow's docker image).
"""
import pytz
import sys
import time
import traceback
import os
import shutil
import subprocess

from uuid import uuid4
from datetime import datetime
from braingeneers.utils import smart_open_braingeneers as smart_open
from braingeneers.iot import messaging


def launch_nextflow_workflow(params):
    home_dir = os.path.expanduser('~')
    if home_dir.endswith('/'):
        home_dir = home_dir[:-1]

    nextflow_cmd = [
        'nextflow',
        'kuberun',
        'https://github.com/DailyDreaming/k8-nextflow',
        '-v whimvol:/workspace',
        '-head-cpus 1',
        '-head-memory 256Mi',
        '-r 1dbdeff',
        '--xyz zxy'
    ]

    docker_run_cmd = [
        'docker',
        'run',
        '--rm',
        f'--volume={home_dir}/.aws/:/root/.aws/',
        f'--volume={home_dir}/.kube/:/root/.kube/',
        f'--volume={home_dir}/.local/bin/:/usr/local/sbin/',
        'quay.io/ucsc_cgl/mqtt-nextflow-s3:0.0'
    ]

    p = subprocess.run(' '.join(docker_run_cmd + nextflow_cmd), shell=True)
    print(p)


def main():
    """
    An infinite loop that keeps listening to the "workflow/start/#" topic,
    launching workflows with the params provided.

    Note: All timestamps are written in UTC.
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
    mb = messaging.MessageBroker("nextflow-launcher-" + str(uuid4()))
    queue = mb.subscribe_message(topic="workflow/start/#", callback=messaging.CallableQueue())
    while True:
        try:
            topic, params = queue.get()
            current_time = datetime.now(tz=pytz.timezone('UTC')).strftime('%Y-%m-%d_%H-%M-%S')
            if isinstance(params, str):
                params = {'': params}  # gotta have a key
            print(f'{topic}: {params}')
            launch_nextflow_workflow(params)
            time.sleep(1)
        except Exception as e:  # this is a long-lived logging service; never say die
            print(f'ERROR: {e}\n{traceback.format_exc()}', file=sys.stderr)
            time.sleep(1)


if __name__ == '__main__':
    main()

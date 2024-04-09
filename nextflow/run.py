#!/usr/bin/env python3
"""
A service that subscribes to the "workflow/start" topic and launches workflows in the PRP.

Workflows are written in and launch with nextflow (or nextflow's docker image).

This assumes a PVC has been created and is available to mount and share between the worker pods.
"""
import sys
import time
import traceback
import os
import shutil
import subprocess
import pytz

from uuid import uuid4
from datetime import datetime
from braingeneers.iot import messaging
from typing import Dict, List


def get_current_commit_hash(url: str = '') -> str:
    """Returns the latest 7 char commit hash for a remote github repo."""
    p = subprocess.run(' '.join(['git', 'ls-remote', url]), shell=True, stdout=-1, stderr=-1)
    p.check_returncode()
    return p.stdout.decode()[:7]


def launch_nextflow_workflow(params: Dict[str, str]) -> None:
    github_url = params['url']

    nextflow_cmd = [
        'nextflow',
        'kuberun',
        github_url,
        '-v whimvol:/workspace',
        '-head-cpus 1',
        '-head-memory 1024Mi',
        f'-r {get_current_commit_hash(github_url)}'
    ]

    for k, v in params.items():
        if k.strip() and k != 'url':  # skip empty strings; e.g. ''
            nextflow_cmd.append(f'--{k} {v}')

    print(f'Now running: {nextflow_cmd}')
    current_time = datetime.now(tz=pytz.timezone('UTC')).strftime('%Y-%m-%d_%H-%M-%S')
    github_url_name = github_url.split('/')[-1][:-len('.git')] if github_url.endswith('.git') else github_url.split('/')[-1]
    stdout_log = open(f'/workflows/{github_url_name}.{current_time}.stdout', 'w')
    stderr_log = open(f'/workflows/{github_url_name}.{current_time}.stderr', 'w')
    p = subprocess.Popen(' '.join(nextflow_cmd), stdout=stdout_log, stderr=stderr_log, shell=True, start_new_session=True)
    print(f'Workflow has begun: {p}')
    print('Check workflow logs at: /workflows/')


def check_and_move_secrets(src: str, dsts: List[str]):
    print('Checking and moving credentials files...')
    for dst in dsts:
        if not os.path.exists(dst):
            if not os.path.exists(src):
                raise RuntimeError(f'{src} does not exist!  Are your secrets mounted?')
            os.makedirs(dst[:-len('/credentials')], exist_ok=True)
            shutil.copyfile(src, dst)


def main():
    """
    An infinite loop that keeps listening to the "workflow/start/#" topic,
    launching workflows with the params provided.

    Note: All timestamps are written in UTC.
    """
    check_and_move_secrets(
        src='/secrets/prp-s3-credentials/credentials',
        dsts=['/root/.aws/credentials', os.path.expanduser('~/.aws/credentials')]
    )
    check_and_move_secrets(
        src='/secrets/nextflow-service-account/kube-config',
        dsts=['/root/.kube/config', os.path.expanduser('~/.kube/config')]
    )

    if not os.path.exists('/workflows/'):
        os.makedirs('/workflows/', exist_ok=True)

    print('Starting the nextflow workflow launching service...')
    mb = messaging.MessageBroker("nextflow-launcher-" + str(uuid4()))
    queue = mb.subscribe_message(topic="workflow/start", callback=messaging.CallableQueue())
    while True:
        try:
            topic, params = queue.get()
            print(f'{topic}: {params}')
            if isinstance(params, dict):
                launch_nextflow_workflow(params)
        except Exception as e:  # this is a long-lived service; never say die
            print(f'ERROR: {e}\n{traceback.format_exc()}', file=sys.stderr)
        time.sleep(1)


if __name__ == '__main__':
    main()

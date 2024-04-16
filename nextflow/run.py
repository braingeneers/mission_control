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
import boto3

from uuid import uuid4
from functools import lru_cache
from datetime import datetime
from braingeneers import get_default_endpoint
from braingeneers.iot import messaging
from typing import Dict, List


@lru_cache()
def get_s3_client():
    return boto3.client('s3', endpoint_url=get_default_endpoint())


def list_uuid_original_data(bucket_slash_uuid: str) -> List[str]:
    """
    Lists all objects contained in s3://{bucket}/{uuid}/original/data/ .

    Note: bucket_slash_uuid == {bucket}/{uuid}
    """
    s3 = get_s3_client()
    assert '/' in bucket_slash_uuid, f'{bucket_slash_uuid} must be a string representing "bucket/uuid" .'
    bucket, uuid = bucket_slash_uuid.split('/')
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=f'{uuid}/original/data/'):
        for obj in page.get('Contents', []):
            obj_name = obj.get('Key', '/')
            if not obj_name.endswith('/'):
                yield f's3://{bucket}/{obj_name}'


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
    with open(f'/workflows/{github_url_name}.{current_time}.cmd', 'w') as f:
        f.write(nextflow_cmd)
    log_file = open(f'/workflows/{github_url_name}.{current_time}.log', 'w')
    p = subprocess.Popen(' '.join(nextflow_cmd), stdout=log_file, stderr=log_file, shell=True, start_new_session=True)
    print(f'Workflow has begun: {p}')
    print('Check workflow logs at: /workflows/')


def check_and_move_secrets(src: str, dsts: List[str]):
    print('Checking and moving credentials files...')
    for dst in dsts:
        if not os.path.exists(dst):
            if not os.path.exists(src):
                raise RuntimeError(f'{src} does not exist!  Are your secrets mounted?')
            os.makedirs(os.path.dirname(dst), exist_ok=True)
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
                if params['url'] == 'https://github.com/DailyDreaming/convert_to_nwb':
                    # for this workflow specifically, we convert an input UUID into full s3 "path"s prior to running
                    # a full s3 "path" must be specified at runtime in nextflow in order for the worker to import it
                    for s3_input_file in list_uuid_original_data(params['bucket_slash_uuid']):
                        launch_nextflow_workflow(params={
                            'url': params['url'],
                            'input_file': s3_input_file,
                            'output_dir': f"{params['bucket_slash_uuid']}/shared/"
                        })
                        time.sleep(1)
                else:
                    launch_nextflow_workflow(params)
        except Exception as e:  # this is a long-lived service; never say die
            print(f'ERROR: {e}\n{traceback.format_exc()}', file=sys.stderr)
        time.sleep(1)


if __name__ == '__main__':
    main()

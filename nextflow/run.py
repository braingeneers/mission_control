"""
Listens for MQTT topics with the convention:

  telemetry/workflow/log/START/<workflow-name> {"json": "params"}

And then triggers an appropriate nextflow workflow.
"""
import docker
import pytz
import sys
import time
import traceback
import os
import shutil
import subprocess
import json

from uuid import uuid4
from datetime import datetime
from braingeneers.utils import smart_open_braingeneers as smart_open
from braingeneers.iot import messaging


# def run_workflow(workflow_src, params):
#     """
#
#     nextflow kuberun https://github.com/DailyDreaming/k8-nextflow -v whimvol:/workspace -head-cpus 1 -head-memory 256Mi --xyz zyx
#     """
#     client = docker.from_env(version='auto')
#     streamfile = 'output.log'
#     home = os.path.expanduser('~')
#     volumes = {
#         os.path.join(home, '.aws/'): {'bind': '/root/.aws/', 'mode': 'rw'},
#         os.path.join(home, '.kube/'): {'bind': '/root/.kube/', 'mode': 'rw'},
#         os.path.join(home, '.local/bin/'): {'bind': '/usr/local/sbin/', 'mode': 'rw'}
#     }
#     cmd = 'nextflow kuberun https://github.com/DailyDreaming/k8-nextflow -v whimvol:/workspace -head-cpus 1 -head-memory 256Mi --xyz zyx'
#
#     # When detach is True, this returns a container object:
#     # >>> client.containers.run("bfirsh/reticulate-splines", detach=True)
#     # <Container '45e6d2de7c54'>
#     container = client.containers.run(image='nextflow/nextflow:latest',
#                                       command=cmd,
#                                       detach=True,
#                                       # volumes=volumes,
#                                       # auto_remove=auto_remove,
#                                       stdout=True,
#                                       stderr=True,
#                                       stream=True,
#                                       remove=True,
#                                       # log_config=log_config,
#                                       # environment=os.environ,
#                                       user=f'{os.getuid()}:{os.getgid()}')
#
#     with open(streamfile, 'wb') as f:
#         # stream=True makes this loop blocking; we will loop until
#         # the container stops and there is no more output.
#         for line in container.logs(stdout=True, stderr=True, stream=True):
#             f.write(line.encode() if isinstance(line, str) else line)


def main():
    workflow_name = 'https://github.com/DailyDreaming/k8-nextflow'
    p = subprocess.run(f'nextflow kuberun {workflow_name} -v whimvol:/workspace -head-cpus 1 -head-memory 256Mi --xyz zyx', shell=True, stdout=-1, stderr=-1)
    print(p)
    print(p.stdout)
    print(p.stderr)


# def main():
#     """
#     An infinite loop that keeps listening to the "telemetry/workflow/log/START/<workflow-name>" topic,
#     triggering workflows with the <workflow-name>.
#     """
#     print('Checking and moving credentials files...')
#     src = '/secrets/prp-s3-credentials/credentials'
#     dsts = ['/root/.aws/credentials', os.path.expanduser('~/.aws/credentials')]
#     for dst in dsts:
#         if not os.path.exists(dst):
#             if not os.path.exists(src):
#                 raise RuntimeError(f'{src} does not exist!  Are your secrets mounted?')
#             os.makedirs(dst[:-len('/credentials')], exist_ok=True)
#             shutil.copyfile(src, dst)
#
#     print('Starting the nextflow workflow launching service...')
#     mb = messaging.MessageBroker("mqtt-nextflow-launcher-" + str(uuid4()))
#     queue = mb.subscribe_message(topic="telemetry/workflow/log/START/#", callback=messaging.CallableQueue())
#     while True:
#         try:
#             topic, message = queue.get()
#             workflow_name = f"workflows/{topic.split('/START/')[-1]}"
#             workflow_name = 'https://github.com/DailyDreaming/k8-nextflow'
#             params = ''
#             if not isinstance(message, str):
#                 for k, v in message:
#                     params += f' --{k}={v}'
#             params = json.loads(message) if isinstance(message, str) else ''
#
#             p = subprocess.run(f'nextflow kuberun {workflow_name} -v whimvol:/workspace -head-cpus 1 -head-memory 256Mi {params}', shell=True)
#         except Exception as e:  # this is a long-lived logging service; never say die
#             print(f'ERROR: {e}\n{traceback.format_exc()}', file=sys.stderr)
#             time.sleep(1)


if __name__ == '__main__':
    main()

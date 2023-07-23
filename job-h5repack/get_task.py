import os
from braingeneers.iot.messaging import MessageBroker
import braingeneers.data.datasets_electrophysiology as de
import braingeneers.utils.common_utils as common_utils
import posixpath
import queue


uuid = os.environ['UUID']
queue_name = f'job-h5repack-{uuid.lower()}'
q = MessageBroker().get_queue(queue_name)
try:
    print(q.get(block=False))
except queue.Empty:
    print('END')

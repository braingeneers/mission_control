import os
from braingeneers.iot.messaging import MessageBroker
import braingeneers.data.datasets_electrophysiology as de
import braingeneers.utils.common_utils as common_utils
import posixpath


uuid = os.environ['UUID']
mb = MessageBroker()
queue_name = f'job-h5repack-{uuid.lower()}'
mb.delete_queue(queue_name)
q = mb.get_queue(queue_name)
metadata = de.load_metadata(uuid)

# Seed the queue with files to process
for ephys_experiment in metadata['ephys_experiments'].values():
    for block in ephys_experiment['blocks']:
        data_file = posixpath.join(common_utils.get_basepath(), 'ephys', uuid, block['path'])
        print(f'Adding to queue: {data_file}')
        q.put(data_file)

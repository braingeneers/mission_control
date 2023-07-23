import os
from braingeneers.iot.messaging import MessageBroker
import braingeneers.data.datasets_electrophysiology as de
import braingeneers.utils.common_utils as common_utils
import posixpath


prefix = common_utils.get_basepath()
file = os.environ['FILE']
mb = MessageBroker()
lock_name = f'job-h5repack-lock-{uuid.lower()}'

with mb.get_lock(lock_name):
    metadata = de.load_metadata(uuid)

    for ephys_experiment in metadata['ephys_experiments']:
        for _, block in ephys_experiment['blocks'].items():
            if block['path'] == file:
                block['path'] = os.environ['ROWMAJOR_FILE']

    de.save_metadata(metadata)
import argparse
from braingeneers.iot.messaging import MessageBroker
import braingeneers.data.datasets_electrophysiology as de
import braingeneers.utils.common_utils as common_utils
import posixpath


def main(uuid: str, delete_queue: bool = True):
    mb = MessageBroker()
    queue_name = f'job-h5repack-{uuid.lower()}'
    if delete_queue:
        mb.delete_queue(queue_name)
    q = mb.get_queue(queue_name)
    metadata = de.load_metadata(uuid)

    # Seed the queue with files to process
    for ephys_experiment in metadata['ephys_experiments'].values():
        for block in ephys_experiment['blocks']:
            data_file = posixpath.join(common_utils.get_basepath(), 'ephys', uuid, block['path'])
            print(f'Adding to queue: {data_file}')
            q.put(data_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Provide UUID as an argument')
    parser.add_argument('--uuid', '-u', type=str, required=True, help='UUID for the process')
    parser.add_argument('--no-delete-queue', '-n', dest='delete', action='store_false', help='Do not delete the queue')
    args = parser.parse_args()
    main(args.uuid, args.delete)

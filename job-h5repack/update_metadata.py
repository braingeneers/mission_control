import argparse
from braingeneers.iot.messaging import MessageBroker
import braingeneers.data.datasets_electrophysiology as de
import braingeneers.utils.common_utils as common_utils
import posixpath
from tenacity import retry, stop_after_attempt, wait_fixed


def main(uuid, file, rowmajor_file):
    mb = MessageBroker()
    lock_name = f'job-h5repack-lock-{uuid.lower()}'

    print(f'Getting Lock: {lock_name}')
    with mb.get_lock(lock_name):
        metadata = de.load_metadata(uuid)

        print(f'Updating metadata for file {file}, changed to {rowmajor_file}')
        for ephys_experiment in metadata['ephys_experiments'].values():
            for block in ephys_experiment['blocks']:
                if block['path'] == file:
                    print(f'Updating file {block["path"]} --> {file}')
                    block['path'] = rowmajor_file

        print('Saving metadata')
        save_metadata(metadata)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def save_metadata(metadata):
    de.save_metadata(metadata)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Provide UUID, FILE, and ROWMAJOR_FILE as arguments')
    parser.add_argument('--uuid', '-u', type=str, required=True, help='UUID for the process')
    parser.add_argument('--file', '-f', type=str, required=True, help='File for the process')
    parser.add_argument('--rowmajor-file', '-r', type=str, required=True, help='Rowmajor file for the process')
    args = parser.parse_args()
    main(args.uuid, args.file, args.rowmajor_file)

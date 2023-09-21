import argparse
from braingeneers.iot.messaging import MessageBroker
import braingeneers.data.datasets_electrophysiology as de
import braingeneers.utils.common_utils as common_utils
import posixpath
from tenacity import retry, stop_after_attempt, wait_fixed


def main(uuid, file, rowmajor_file):

    print(f'Getting metadata write lock: {uuid}')
    with MessageBroker().get_lock(uuid):
        metadata = de.load_metadata(uuid)

        # Get the block for either the file or the rowmajor file
        file_block = [
            block
            for block in metadata['ephys_experiments'].values()
            for block in block['blocks'] if block['path'] == file or block['path'] == rowmajor_file
        ]

        # assert that one and only one of the files was found
        assert len(file_block) == 1, \
            f'Found {len(file_block)} blocks for file {file} and ' \
            f'rowmajor file {rowmajor_file} where there should be exactly 1'

        # Either update or exit successfully if the update has already been applied
        if file_block[0]['path'] == rowmajor_file and 'data_order' in file_block[0] and file_block[0]['data_order'] == 'rowmajor':
            print(f'File {file} was already updated to {rowmajor_file}, exiting successfully without any changes.')
        else:
            # Verify that the rowmajor_file exists
            s3path_rowmajor_file = posixpath.join(common_utils.get_basepath(), 'ephys', uuid, rowmajor_file)
            assert common_utils.file_exists(s3path_rowmajor_file), f'Rowmajor file does not exist at {s3path_rowmajor_file}, no update performed.'

            # perform update and save
            print(f'Updating metadata for file {file}, changed to {rowmajor_file}')
            file_block[0]['path'] = rowmajor_file
            file_block[0]['data_order'] = 'rowmajor'
            save_metadata(metadata)
            print(f'Metadata saved to {posixpath.join(common_utils.get_basepath(), "ephys", uuid, "metadata.json")}')


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def save_metadata(metadata):
    de.save_metadata(metadata)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Provide UUID, FILE, and ROWMAJOR_FILE as arguments')
    parser.add_argument('--uuid', '-u', type=str, required=True, help='UUID for the process')
    parser.add_argument('--file', '-f', type=str, required=True, help='File for the process including original/data file prefix')
    parser.add_argument('--rowmajor-file', '-r', type=str, required=True, help='Rowmajor file for the process including original/data file prefix')
    args = parser.parse_args()
    main(args.uuid, args.file, args.rowmajor_file)

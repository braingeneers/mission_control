#!/usr/bin/env python

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_EXCEPTION
import braingeneers.utils.smart_open_braingeneers as smart_open_bgr
import smart_open as smart_open_aws
import boto3

NRP_ENDPOINT = os.getenv('NRP_ENDPOINT')
GLACIER_BUCKET = os.getenv('GLACIER_BUCKET')
LOCAL_SCRATCH_DIR = os.getenv('LOCAL_SCRATCH_DIR')
AWS_PROFILE = 'aws-braingeneers-backups'

# Create a boto3 session using the specified AWS profile
session = boto3.Session(profile_name=AWS_PROFILE)
s3_client = session.client('s3')

def copy_file(source_key, glacier_bucket):
    try:
        print(f'Copying: {source_key}')
        source_url = f's3://{source_key}'
        destination_url = f's3://{glacier_bucket}/{source_key}'

        with smart_open_bgr.open(source_url, 'rb') as fin, smart_open_aws.open(destination_url, 'wb', transport_params={'client': s3_client}) as fout:
            while True:
                data = fin.read(1024 * 1024)  # 1 MB at a time
                if data:
                    fout.write(data)
                else:
                    break
        return source_key, True
    except Exception as e:
        return source_key, False, e

def process_files(file_list, glacier_bucket, max_workers=1):
    total_files = len(file_list)
    success = True
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(copy_file, file.strip(), glacier_bucket): file for file in file_list}

        # Use wait with FIRST_EXCEPTION to stop processing on first failure
        done, not_done = wait(futures, return_when=FIRST_EXCEPTION)

        for future in done:
            try:
                source_key, file_success, *error = future.result()
                if file_success:
                    print(f'Processed: {list(futures).index(future) + 1}/{total_files} s3://{source_key}')
                else:
                    success = False
                    print(f'Upload failed: s3://{source_key} - {error[0]}', file=sys.stderr)
                    break
            except Exception as e:
                success = False
                print(f'Exception occurred: {e}', file=sys.stderr)
                break

        # Cancel remaining futures if a failure occurred
        if not success:
            for future in not_done:
                future.cancel()

    return success

def main():
    puts_file = os.path.join(LOCAL_SCRATCH_DIR, 'puts.txt')

    with open(puts_file, 'r') as f:
        file_list = f.readlines()

    success = process_files(file_list, GLACIER_BUCKET)

    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()

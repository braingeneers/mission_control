#!/usr/bin/env python

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        return source_key, True, None
    except Exception as e:
        return source_key, False, e

def process_files(file_list, glacier_bucket, max_workers=1):
    total_files = len(file_list)
    success_count = 0
    failure_count = 0
    failures = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(copy_file, file.strip(), glacier_bucket): file for file in file_list}

        for idx, future in enumerate(as_completed(futures), 1):
            try:
                source_key, file_success, error = future.result()
                if file_success:
                    success_count += 1
                    print(f'Processed: {idx}/{total_files} s3://{source_key}')
                else:
                    failure_count += 1
                    failures.append((source_key, error))
                    print(f'Upload failed: s3://{source_key} - {error}', file=sys.stderr)
            except Exception as e:
                failure_count += 1
                failures.append(('unknown', e))
                print(f'Exception occurred: {e}', file=sys.stderr)

    print(f'\nSummary:')
    print(f'  Successes: {success_count}')
    print(f'  Failures: {failure_count}')

    if failure_count > 0:
        print('\nFailed Files:')
        for source_key, error in failures:
            print(f'  s3://{source_key} - {error}', file=sys.stderr)

    return failure_count == 0

def main():
    puts_file = os.path.join(LOCAL_SCRATCH_DIR, 'puts.txt')

    with open(puts_file, 'r') as f:
        file_list = f.readlines()

    success = process_files(file_list, GLACIER_BUCKET)

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

#!/usr/bin/env python

import argparse
import os
import subprocess
import sys
import time

import boto3
import smart_open as smart_open_aws
from botocore.config import Config as BotocoreConfig


DEFAULT_AWS_PROFILE = 'aws-braingeneers-backups'
DEFAULT_AWS_REGION = 'us-west-2'
DEFAULT_PART_SIZE_MIB = 64
DEFAULT_CHUNK_SIZE_MIB = 64
DEFAULT_UPLOADER = 'smart-open'
DEFAULT_MULTIPART_UPLOAD = True
DEFAULT_RCLONE_S3_PROVIDER = 'AWS'
DEFAULT_RCLONE_USE_PRESIGNED_REQUEST = 'unset'
DEFAULT_RCLONE_USE_UNSIGNED_PAYLOAD = 'unset'
DEFAULT_RCLONE_DISABLE_CHECKSUM = 'false'
DEFAULT_RCLONE_CHUNK_SIZE_MIB = 0
DEFAULT_RCLONE_UPLOAD_CONCURRENCY = 0


def parse_args():
    parser = argparse.ArgumentParser(
        description='Local proof-of-concept uploader for Stage 4 multipart behavior.'
    )
    parser.add_argument('--source-file', required=True, help='Local file path to upload.')
    parser.add_argument('--destination-url', required=True, help='Destination S3 URL.')
    parser.add_argument(
        '--uploader',
        choices=['smart-open', 'aws-cli', 'rclone'],
        default=DEFAULT_UPLOADER,
        help=f'Upload implementation to exercise (default: {DEFAULT_UPLOADER})',
    )
    parser.add_argument(
        '--aws-profile',
        default=os.getenv('STAGE4_POC_AWS_PROFILE', DEFAULT_AWS_PROFILE),
        help=f'AWS profile name (default: {DEFAULT_AWS_PROFILE})',
    )
    parser.add_argument(
        '--aws-region',
        default=os.getenv('STAGE4_POC_AWS_REGION', DEFAULT_AWS_REGION),
        help=f'AWS region name (default: {DEFAULT_AWS_REGION})',
    )
    parser.add_argument(
        '--part-size-mib',
        type=int,
        default=DEFAULT_PART_SIZE_MIB,
        help=f'Multipart part size in MiB (default: {DEFAULT_PART_SIZE_MIB})',
    )
    parser.add_argument(
        '--copy-chunk-mib',
        type=int,
        default=DEFAULT_CHUNK_SIZE_MIB,
        help=f'Copy chunk size in MiB (default: {DEFAULT_CHUNK_SIZE_MIB})',
    )
    parser.add_argument(
        '--multipart-upload',
        choices=['true', 'false'],
        default='true' if DEFAULT_MULTIPART_UPLOAD else 'false',
        help='Whether smart_open should use multipart upload (default: true)',
    )
    parser.add_argument(
        '--aws-max-attempts',
        type=int,
        default=5,
        help='Botocore retry max attempts for the destination client (default: 5)',
    )
    parser.add_argument(
        '--aws-retry-mode',
        default='standard',
        help='Botocore retry mode for the destination client (default: standard)',
    )
    parser.add_argument(
        '--rclone-s3-provider',
        default=DEFAULT_RCLONE_S3_PROVIDER,
        help=f'Rclone S3 provider name (default: {DEFAULT_RCLONE_S3_PROVIDER})',
    )
    parser.add_argument(
        '--rclone-use-presigned-request',
        choices=['true', 'false', 'unset'],
        default=DEFAULT_RCLONE_USE_PRESIGNED_REQUEST,
        help='Rclone S3 single-part upload style override (default: unset)',
    )
    parser.add_argument(
        '--rclone-use-unsigned-payload',
        choices=['true', 'false', 'unset'],
        default=DEFAULT_RCLONE_USE_UNSIGNED_PAYLOAD,
        help='Rclone S3 unsigned payload override (default: unset)',
    )
    parser.add_argument(
        '--rclone-disable-checksum',
        choices=['true', 'false'],
        default=DEFAULT_RCLONE_DISABLE_CHECKSUM,
        help='Disable rclone MD5 checksum metadata on upload (default: false)',
    )
    parser.add_argument(
        '--rclone-chunk-size-mib',
        type=int,
        default=DEFAULT_RCLONE_CHUNK_SIZE_MIB,
        help='Rclone multipart chunk size in MiB; 0 keeps the default',
    )
    parser.add_argument(
        '--rclone-upload-concurrency',
        type=int,
        default=DEFAULT_RCLONE_UPLOAD_CONCURRENCY,
        help='Rclone multipart upload concurrency; 0 keeps the default',
    )
    return parser.parse_args()


def build_client(profile_name, region_name, max_attempts, retry_mode):
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    return session.client(
        's3',
        region_name=region_name,
        config=BotocoreConfig(
            retries={
                'max_attempts': max_attempts,
                'mode': retry_mode,
            }
        ),
    )


def upload_with_smart_open(args, part_size_bytes, chunk_size_bytes):
    client = build_client(
        profile_name=args.aws_profile,
        region_name=args.aws_region,
        max_attempts=args.aws_max_attempts,
        retry_mode=args.aws_retry_mode,
    )
    multipart_upload = args.multipart_upload == 'true'

    started = time.time()
    bytes_written = 0
    with open(args.source_file, 'rb') as source_file, smart_open_aws.open(
        args.destination_url,
        'wb',
        transport_params={
            'client': client,
            'multipart_upload': multipart_upload,
            'min_part_size': part_size_bytes,
        },
    ) as destination_file:
        while True:
            chunk = source_file.read(chunk_size_bytes)
            if not chunk:
                break
            destination_file.write(chunk)
            bytes_written += len(chunk)
            elapsed = max(0.001, time.time() - started)
            mib_written = bytes_written / (1024 * 1024)
            print(
                (
                    f'Uploaded chunk={len(chunk)} bytes total={bytes_written} bytes '
                    f'({mib_written:.1f} MiB) elapsed={elapsed:.2f}s '
                    f'rate={mib_written / elapsed:.2f} MiB/s'
                ),
                flush=True,
            )

    elapsed = max(0.001, time.time() - started)
    print(
        (
            f'Upload complete: bytes_written={bytes_written} '
            f'elapsed={elapsed:.2f}s average_rate={(bytes_written / (1024 * 1024)) / elapsed:.2f} MiB/s'
        ),
        flush=True,
    )


def upload_with_aws_cli(args):
    command = [
        'aws',
        '--profile',
        args.aws_profile,
        '--region',
        args.aws_region,
        's3',
        'cp',
        args.source_file,
        args.destination_url,
    ]
    print(f'AWS CLI command: {" ".join(command)}', flush=True)
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def parse_s3_url(url):
    if not url.startswith('s3://'):
        raise ValueError(f'Unsupported S3 URL: {url}')
    remainder = url[len('s3://'):]
    bucket, _, key = remainder.partition('/')
    if not bucket or not key:
        raise ValueError(f'Expected s3://bucket/key URL, got: {url}')
    return bucket, key


def upload_with_rclone(args):
    bucket, key = parse_s3_url(args.destination_url)
    remote = (
        f":s3,provider={args.rclone_s3_provider},env_auth=true,"
        f"profile={args.aws_profile},region={args.aws_region}:{bucket}/{key}"
    )
    command = [
        'rclone',
        'copyto',
        args.source_file,
        remote,
        '--stats=15s',
        '--stats-one-line',
        '--progress',
    ]
    if args.multipart_upload == 'false':
        command.append('--s3-use-multipart-uploads=false')
    if args.rclone_use_presigned_request != 'unset':
        command.append(f'--s3-use-presigned-request={args.rclone_use_presigned_request}')
    if args.rclone_use_unsigned_payload != 'unset':
        command.append(f'--s3-use-unsigned-payload={args.rclone_use_unsigned_payload}')
    if args.rclone_disable_checksum == 'true':
        command.append('--s3-disable-checksum')
    if args.rclone_chunk_size_mib > 0:
        command.append(f'--s3-chunk-size={args.rclone_chunk_size_mib}M')
    if args.rclone_upload_concurrency > 0:
        command.append(f'--s3-upload-concurrency={args.rclone_upload_concurrency}')
    print(f'Rclone command: {" ".join(command)}', flush=True)
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main():
    args = parse_args()
    part_size_bytes = args.part_size_mib * 1024 * 1024
    chunk_size_bytes = args.copy_chunk_mib * 1024 * 1024

    print(
        (
            'Stage 4 upload POC config: '
            f"source_file={args.source_file}, destination_url={args.destination_url}, "
            f'uploader={args.uploader}, multipart_upload={args.multipart_upload}, '
            f'aws_profile={args.aws_profile}, aws_region={args.aws_region}, '
            f'part_size_bytes={part_size_bytes}, copy_chunk_bytes={chunk_size_bytes}, '
            f'aws_max_attempts={args.aws_max_attempts}, aws_retry_mode={args.aws_retry_mode}, '
            f'rclone_s3_provider={args.rclone_s3_provider}, '
            f'rclone_use_presigned_request={args.rclone_use_presigned_request}, '
            f'rclone_use_unsigned_payload={args.rclone_use_unsigned_payload}, '
            f'rclone_disable_checksum={args.rclone_disable_checksum}, '
            f'rclone_chunk_size_mib={args.rclone_chunk_size_mib}, '
            f'rclone_upload_concurrency={args.rclone_upload_concurrency}'
        ),
        flush=True,
    )

    if args.uploader == 'smart-open':
        upload_with_smart_open(args, part_size_bytes, chunk_size_bytes)
    elif args.uploader == 'aws-cli':
        upload_with_aws_cli(args)
    elif args.uploader == 'rclone':
        upload_with_rclone(args)
    else:
        raise SystemExit(f'Unsupported uploader: {args.uploader}')


if __name__ == '__main__':
    main()

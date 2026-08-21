#!/usr/bin/env python

import argparse
import csv
import json
import math
import os
import random
import sys
import threading
import tempfile
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_NRP_ENDPOINT = 'https://s3.braingeneers.gi.ucsc.edu'
NRP_ENDPOINT = os.getenv('NRP_ENDPOINT') or os.getenv('ENDPOINT') or DEFAULT_NRP_ENDPOINT
# Keep both names available for downstream helpers.
os.environ['NRP_ENDPOINT'] = NRP_ENDPOINT
os.environ['ENDPOINT'] = NRP_ENDPOINT

import boto3
import braingeneers.utils.smart_open_braingeneers as smart_open_bgr
import smart_open as smart_open_aws
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectionClosedError,
    EndpointConnectionError,
    ParamValidationError,
    ReadTimeoutError,
    SSLError,
)
from badkeys import (
    SOURCE_GET_FAILED_AFTER_HEAD_SUCCESS,
    append_source_get_failed_slack_section,
    make_badkey_record,
    merge_badkey_records,
    read_badkeys_tsv,
    source_get_failed_records,
    write_badkeys_tsv,
)
from stage4_keys import build_source_lookup_candidates, load_put_keys, normalize_bucket_object_key
from lifecycle_controls import is_retention_marker

GLACIER_BUCKET = os.getenv('GLACIER_BUCKET')
LOCAL_SCRATCH_DIR = os.getenv('LOCAL_SCRATCH_DIR')
AWS_PROFILE = os.getenv('GLACIER_PROFILE', 'aws-braingeneers-backups')
DEFAULT_AWS_REGION = 'us-west-2'
DEFAULT_WORKERS = 2
DEFAULT_RETRIES = 3
DEFAULT_RETRY_BASE_SECONDS = 1.5
DEFAULT_RETRY_MAX_SECONDS = 30.0
DEFAULT_AWS_MAX_ATTEMPTS = 5
DEFAULT_AWS_RETRY_MODE = 'standard'
DEFAULT_AWS_MAX_POOL_CONNECTIONS = 64
MULTIPART_PART_SIZE_BYTES = 64 * 1024 * 1024
DEFAULT_PROGRESS_INTERVAL_SECONDS = 30
DEFAULT_PROGRESS_STALL_ALERT_SECONDS = 600
DEFAULT_MAX_PENDING_TASKS = 256
COPY_CHUNK_BYTES = 1 * 1024 * 1024
EXIT_SUCCESS = 0
EXIT_STAGE4_PUTS_LOAD_FAILURE = 42
EXIT_STAGE4_RUNTIME_FAILURE = 43
EXIT_STAGE4_UPLOAD_FRACTION_GUARD = 44


class UploadFractionGuardError(ValueError):
    pass


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def validate_upload_fraction_guard(file_list, comparison_summary_path, max_upload_fraction):
    try:
        with open(comparison_summary_path, 'r', encoding='utf8') as summary_file:
            summary = json.load(summary_file)
    except (OSError, json.JSONDecodeError) as error:
        raise UploadFractionGuardError(f'could not read comparison summary: {error}') from error

    if summary.get('schema_version') != 1:
        raise UploadFractionGuardError(
            f'unsupported comparison summary schema_version: {summary.get("schema_version")!r}'
        )

    required_integer_fields = (
        'eligible_local_distinct_objects',
        'pending_put_rows',
        'pending_put_distinct_objects',
    )
    for field in required_integer_fields:
        value = summary.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise UploadFractionGuardError(f'invalid {field}: {value!r}')

    recorded_fraction = summary.get('pending_upload_fraction')
    if isinstance(recorded_fraction, bool) or not isinstance(recorded_fraction, (int, float)):
        raise UploadFractionGuardError(f'invalid pending_upload_fraction: {recorded_fraction!r}')
    if not math.isfinite(float(recorded_fraction)):
        raise UploadFractionGuardError('pending_upload_fraction must be finite')

    actual_rows = len(file_list)
    actual_distinct = len(set(file_list))
    if actual_rows != summary['pending_put_rows']:
        raise UploadFractionGuardError(
            f'PUT row count mismatch: summary={summary["pending_put_rows"]} actual={actual_rows}'
        )
    if actual_distinct != summary['pending_put_distinct_objects']:
        raise UploadFractionGuardError(
            (
                'distinct PUT count mismatch: '
                f'summary={summary["pending_put_distinct_objects"]} actual={actual_distinct}'
            )
        )

    has_control_accounting = all(
        field in summary
        for field in (
            'pending_data_put_rows',
            'pending_data_put_distinct_objects',
            'pending_control_put_rows',
            'pending_control_put_distinct_objects',
        )
    )
    data_puts = [key for key in file_list if not is_retention_marker(key)]
    control_puts = [key for key in file_list if is_retention_marker(key)]
    actual_data_rows = len(data_puts)
    actual_data_distinct = len(set(data_puts))
    actual_control_rows = len(control_puts)
    actual_control_distinct = len(set(control_puts))
    if has_control_accounting:
        expected_counts = {
            'pending_data_put_rows': actual_data_rows,
            'pending_data_put_distinct_objects': actual_data_distinct,
            'pending_control_put_rows': actual_control_rows,
            'pending_control_put_distinct_objects': actual_control_distinct,
        }
        for field, actual in expected_counts.items():
            value = summary[field]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise UploadFractionGuardError(f'invalid {field}: {value!r}')
            if value != actual:
                raise UploadFractionGuardError(
                    f'{field} mismatch: summary={value} actual={actual}'
                )
    else:
        # Stage-by-stage compatibility for summaries written before control
        # objects received separate accounting.
        actual_data_rows = actual_rows
        actual_data_distinct = actual_distinct
        actual_control_rows = 0
        actual_control_distinct = 0

    eligible_distinct = summary['eligible_local_distinct_objects']
    if eligible_distinct == 0 and actual_data_distinct > 0:
        raise UploadFractionGuardError(
            'eligible local data-object count is zero while pending data PUTs are nonzero'
        )
    actual_fraction = actual_data_distinct / eligible_distinct if eligible_distinct else 0.0
    if not math.isclose(actual_fraction, float(recorded_fraction), rel_tol=1e-9, abs_tol=1e-12):
        raise UploadFractionGuardError(
            (
                'pending upload fraction mismatch: '
                f'summary={float(recorded_fraction):.12f} actual={actual_fraction:.12f}'
            )
        )

    print(
        (
            '[stage4][guard] '
            f'eligible_local_distinct_objects={eligible_distinct} '
            f'pending_data_put_distinct_objects={actual_data_distinct} '
            f'pending_control_put_distinct_objects={actual_control_distinct} '
            f'pending_upload_fraction={actual_fraction:.6f} '
            f'max_upload_fraction={max_upload_fraction:.6f}'
        ),
        flush=True,
    )
    if actual_fraction > max_upload_fraction:
        raise UploadFractionGuardError(
            (
                f'pending upload fraction {actual_fraction:.6f} exceeds '
                f'configured maximum {max_upload_fraction:.6f}; no uploads were started'
            )
        )
    return summary


def build_s3_client():
    session = boto3.Session(profile_name=AWS_PROFILE or None)
    aws_region = os.getenv('STAGE4_AWS_REGION') or session.region_name or DEFAULT_AWS_REGION
    return session.client(
        's3',
        region_name=aws_region,
        config=BotocoreConfig(
            retries={
                'max_attempts': env_int('STAGE4_AWS_MAX_ATTEMPTS', DEFAULT_AWS_MAX_ATTEMPTS),
                'mode': os.getenv('STAGE4_AWS_RETRY_MODE', DEFAULT_AWS_RETRY_MODE),
            },
            max_pool_connections=env_int('STAGE4_AWS_MAX_POOL_CONNECTIONS', DEFAULT_AWS_MAX_POOL_CONNECTIONS),
        ),
    )


_s3_client = None
_source_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = build_s3_client()
    return _s3_client


def build_source_s3_client():
    return boto3.client(
        's3',
        endpoint_url=NRP_ENDPOINT,
        config=BotocoreConfig(
            signature_version='s3v4',
            s3={'addressing_style': 'path'},
            retries={
                'max_attempts': env_int('STAGE4_SOURCE_AWS_MAX_ATTEMPTS', DEFAULT_AWS_MAX_ATTEMPTS),
                'mode': os.getenv('STAGE4_SOURCE_AWS_RETRY_MODE', DEFAULT_AWS_RETRY_MODE),
            },
            max_pool_connections=env_int('STAGE4_SOURCE_AWS_MAX_POOL_CONNECTIONS', DEFAULT_AWS_MAX_POOL_CONNECTIONS),
        ),
    )


def get_source_s3_client():
    global _source_s3_client
    if _source_s3_client is None:
        _source_s3_client = build_source_s3_client()
    return _source_s3_client


def head_object_exists(glacier_bucket, key, s3_client=None):
    client = s3_client or get_s3_client()
    return client.head_object(Bucket=glacier_bucket, Key=key)


def source_head_object_exists(bucket_key, source_s3_client=None):
    normalized = normalize_bucket_object_key(bucket_key)
    if normalized is None:
        raise ValueError(f'invalid source bucket/key: {bucket_key!r}')
    bucket, object_key = normalized.split('/', 1)
    client = source_s3_client or get_source_s3_client()
    return client.head_object(Bucket=bucket, Key=object_key)


def find_head_visible_source_key(source_candidates, source_head_object_func=None, source_s3_client=None):
    source_head_object_func = source_head_object_func or source_head_object_exists
    for candidate in source_candidates:
        try:
            source_head_object_func(candidate, source_s3_client=source_s3_client)
            return candidate
        except Exception as error:
            if is_missing_source_error(error):
                continue
            print(
                f'WARNING: Source HeadObject diagnostic failed for s3://{candidate}: {error}',
                file=sys.stderr,
                flush=True,
            )
            continue
    return None


def stream_upload(
    source_url,
    destination_url,
    source_opener=None,
    destination_opener=None,
    s3_client=None,
    multipart_part_size_bytes=None,
    copy_chunk_bytes=None,
    progress_callback=None,
):
    source_opener = source_opener or smart_open_bgr.open
    destination_opener = destination_opener or smart_open_aws.open
    s3_client = s3_client or get_s3_client()
    multipart_part_size_bytes = multipart_part_size_bytes or MULTIPART_PART_SIZE_BYTES
    copy_chunk_bytes = copy_chunk_bytes or COPY_CHUNK_BYTES
    bytes_copied = 0

    with source_opener(source_url, 'rb') as fin, destination_opener(
        destination_url,
        'wb',
        transport_params={
            'client': s3_client,
            'multipart_upload': True,
            'min_part_size': multipart_part_size_bytes,
        },
    ) as fout:
        while True:
            data = fin.read(copy_chunk_bytes)
            if not data:
                break
            fout.write(data)
            bytes_copied += len(data)
            if progress_callback is not None:
                progress_callback(len(data))

    return bytes_copied


def is_retryable_error(error):
    # Invalid request shapes/params will never succeed on retry.
    if isinstance(error, ParamValidationError):
        return False
    if isinstance(error, (EndpointConnectionError, ConnectionClosedError, ReadTimeoutError, SSLError)):
        return True
    if isinstance(error, ClientError):
        response = error.response or {}
        status = response.get('ResponseMetadata', {}).get('HTTPStatusCode')
        code = response.get('Error', {}).get('Code', '')
        if status and int(status) >= 500:
            return True
        if code in {'RequestTimeout', 'Throttling', 'SlowDown', 'InternalError', 'ServiceUnavailable'}:
            return True
    if isinstance(error, BotoCoreError):
        return True

    message = str(error).lower()
    retry_tokens = (
        'ssl validation failed',
        'eof occurred in violation of protocol',
        'connection reset',
        'connection aborted',
        'read timeout',
        'timed out',
        'temporarily unavailable',
        'broken pipe',
    )
    return any(token in message for token in retry_tokens)


def is_missing_source_error(error):
    if isinstance(error, ClientError):
        response = error.response or {}
        status = response.get('ResponseMetadata', {}).get('HTTPStatusCode')
        code = response.get('Error', {}).get('Code', '')
        if status == 404:
            return True
        if code in {'404', 'NoSuchKey', 'NoSuchVersion', 'NotFound'}:
            return True

    message = str(error).lower()
    missing_tokens = (
        'nosuchkey',
        'no such key',
        'not found',
        '404',
    )
    return any(token in message for token in missing_tokens)


def format_duration(total_seconds):
    total_seconds = max(0, int(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


def classify_error(error):
    if isinstance(error, ClientError):
        response = error.response or {}
        status = response.get('ResponseMetadata', {}).get('HTTPStatusCode')
        code = response.get('Error', {}).get('Code', 'Unknown')
        if status is None:
            return f'ClientError:{code}'
        return f'ClientError:{code}:{status}'
    return type(error).__name__


def utc_now_iso():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


class ActivityLogger:
    FIELDNAMES = [
        'CompletedAtUTC',
        'RunStartedAtUTC',
        'BucketKey',
        'UploadedBucketKey',
        'BytesCopied',
        'GlacierBucket',
        'Result',
    ]

    def __init__(self, path, run_started_at_utc):
        self.path = path
        self.run_started_at_utc = run_started_at_utc
        self._lock = threading.Lock()
        self._upgrade_legacy_log_if_needed()
        file_exists = os.path.exists(path)
        self._file_handle = open(path, 'a', encoding='utf8', newline='')
        self._writer = csv.DictWriter(self._file_handle, fieldnames=self.FIELDNAMES)
        if not file_exists or os.path.getsize(path) == 0:
            self._writer.writeheader()
            self._file_handle.flush()

    def _upgrade_legacy_log_if_needed(self):
        if not os.path.exists(self.path) or os.path.getsize(self.path) == 0:
            return

        with open(self.path, 'r', encoding='utf8', newline='') as existing_file:
            reader = csv.DictReader(existing_file)
            if reader.fieldnames == self.FIELDNAMES:
                return
            legacy_rows = list(reader)

        temp_fd, temp_path = tempfile.mkstemp(
            dir=os.path.dirname(self.path) or None,
            prefix='activity-log-upgrade-',
            suffix='.csv',
            text=True,
        )
        os.close(temp_fd)
        try:
            with open(temp_path, 'w', encoding='utf8', newline='') as upgraded_file:
                writer = csv.DictWriter(upgraded_file, fieldnames=self.FIELDNAMES)
                writer.writeheader()
                for row in legacy_rows:
                    writer.writerow(
                        {
                            'CompletedAtUTC': row.get('CompletedAtUTC', ''),
                            'RunStartedAtUTC': row.get('RunStartedAtUTC', ''),
                            'BucketKey': row.get('BucketKey', ''),
                            'UploadedBucketKey': row.get('UploadedBucketKey', ''),
                            'BytesCopied': row.get('BytesCopied', ''),
                            'GlacierBucket': row.get('GlacierBucket', ''),
                            'Result': row.get('Result', 'uploaded'),
                        }
                    )
            os.replace(temp_path, self.path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def record_event(self, bucket_key, uploaded_bucket_key, bytes_copied, glacier_bucket, result):
        row = {
            'CompletedAtUTC': utc_now_iso(),
            'RunStartedAtUTC': self.run_started_at_utc,
            'BucketKey': bucket_key,
            'UploadedBucketKey': uploaded_bucket_key,
            'BytesCopied': bytes_copied,
            'GlacierBucket': glacier_bucket,
            'Result': result,
        }
        with self._lock:
            self._writer.writerow(row)
            self._file_handle.flush()

    def close(self):
        with self._lock:
            self._file_handle.close()


class ProgressStats:
    def __init__(self, total_files):
        self.total_files = total_files
        self.start_time = time.monotonic()
        self.last_completion_time = self.start_time
        self.completed = 0
        self.success_count = 0
        self.failure_count = 0
        self.success_bytes = 0
        self.stream_bytes = 0
        self.retry_count = 0
        self.retry_sleep_seconds = 0.0
        self.retry_error_counts = Counter()
        self.active_transfers = {}
        self._lock = threading.Lock()

    def record_retry(self, error, sleep_seconds):
        with self._lock:
            self.retry_count += 1
            self.retry_sleep_seconds += sleep_seconds
            self.retry_error_counts[classify_error(error)] += 1

    def record_completion(self, success, bytes_copied):
        now = time.monotonic()
        with self._lock:
            self.completed += 1
            self.last_completion_time = now
            if success:
                self.success_count += 1
                self.success_bytes += bytes_copied
            else:
                self.failure_count += 1

    def record_transfer_start(self, source_key):
        now = time.monotonic()
        with self._lock:
            self.active_transfers[source_key] = {
                'start_time': now,
                'last_progress_time': now,
                'stream_bytes': 0,
            }

    def record_transfer_progress(self, source_key, bytes_delta):
        if bytes_delta <= 0:
            return
        now = time.monotonic()
        with self._lock:
            self.stream_bytes += bytes_delta
            transfer = self.active_transfers.get(source_key)
            if transfer is not None:
                transfer['stream_bytes'] += bytes_delta
                transfer['last_progress_time'] = now

    def record_transfer_end(self, source_key):
        with self._lock:
            self.active_transfers.pop(source_key, None)

    def snapshot(self):
        now = time.monotonic()
        with self._lock:
            return {
                'now': now,
                'start_time': self.start_time,
                'last_completion_time': self.last_completion_time,
                'total_files': self.total_files,
                'completed': self.completed,
                'success_count': self.success_count,
                'failure_count': self.failure_count,
                'success_bytes': self.success_bytes,
                'stream_bytes': self.stream_bytes,
                'retry_count': self.retry_count,
                'retry_sleep_seconds': self.retry_sleep_seconds,
                'retry_error_counts': self.retry_error_counts.copy(),
                'active_transfers': {
                    key: value.copy() for key, value in self.active_transfers.items()
                },
            }


def compact_key(key, max_len=100):
    if len(key) <= max_len:
        return key
    return f'...{key[-(max_len - 3):]}'


def progress_reporter(stats, interval_seconds, stop_event, stall_alert_seconds):
    previous = stats.snapshot()
    last_stall_alert_time = 0.0
    while not stop_event.wait(interval_seconds):
        current = stats.snapshot()
        elapsed = max(0.0, current['now'] - current['start_time'])
        interval_elapsed = max(1e-6, current['now'] - previous['now'])
        completed_delta = current['completed'] - previous['completed']
        bytes_delta = current['success_bytes'] - previous['success_bytes']
        stream_bytes_delta = current['stream_bytes'] - previous['stream_bytes']
        retries_delta = current['retry_count'] - previous['retry_count']
        retry_sleep_delta = current['retry_sleep_seconds'] - previous['retry_sleep_seconds']
        percent = (100.0 * current['completed'] / current['total_files']) if current['total_files'] else 100.0
        in_flight = max(0, current['total_files'] - current['completed'])
        interval_files_per_sec = completed_delta / interval_elapsed
        interval_mib_per_sec = (bytes_delta / (1024 * 1024)) / interval_elapsed
        interval_stream_mib_per_sec = (stream_bytes_delta / (1024 * 1024)) / interval_elapsed
        overall_mib_per_sec = ((current['success_bytes'] / (1024 * 1024)) / elapsed) if elapsed > 0 else 0.0
        no_progress_seconds = max(0.0, current['now'] - current['last_completion_time'])
        top_retry_errors = current['retry_error_counts'].most_common(3)
        top_retry_errors_label = ', '.join(f'{name}={count}' for name, count in top_retry_errors) if top_retry_errors else 'none'
        active_transfers = current['active_transfers']
        active_count = len(active_transfers)
        oldest_active_seconds = 0.0
        stalled_active_count = 0
        oldest_active_labels = 'none'
        if active_transfers:
            now = current['now']
            transfer_rows = []
            for key, meta in active_transfers.items():
                age_seconds = max(0.0, now - meta['start_time'])
                idle_seconds = max(0.0, now - meta['last_progress_time'])
                stream_mib = meta['stream_bytes'] / (1024 * 1024)
                transfer_rows.append((key, age_seconds, idle_seconds, stream_mib))
            oldest_active_seconds = max(row[1] for row in transfer_rows)
            stalled_active_count = sum(1 for row in transfer_rows if row[2] >= interval_seconds * 2)
            transfer_rows.sort(key=lambda row: row[1], reverse=True)
            oldest_active_labels = ', '.join(
                f"{compact_key(row[0])}@{row[1]:.0f}s/{row[3]:.1f}MiB"
                for row in transfer_rows[:3]
            )

        print(
            (
                f"[STATUS] elapsed={format_duration(elapsed)} done={current['completed']}/{current['total_files']} "
                f"({percent:.1f}%) in_flight={in_flight} ok={current['success_count']} fail={current['failure_count']} "
                f"retries={current['retry_count']} retry_sleep={current['retry_sleep_seconds']:.0f}s "
                f"rate={interval_files_per_sec:.2f} files/s, {interval_mib_per_sec:.2f} MiB/s "
                f"stream_rate={interval_stream_mib_per_sec:.2f} MiB/s "
                f"(overall {overall_mib_per_sec:.2f} MiB/s) no_progress={no_progress_seconds:.0f}s "
                f"window_retries={retries_delta} window_retry_sleep={retry_sleep_delta:.1f}s "
                f"active={active_count} oldest_active={oldest_active_seconds:.0f}s "
                f"stalled_active={stalled_active_count} top_retry_errors={top_retry_errors_label}"
            ),
            file=sys.stderr,
            flush=True,
        )

        if active_count > 0 and no_progress_seconds >= stall_alert_seconds:
            if (current['now'] - last_stall_alert_time) >= max(stall_alert_seconds, interval_seconds):
                print(
                    (
                        '[stage4][alert] No file completions for an extended window while uploads are still active. '
                        f'no_progress={no_progress_seconds:.0f}s active={active_count} '
                        f'oldest_active={oldest_active_seconds:.0f}s stream_rate={interval_stream_mib_per_sec:.2f} MiB/s '
                        f'oldest_keys={oldest_active_labels}'
                    ),
                    file=sys.stderr,
                    flush=True,
                )
                last_stall_alert_time = current['now']

        if completed_delta == 0 and retries_delta > 0:
            print(
                (
                    '[stage4][alert] No file completions in the last reporting window while retries increased. '
                    'Likely retry/backoff storm causing low throughput.'
                ),
                file=sys.stderr,
                flush=True,
            )

        previous = current


def copy_file(
    source_key,
    glacier_bucket,
    retries,
    retry_base_seconds,
    retry_max_seconds,
    stats,
    head_object_func=None,
    source_opener=None,
    destination_opener=None,
    s3_client=None,
    source_s3_client=None,
    source_head_object_func=None,
    multipart_part_size_bytes=None,
    copy_chunk_bytes=None,
    sleep_func=time.sleep,
    uniform_func=random.uniform,
):
    source_candidates = build_source_lookup_candidates(source_key)
    if not source_candidates:
        return {
            'destination_key': source_key,
            'resolved_source_key': source_key,
            'status': 'failed',
            'error': ValueError('invalid source key'),
            'bytes_copied': 0,
        }

    total_attempts = retries + 1
    head_object_func = head_object_func or head_object_exists
    s3_client = s3_client or get_s3_client()
    multipart_part_size_bytes = multipart_part_size_bytes or MULTIPART_PART_SIZE_BYTES
    copy_chunk_bytes = copy_chunk_bytes or COPY_CHUNK_BYTES

    for attempt in range(1, total_attempts + 1):
        if not is_retention_marker(source_key):
            try:
                head_object_func(glacier_bucket, source_key, s3_client=s3_client)
                return {
                    'destination_key': source_key,
                    'resolved_source_key': source_key,
                    'status': 'skipped_existing',
                    'error': None,
                    'bytes_copied': 0,
                }
            except Exception as error:
                if not is_missing_source_error(error):
                    if attempt >= total_attempts or not is_retryable_error(error):
                        return {
                            'destination_key': source_key,
                            'resolved_source_key': source_key,
                            'status': 'failed',
                            'error': error,
                            'bytes_copied': 0,
                        }

                    backoff = min(retry_max_seconds, retry_base_seconds * (2 ** (attempt - 1)))
                    sleep_seconds = backoff * uniform_func(0.8, 1.2)
                    stats.record_retry(error, sleep_seconds)
                    print(
                        (
                            f'Retrying destination existence check ({attempt}/{retries}) for '
                            f's3://{glacier_bucket}/{source_key} in {sleep_seconds:.1f}s due to retryable error: {error}'
                        ),
                        file=sys.stderr,
                    )
                    sleep_func(sleep_seconds)
                    continue

        for candidate_idx, candidate_source_key in enumerate(source_candidates):
            source_url = f's3://{candidate_source_key}'
            destination_url = f's3://{glacier_bucket}/{source_key}'
            bytes_copied = 0
            stats.record_transfer_start(candidate_source_key)
            try:
                bytes_copied = stream_upload(
                    source_url,
                    destination_url,
                    source_opener=source_opener,
                    destination_opener=destination_opener,
                    s3_client=s3_client,
                    multipart_part_size_bytes=multipart_part_size_bytes,
                    copy_chunk_bytes=copy_chunk_bytes,
                    progress_callback=lambda size: stats.record_transfer_progress(candidate_source_key, size),
                )

                if candidate_source_key != source_key:
                    print(
                        (
                            f"[stage4] source key fallback matched: original='s3://{source_key}' "
                            f"resolved='s3://{candidate_source_key}'"
                        ),
                        file=sys.stderr,
                        flush=True,
                    )
                return {
                    'destination_key': source_key,
                    'resolved_source_key': candidate_source_key,
                    'status': 'uploaded',
                    'error': None,
                    'bytes_copied': bytes_copied,
                }
            except Exception as error:
                has_fallback = candidate_idx < (len(source_candidates) - 1)
                if is_missing_source_error(error) and has_fallback:
                    continue

                if attempt >= total_attempts or not is_retryable_error(error):
                    status = 'missing_source' if is_missing_source_error(error) else 'failed'
                    head_visible_source_key = None
                    if status == 'missing_source':
                        head_visible_source_key = find_head_visible_source_key(
                            source_candidates,
                            source_head_object_func=source_head_object_func,
                            source_s3_client=source_s3_client,
                        )
                    return {
                        'destination_key': source_key,
                        'resolved_source_key': candidate_source_key,
                        'status': status,
                        'error': error,
                        'bytes_copied': 0,
                        'head_visible_source_key': head_visible_source_key,
                    }

                backoff = min(retry_max_seconds, retry_base_seconds * (2 ** (attempt - 1)))
                sleep_seconds = backoff * uniform_func(0.8, 1.2)
                stats.record_retry(error, sleep_seconds)
                print(
                    (
                        f'Retrying upload ({attempt}/{retries}) for s3://{candidate_source_key} '
                        f'in {sleep_seconds:.1f}s due to retryable error: {error}'
                    ),
                    file=sys.stderr,
                )
                sleep_func(sleep_seconds)
                break
            finally:
                stats.record_transfer_end(candidate_source_key)


def process_files(
    file_list,
    glacier_bucket,
    max_workers,
    max_pending_tasks,
    retries,
    retry_base_seconds,
    retry_max_seconds,
    progress_interval_seconds,
    progress_stall_alert_seconds,
    activity_logger,
):
    total_files = len(file_list)
    stats = ProgressStats(total_files=total_files)
    success_count = 0
    already_present_count = 0
    failure_count = 0
    missing_source_count = 0
    failures = []
    missing_sources = []
    source_access_bad_keys = []
    stop_event = threading.Event()
    progress_thread = None

    if progress_interval_seconds > 0:
        progress_thread = threading.Thread(
            target=progress_reporter,
            args=(stats, progress_interval_seconds, stop_event, progress_stall_alert_seconds),
            daemon=True,
        )
        progress_thread.start()

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            file_iter = iter(file_list)
            pending = {}
            completed_count = 0

            def submit_next_task():
                try:
                    source_key = next(file_iter)
                except StopIteration:
                    return False

                future = executor.submit(
                    copy_file,
                    source_key,
                    glacier_bucket,
                    retries,
                    retry_base_seconds,
                    retry_max_seconds,
                    stats,
                )
                pending[future] = source_key
                return True

            while len(pending) < max_pending_tasks and submit_next_task():
                pass

            while pending:
                done_futures, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done_futures:
                    completed_count += 1
                    source_key = pending.pop(future, 'unknown')
                    try:
                        result = future.result()
                        destination_key = result['destination_key']
                        resolved_source_key = result['resolved_source_key']
                        status = result['status']
                        error = result['error']
                        bytes_copied = result['bytes_copied']
                        head_visible_source_key = result.get('head_visible_source_key')
                        stats.record_completion(success=(status in {'uploaded', 'skipped_existing'}), bytes_copied=bytes_copied)
                        if status == 'uploaded':
                            success_count += 1
                            activity_logger.record_event(
                                destination_key,
                                destination_key,
                                bytes_copied,
                                glacier_bucket,
                                'uploaded',
                            )
                            print(f'Processed: {completed_count}/{total_files} s3://{destination_key}', flush=True)
                        elif status == 'skipped_existing':
                            already_present_count += 1
                            activity_logger.record_event(
                                destination_key,
                                destination_key,
                                0,
                                glacier_bucket,
                                'already_present_skipped',
                            )
                            print(
                                f'Already present (skipped): {completed_count}/{total_files} s3://{destination_key}',
                                flush=True,
                            )
                        else:
                            if status == 'missing_source':
                                missing_source_count += 1
                                missing_sources.append((resolved_source_key, error))
                                if head_visible_source_key:
                                    source_access_bad_keys.append(head_visible_source_key)
                                print(
                                    (
                                        f'Missing source (skipped): {completed_count}/{total_files} '
                                        f's3://{resolved_source_key} - {error}'
                                    ),
                                    file=sys.stderr,
                                    flush=True,
                                )
                            else:
                                failure_count += 1
                                failures.append((destination_key, error))
                                print(f'Upload failed: s3://{destination_key} - {error}', file=sys.stderr, flush=True)
                    except Exception as error:
                        failure_count += 1
                        failures.append((source_key, error))
                        stats.record_completion(success=False, bytes_copied=0)
                        print(f'Exception occurred for s3://{source_key} - {error}', file=sys.stderr, flush=True)

                while len(pending) < max_pending_tasks and submit_next_task():
                    pass
    finally:
        stop_event.set()
        if progress_thread is not None:
            progress_thread.join(timeout=2)

    print('\nSummary:')
    print(f'  Successes: {success_count}')
    print(f'  Already present skipped: {already_present_count}')
    print(f'  Missing sources skipped: {missing_source_count}')
    print(f'  Failures: {failure_count}')
    snapshot = stats.snapshot()
    elapsed = max(0.0, snapshot['now'] - snapshot['start_time'])
    average_mib_per_sec = ((snapshot['success_bytes'] / (1024 * 1024)) / elapsed) if elapsed > 0 else 0.0
    print(f'  Retries: {snapshot["retry_count"]}')
    print(f'  Retry sleep: {snapshot["retry_sleep_seconds"]:.1f}s')
    print(f'  Successful data copied: {snapshot["success_bytes"] / (1024 * 1024):.1f} MiB')
    print(f'  Average throughput: {average_mib_per_sec:.2f} MiB/s')
    top_retry_errors = snapshot['retry_error_counts'].most_common(5)
    if top_retry_errors:
        print('  Top retry errors:')
        for name, count in top_retry_errors:
            print(f'    - {name}: {count}')

    if failure_count > 0:
        print('\nFailed Files:')
        for source_key, error in failures:
            print(f'  s3://{source_key} - {error}', file=sys.stderr)

    if missing_source_count > 0:
        print('\nSkipped Missing Source Files:')
        for source_key, error in missing_sources:
            print(f'  s3://{source_key} - {error}', file=sys.stderr)

    source_access_bad_key_count = len(set(source_access_bad_keys))
    if source_access_bad_key_count > 0:
        print(
            (
                '\nSource access bad keys: '
                f'{source_access_bad_key_count} key(s) had source HeadObject metadata but failed source GetObject.'
            ),
            file=sys.stderr,
        )

    if failure_count > 0 or missing_source_count > 0:
        print(
            (
                '\nStage 4 completed with recoverable per-file issues. '
                'Remaining failed or missing-source objects can be retried in the next upload cycle.'
            ),
            file=sys.stderr,
            flush=True,
        )
    else:
        print('\nStage 4 completed cleanly.', flush=True)

    return {
        'success_count': success_count,
        'already_present_count': already_present_count,
        'failure_count': failure_count,
        'missing_source_count': missing_source_count,
        'source_access_bad_keys': sorted(set(source_access_bad_keys)),
    }


def split_s3_uri(uri):
    parsed = urlparse(uri)
    if parsed.scheme != 's3' or not parsed.netloc or not parsed.path:
        raise ValueError(f'Expected s3://bucket/key URI, got {uri!r}')
    return parsed.netloc, parsed.path.lstrip('/')


def upload_primary_inventory_artifact(local_path, primary_inventory_path, source_s3_client=None):
    if not primary_inventory_path:
        return
    if not primary_inventory_path.endswith('/'):
        primary_inventory_path = f'{primary_inventory_path}/'
    destination_uri = f'{primary_inventory_path}{Path(local_path).name}'
    bucket, key = split_s3_uri(destination_uri)
    client = source_s3_client or get_source_s3_client()
    with open(local_path, 'rb') as file_handle:
        client.put_object(Bucket=bucket, Key=key, Body=file_handle.read())
    print(f'Uploaded {local_path} to {destination_uri}', flush=True)


def update_source_access_artifacts(source_access_bad_keys, source_s3_client=None):
    if not LOCAL_SCRATCH_DIR:
        return

    records = [
        make_badkey_record(SOURCE_GET_FAILED_AFTER_HEAD_SUCCESS, bucket_key)
        for bucket_key in sorted(set(source_access_bad_keys))
    ]
    if not records:
        return

    badkeys_path = os.path.join(LOCAL_SCRATCH_DIR, 'badkeys.tsv')
    slack_path = os.path.join(LOCAL_SCRATCH_DIR, 'cleanup_within_notification_window_slack.txt')
    merged_records = merge_badkey_records(read_badkeys_tsv(badkeys_path), records)
    write_badkeys_tsv(badkeys_path, merged_records)

    source_records = source_get_failed_records(merged_records)
    if os.path.exists(slack_path):
        with open(slack_path, 'r', encoding='utf8') as slack_file:
            slack_message = slack_file.read()
        updated_message = append_source_get_failed_slack_section(slack_message, source_records)
        with open(slack_path, 'w', encoding='utf8') as slack_file:
            slack_file.write(updated_message)
    else:
        print(f'WARNING: Missing cleanup Slack message artifact: {slack_path}', file=sys.stderr, flush=True)

    primary_inventory_path = os.getenv('PRIMARY_INVENTORY_PATH')
    if not primary_inventory_path:
        return

    for artifact_path in (badkeys_path, slack_path):
        if not os.path.exists(artifact_path):
            continue
        try:
            upload_primary_inventory_artifact(
                artifact_path,
                primary_inventory_path,
                source_s3_client=source_s3_client,
            )
        except Exception as error:
            print(
                f'WARNING: Failed to upload updated artifact {artifact_path}: {error}',
                file=sys.stderr,
                flush=True,
            )


def main():
    parser = argparse.ArgumentParser(description='Copy S3 files to Glacier bucket with parallel processing.')
    parser.add_argument(
        '-w',
        '--workers',
        type=int,
        default=DEFAULT_WORKERS,
        help=f'Number of worker threads (default: {DEFAULT_WORKERS})',
    )
    parser.add_argument(
        '--retries',
        type=int,
        default=env_int('STAGE4_RETRIES', DEFAULT_RETRIES),
        help=f'Number of retries for transient upload errors per file (default: {DEFAULT_RETRIES})',
    )
    parser.add_argument(
        '--retry-base-seconds',
        type=float,
        default=env_float('STAGE4_RETRY_BASE_SECONDS', DEFAULT_RETRY_BASE_SECONDS),
        help=f'Base delay for exponential retry backoff (default: {DEFAULT_RETRY_BASE_SECONDS})',
    )
    parser.add_argument(
        '--retry-max-seconds',
        type=float,
        default=env_float('STAGE4_RETRY_MAX_SECONDS', DEFAULT_RETRY_MAX_SECONDS),
        help=f'Maximum delay between retries (default: {DEFAULT_RETRY_MAX_SECONDS})',
    )
    parser.add_argument(
        '--progress-interval-seconds',
        type=int,
        default=env_int('STAGE4_PROGRESS_INTERVAL_SECONDS', DEFAULT_PROGRESS_INTERVAL_SECONDS),
        help=(
            'Heartbeat logging interval for throughput/retry diagnostics; '
            'set to 0 to disable (default: '
            f'{DEFAULT_PROGRESS_INTERVAL_SECONDS})'
        ),
    )
    parser.add_argument(
        '--progress-stall-alert-seconds',
        type=int,
        default=env_int('STAGE4_PROGRESS_STALL_ALERT_SECONDS', DEFAULT_PROGRESS_STALL_ALERT_SECONDS),
        help=(
            'Emit explicit stall diagnostics when no file completes for this long while workers stay active '
            f'(default: {DEFAULT_PROGRESS_STALL_ALERT_SECONDS})'
        ),
    )
    parser.add_argument(
        '--max-pending-tasks',
        type=int,
        default=env_int('STAGE4_MAX_PENDING_TASKS', DEFAULT_MAX_PENDING_TASKS),
        help=(
            'Maximum number of submitted-but-not-yet-completed upload tasks held in memory at once '
            f'(default: {DEFAULT_MAX_PENDING_TASKS})'
        ),
    )
    parser.add_argument(
        '--comparison-summary',
        default=None,
        help='Stage 3 comparison-summary.json used for the pre-upload safety guard',
    )
    parser.add_argument(
        '--max-upload-fraction',
        type=float,
        default=None,
        help='Fail before uploading when pending distinct PUTs exceed this fraction of eligible local objects',
    )
    args = parser.parse_args()

    if args.workers < 1:
        parser.error('--workers must be >= 1')
    if args.retries < 0:
        parser.error('--retries must be >= 0')
    if args.retry_base_seconds <= 0:
        parser.error('--retry-base-seconds must be > 0')
    if args.retry_max_seconds <= 0:
        parser.error('--retry-max-seconds must be > 0')
    if args.progress_interval_seconds < 0:
        parser.error('--progress-interval-seconds must be >= 0')
    if args.progress_stall_alert_seconds < 0:
        parser.error('--progress-stall-alert-seconds must be >= 0')
    if args.max_pending_tasks < args.workers:
        parser.error('--max-pending-tasks must be >= --workers')
    if (args.comparison_summary is None) != (args.max_upload_fraction is None):
        parser.error('--comparison-summary and --max-upload-fraction must be provided together')
    if args.max_upload_fraction is not None and not 0 <= args.max_upload_fraction <= 1:
        parser.error('--max-upload-fraction must be between 0 and 1')

    puts_file = os.path.join(LOCAL_SCRATCH_DIR, 'puts.txt')
    activity_log_file = os.path.join(LOCAL_SCRATCH_DIR, 'activity.log')
    try:
        file_list = load_put_keys(puts_file)
    except Exception as error:
        print(
            (
                f'Fatal stage4 error: unable to load PUT keys from {puts_file}. '
                f'Error: {error}'
            ),
            file=sys.stderr,
            flush=True,
        )
        sys.exit(EXIT_STAGE4_PUTS_LOAD_FAILURE)

    if args.comparison_summary is not None:
        try:
            validate_upload_fraction_guard(file_list, args.comparison_summary, args.max_upload_fraction)
        except UploadFractionGuardError as error:
            print(
                f'Fatal stage4 upload-fraction guard: {error}',
                file=sys.stderr,
                flush=True,
            )
            sys.exit(EXIT_STAGE4_UPLOAD_FRACTION_GUARD)
    random.shuffle(file_list)

    aws_max_attempts = env_int('STAGE4_AWS_MAX_ATTEMPTS', DEFAULT_AWS_MAX_ATTEMPTS)
    aws_retry_mode = os.getenv('STAGE4_AWS_RETRY_MODE', DEFAULT_AWS_RETRY_MODE)
    aws_max_pool_connections = env_int('STAGE4_AWS_MAX_POOL_CONNECTIONS', DEFAULT_AWS_MAX_POOL_CONNECTIONS)
    aws_region = os.getenv('STAGE4_AWS_REGION') or boto3.Session(profile_name=AWS_PROFILE or None).region_name or DEFAULT_AWS_REGION
    run_started_at_utc = utc_now_iso()
    activity_logger = ActivityLogger(activity_log_file, run_started_at_utc)

    print(
        (
            'Stage 4 config: '
            f'workers={args.workers}, retries={args.retries}, '
            f'retry_base_seconds={args.retry_base_seconds}, retry_max_seconds={args.retry_max_seconds}, '
            f'max_pending_tasks={args.max_pending_tasks}, '
            f'aws_max_attempts={aws_max_attempts}, aws_retry_mode={aws_retry_mode}, '
            f'aws_max_pool_connections={aws_max_pool_connections}, aws_region={aws_region}, '
            'upload_path=smart_open_multipart_only, '
            f'multipart_part_size_bytes={MULTIPART_PART_SIZE_BYTES}, '
            f'copy_chunk_bytes={COPY_CHUNK_BYTES}, '
            'destination_exists_precheck=head_object, '
            f'activity_log={activity_log_file}, '
            f'progress_interval_seconds={args.progress_interval_seconds}, '
            f'progress_stall_alert_seconds={args.progress_stall_alert_seconds}, '
            'shuffle_puts_order=true'
        ),
        flush=True,
    )

    try:
        try:
            process_result = process_files(
                file_list=file_list,
                glacier_bucket=GLACIER_BUCKET,
                max_workers=args.workers,
                max_pending_tasks=args.max_pending_tasks,
                retries=args.retries,
                retry_base_seconds=args.retry_base_seconds,
                retry_max_seconds=args.retry_max_seconds,
                progress_interval_seconds=args.progress_interval_seconds,
                progress_stall_alert_seconds=args.progress_stall_alert_seconds,
                activity_logger=activity_logger,
            )
            update_source_access_artifacts(process_result.get('source_access_bad_keys', []))
        finally:
            activity_logger.close()
    except Exception as error:
        print(
            f'Fatal stage4 runtime error: {type(error).__name__}: {error}',
            file=sys.stderr,
            flush=True,
        )
        sys.exit(EXIT_STAGE4_RUNTIME_FAILURE)

    sys.exit(EXIT_SUCCESS)


if __name__ == '__main__':
    main()

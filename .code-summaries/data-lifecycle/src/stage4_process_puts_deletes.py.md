# stage4_process_puts_deletes.py

**Path:** `data-lifecycle/src/stage4_process_puts_deletes.py`
**Module:** `data-lifecycle.src.stage4_process_puts_deletes`
**Feature Area:** `data-lifecycle`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Stage 4 parallel execution engine streaming object backups from Ceph/NRP S3 to AWS Glacier S3 using smart-open multipart streams, retry logic, error classification, and progress logging.

## Connections
- **Uses:** `SOURCE_GET_FAILED_AFTER_HEAD_SUCCESS` from `data-lifecycle.src.badkeys` — imports (static evidence).
- **Uses:** `append_source_get_failed_slack_section` from `data-lifecycle.src.badkeys` — imports (static evidence).
- **Uses:** `make_badkey_record` from `data-lifecycle.src.badkeys` — imports (static evidence).
- **Uses:** `merge_badkey_records` from `data-lifecycle.src.badkeys` — imports (static evidence).
- **Uses:** `read_badkeys_tsv` from `data-lifecycle.src.badkeys` — imports (static evidence).
- **Uses:** `source_get_failed_records` from `data-lifecycle.src.badkeys` — imports (static evidence).
- **Uses:** `write_badkeys_tsv` from `data-lifecycle.src.badkeys` — imports (static evidence).
- **Uses:** `is_retention_marker` from `data-lifecycle.src.lifecycle_controls` — imports (static evidence).
- **Uses:** `build_source_lookup_candidates` from `data-lifecycle.src.stage4_keys` — imports (static evidence).
- **Uses:** `load_put_keys` from `data-lifecycle.src.stage4_keys` — imports (static evidence).
- **Uses:** `normalize_bucket_object_key` from `data-lifecycle.src.stage4_keys` — imports (static evidence).
- **Shared data:** Reads manifests produced by `generate_puts_deletes.py`.
- **Shared data:** Imports key helpers from `stage4_keys.py` and badkey logging from `badkeys.py`.

## Dependencies
- `boto3` — external or unresolved local import; source import evidence.
- `botocore.config.Config` — external or unresolved local import; source import evidence.
- `botocore.exceptions.BotoCoreError` — external or unresolved local import; source import evidence.
- `botocore.exceptions.ClientError` — external or unresolved local import; source import evidence.
- `botocore.exceptions.ConnectionClosedError` — external or unresolved local import; source import evidence.
- `botocore.exceptions.EndpointConnectionError` — external or unresolved local import; source import evidence.
- `botocore.exceptions.ParamValidationError` — external or unresolved local import; source import evidence.
- `botocore.exceptions.ReadTimeoutError` — external or unresolved local import; source import evidence.
- `botocore.exceptions.SSLError` — external or unresolved local import; source import evidence.
- `smart_open` — external or unresolved local import; source import evidence.

## Classes
### UploadFractionGuardError(ValueError)
> Exception raised when puts count exceeds safety fraction of total inventory.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:70`
**Kind:** class. **Instantiated by:** data-lifecycle/src/stage4_process_puts_deletes.py:108 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:112 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:114 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:119 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:123 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:155 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:157 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:170 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:175 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:194 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:93 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:96 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None
### ActivityLogger()
> Thread-safe TSV writer recording individual transfer outcomes and timings.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:407`
**Kind:** class. **Instantiated by:** data-lifecycle/src/stage4_process_puts_deletes.py:1170 (named-call hint)
**Constructor:** `__init__(self, path, run_started_at_utc)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `_file_handle` | inferred at runtime | `open(path, 'a', encoding='utf8', newline='')` |
| `_lock` | inferred at runtime | `threading.Lock()` |
| `_writer` | inferred at runtime | `csv.DictWriter(self._file_handle, fieldnames=self.FIELDNAMES)` |
| `path` | inferred at runtime | `path` |
| `run_started_at_utc` | inferred at runtime | `run_started_at_utc` |
**Methods:**
#### `_upgrade_legacy_log_if_needed(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:430`
#### `record_event(self, bucket_key, uploaded_bucket_key, bytes_copied, glacier_bucket, result)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:468`
#### `close(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:482`
### ProgressStats()
> unclear — see source
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:487`
**Kind:** class. **Instantiated by:** data-lifecycle/src/stage4_process_puts_deletes.py:811 (named-call hint)
**Constructor:** `__init__(self, total_files)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `_lock` | inferred at runtime | `threading.Lock()` |
| `active_transfers` | inferred at runtime | `{}` |
| `completed` | inferred at runtime | `0` |
| `failure_count` | inferred at runtime | `0` |
| `last_completion_time` | inferred at runtime | `self.start_time` |
| `retry_count` | inferred at runtime | `0` |
| `retry_error_counts` | inferred at runtime | `Counter()` |
| `retry_sleep_seconds` | inferred at runtime | `0.0` |
| `start_time` | inferred at runtime | `time.monotonic()` |
| `stream_bytes` | inferred at runtime | `0` |
| `success_bytes` | inferred at runtime | `0` |
| `success_count` | inferred at runtime | `0` |
| `total_files` | inferred at runtime | `total_files` |
**Methods:**
#### `record_retry(self, error, sleep_seconds)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:503`
#### `record_completion(self, success, bytes_copied)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:509`
#### `record_transfer_start(self, source_key)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:520`
#### `record_transfer_progress(self, source_key, bytes_delta)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:529`
#### `record_transfer_end(self, source_key)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:540`
#### `snapshot(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:544`

## Functions
### `env_int(name, default)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:1063 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:1081 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:1091 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:1100 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:1165 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:1167 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:211 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:214 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:238 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:241 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:74`
### `env_float(name, default)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:1069 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:1075 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:81`
### `validate_upload_fraction_guard(file_list, comparison_summary_path, max_upload_fraction)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:1155 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:88`
### `build_s3_client()`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:226 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:203`
### `get_s3_client()`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:264 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:307 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:687 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:223`
### `build_source_s3_client()`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:249 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:230`
### `get_source_s3_client()`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:259 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:273 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:998 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:246`
### `open_source_object(source_url, mode)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:253`
### `head_object_exists(glacier_bucket, key, s3_client=None)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:263`
### `source_head_object_exists(bucket_key, source_s3_client=None)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:268`
### `find_head_visible_source_key(source_candidates, source_head_object_func=None, source_s3_client=None)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:768 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:277`
### `stream_upload(source_url, destination_url, source_opener=None, destination_opener=None, s3_client=None, multipart_part_size_bytes=None, copy_chunk_bytes=None, progress_callback=None)`
> Streams an object directly from source S3 to destination S3 using `smart_open` without local disk staging.
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:732 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:295`
### `is_retryable_error(error)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:704 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:764 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:334`
### `is_missing_source_error(error)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:284 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:703 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:761 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:765 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:365`
### `format_duration(total_seconds)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:616 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:385`
### `classify_error(error)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:507 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:392`
### `utc_now_iso()`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:1169 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:470 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:403`
### `compact_key(key, max_len=100)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:610 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:566`
### `progress_reporter(stats, interval_seconds, stop_event, stall_alert_seconds)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:572`
### `copy_file(source_key, glacier_bucket, retries, retry_base_seconds, retry_max_seconds, stats, head_object_func=None, source_opener=None, destination_opener=None, s3_client=None, source_s3_client=None, source_head_object_func=None, multipart_part_size_bytes=None, copy_chunk_bytes=None, sleep_func=time.sleep, uniform_func=random.uniform)`
> Handles source existence check, fallback candidate lookup, upload, and error handling for one key.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:657`
### `process_files(file_list, glacier_bucket, max_workers, max_pending_tasks, retries, retry_base_seconds, retry_max_seconds, progress_interval_seconds, progress_stall_alert_seconds, activity_logger)`
> Dispatches upload and delete tasks across ThreadPoolExecutor workers.
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:1194 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:798`
### `split_s3_uri(uri)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:997 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:984`
### `upload_primary_inventory_artifact(local_path, primary_inventory_path, source_s3_client=None)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:1038 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:991`
### `update_source_access_artifacts(source_access_bad_keys, source_s3_client=None)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:1206 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:1004`
### `main()`
> CLI entry point initializing S3 clients, validating safety guards, and running the transfer pool.
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:1221 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_process_puts_deletes.py:1051`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env `NRP_ENDPOINT`: S3 endpoint URL for Ceph storage (default: `https://s3.braingeneers.gi.ucsc.edu`). |
| Env `AWS_PROFILE`: AWS credential profile name (default: `aws-braingeneers-backups`). |
| Env `MAX_WORKERS`: ThreadPoolExecutor worker concurrency (default: 8). |
| Env `MAX_UPLOAD_FRACTION_GUARD`: Safety threshold preventing catastrophic mass-upload if inventory is corrupt. |
| `--puts-file PATH`: Path to file containing keys to upload. |
| `--deletes-file PATH`: Path to file containing keys to delete from Glacier. |
| `--dry-run`: Simulate operations without performing S3 writes. |

## Data Shapes
- Input: `puts.txt` (newline-delimited keys), `deletes.txt` (newline-delimited keys).
- Output: `activity.tsv` (records timestamp, status, key, size, duration), `badkeys.tsv`, console metrics.

## Notes
- Validates total upload fraction against guard threshold before initiating transfers.
- Retries transient S3 network and throttle errors with exponential backoff and jitter.

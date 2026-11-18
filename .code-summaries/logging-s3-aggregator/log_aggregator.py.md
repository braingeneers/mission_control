# log_aggregator.py

**Path:** `logging-s3-aggregator/log_aggregator.py`
**Module:** `logging-s3-aggregator.log_aggregator`
**Feature Area:** `logging-s3-aggregator`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Periodic aggregation service that scans singleton S3 telemetry log files, combines up to 100 entries per batch into cumulative log TSVs, and deletes processed singles.

## Connections
- **Shared data:** Aggregates log files created by `logging-s3/log.py`.
- **Shared data:** Uses `braingeneers.utils.smart_open_braingeneers`.

## Dependencies
- `braingeneers.utils.common_utils._lazy_init_s3_client` — external or unresolved local import; source import evidence.
- `braingeneers.utils.s3wrangler` — external or unresolved local import; source import evidence.
- `braingeneers.utils.smart_open_braingeneers` — external or unresolved local import; source import evidence.
- `tenacity.retry` — external or unresolved local import; source import evidence.
- `tenacity.stop_after_attempt` — external or unresolved local import; source import evidence.
- `tenacity.wait_exponential` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
### `log_to_stderr(retry_state)`
> Print our retries to the screen so that we know what's going on.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `logging-s3-aggregator/log_aggregator.py:23`
### `delete_s3_object(uri: str)`
> Deletes an S3 object with exponential retry on network/throttle error.
> **Called by:** logging-s3-aggregator/log_aggregator.py:121 (named-call hint). **Side effects:** unclear — see source.
**Source:** `logging-s3-aggregator/log_aggregator.py:30`
### `batch_100_logs(singletons: str)`
> Groups up to 100 single log files per experiment UUID.
> **Called by:** logging-s3-aggregator/log_aggregator.py:89 (named-call hint). **Side effects:** unclear — see source.
**Source:** `logging-s3-aggregator/log_aggregator.py:36`
### `format_log_entries(log_entries: dict, header_keys: list)`
> Parses and sorts log lines chronologically by timestamp.
> **Called by:** logging-s3-aggregator/log_aggregator.py:110 (named-call hint). **Side effects:** unclear — see source.
**Source:** `logging-s3-aggregator/log_aggregator.py:51`
### `combine_logs(singletons: str, combined: str)`
> Appends formatted entries to cumulative S3 log file and deletes originals.
> **Called by:** logging-s3-aggregator/log_aggregator.py:149 (named-call hint); logging-s3-aggregator/log_aggregator.py:150 (named-call hint); logging-s3-aggregator/log_aggregator.py:151 (named-call hint). **Side effects:** write call (static hint).
**Source:** `logging-s3-aggregator/log_aggregator.py:81`
### `main()`
> Main polling loop scanning S3 bucket and executing batch aggregation.
> **Called by:** logging-s3-aggregator/log_aggregator.py:158 (named-call hint). **Side effects:** unclear — see source.
**Source:** `logging-s3-aggregator/log_aggregator.py:125`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| S3 logs prefix: `s3://braingeneers/logs/` |
| Batch size: 100 log files per merge cycle. |

## Data Shapes
- Input: S3 individual log TSVs (`s3://braingeneers/logs/<UUID>/<file>.tsv`).
- Output: Aggregated log file `s3://braingeneers/logs/<UUID>/log.tsv`.

## Notes
- Uses `s3wrangler` and boto3 to list and batch S3 objects.
- Employs tenacity exponential backoff retries when deleting merged objects from S3.

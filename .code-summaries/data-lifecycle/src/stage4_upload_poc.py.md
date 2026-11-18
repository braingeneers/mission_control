# stage4_upload_poc.py

**Path:** `data-lifecycle/src/stage4_upload_poc.py`
**Module:** `data-lifecycle.src.stage4_upload_poc`
**Feature Area:** `data-lifecycle`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Proof-of-concept benchmarking script comparing throughput and memory consumption across smart-open, AWS CLI, and rclone for streaming large dataset uploads to Glacier.

## Connections
- **Shared data:** Informed the design and chunk sizing decisions in `stage4_process_puts_deletes.py`.

## Dependencies
- `boto3` — external or unresolved local import; source import evidence.
- `botocore.config.Config` — external or unresolved local import; source import evidence.
- `smart_open` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
### `parse_args()`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_upload_poc.py:240 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_upload_poc.py:28`
### `build_client(profile_name, region_name, max_attempts, retry_mode)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_upload_poc.py:132 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_upload_poc.py:117`
### `upload_with_smart_open(args, part_size_bytes, chunk_size_bytes)`
> Transfers file using `smart_open.open` streaming with multipart upload parameters.
> **Called by:** data-lifecycle/src/stage4_upload_poc.py:263 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/src/stage4_upload_poc.py:131`
### `upload_with_aws_cli(args)`
> Invokes `aws s3 cp` subprocess with configured profile and region.
> **Called by:** data-lifecycle/src/stage4_upload_poc.py:265 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_upload_poc.py:178`
### `parse_s3_url(url)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_upload_poc.py:207 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_upload_poc.py:196`
### `upload_with_rclone(args)`
> Invokes `rclone copyto` subprocess configured with AWS credentials.
> **Called by:** data-lifecycle/src/stage4_upload_poc.py:267 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_upload_poc.py:206`
### `main()`
> CLI entry point running chosen transfer benchmark.
> **Called by:** data-lifecycle/src/stage4_upload_poc.py:273 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_upload_poc.py:239`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| `--source URI`: Source file path or S3 URI. |
| `--target URI`: Destination S3 URI. |
| `--uploader [smart-open\|aws-cli\|rclone]`: Selected transfer engine implementation. |
| `--part-size-mib INT`: Multipart upload chunk size in MiB (default: 64). |
| `--aws-profile NAME`: AWS CLI credential profile name. |

## Data Shapes
- Input: Source file/stream.
- Output: Transferred S3 object and stdout benchmark performance timings (MiB/s, elapsed seconds).

## Notes
- Evaluates memory and process overhead for massive file transfers to AWS S3 Glacier Deep Archive.

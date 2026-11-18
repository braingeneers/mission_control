# update_metadata.py

**Path:** `job-h5repack/update_metadata.py`
**Module:** `job-h5repack.update_metadata`
**Feature Area:** `job-h5repack`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Post-processing task updater acquiring an S3 distributed lock to update electrophysiology experiment metadata when an HDF5 file has been converted to row-major layout.

## Connections
- **Shared data:** Updates metadata files after files processed by `job-h5repack` workers.
- **Shared data:** Uses `braingeneers.data.datasets_electrophysiology.save_metadata`.

## Dependencies
- `braingeneers.data.datasets_electrophysiology` — external or unresolved local import; source import evidence.
- `braingeneers.iot.messaging.MessageBroker` — external or unresolved local import; source import evidence.
- `braingeneers.utils.common_utils` — external or unresolved local import; source import evidence.
- `tenacity.retry` — external or unresolved local import; source import evidence.
- `tenacity.stop_after_attempt` — external or unresolved local import; source import evidence.
- `tenacity.wait_fixed` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
### `main(uuid, file, rowmajor_file)`
> Acquires distributed lock, verifies rowmajor file existence on S3, updates block path to rowmajor, and persists metadata.
> **Called by:** job-h5repack/update_metadata.py:54 (named-call hint). **Side effects:** unclear — see source.
**Source:** `job-h5repack/update_metadata.py:9`
### `save_metadata(metadata)`
> Persists modified dataset metadata dict to S3 with tenacity retries.
> **Called by:** job-h5repack/update_metadata.py:39 (named-call hint). **Side effects:** unclear — see source.
**Source:** `job-h5repack/update_metadata.py:44`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| `--uuid -u UUID`: Dataset UUID. |
| `--file -f PATH`: Original block file path in metadata. |
| `--rowmajor-file -r PATH`: New rowmajor file path replacing original. |

## Data Shapes
- Input/Output: JSON metadata record loaded from and saved to S3 ephys directory.

## Notes
- Uses `MessageBroker().get_lock(uuid)` context manager for concurrency safety.
- Retries metadata save on network failure using tenacity retry decorator.

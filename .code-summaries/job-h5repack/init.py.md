# init.py

**Path:** `job-h5repack/init.py`
**Module:** `job-h5repack.init`
**Feature Area:** `job-h5repack`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Initialization CLI script for electrophysiology h5repack jobs, reading dataset metadata from S3 and populating an MQTT message queue with data files to repack.

## Connections
- **Shared data:** Seeds task queue consumed by `job-h5repack/get_task.py`.
- **Shared data:** Uses `braingeneers.data.datasets_electrophysiology`.

## Dependencies
- `braingeneers.data.datasets_electrophysiology` — external or unresolved local import; source import evidence.
- `braingeneers.iot.messaging.MessageBroker` — external or unresolved local import; source import evidence.
- `braingeneers.utils.common_utils` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
### `main(uuid: str, delete_queue: bool=True)`
> Clears optional existing queue, loads experiment blocks, and enqueues all raw data files.
> **Called by:** job-h5repack/init.py:29 (named-call hint). **Side effects:** unclear — see source.
**Source:** `job-h5repack/init.py:8`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| `--uuid -u UUID`: Electrophysiology experiment UUID. |
| `--no-delete-queue -n`: Preserve existing queue without clearing. |

## Data Shapes
- Input: Dataset metadata loaded via `braingeneers.data.datasets_electrophysiology.load_metadata`.
- Output: Enqueues data file paths into queue `job-h5repack-{uuid}`.

## Notes
- Constructs S3 paths using `common_utils.get_basepath() / 'ephys' / uuid / block['path']`.

# get_task.py

**Path:** `job-h5repack/get_task.py`
**Module:** `job-h5repack.get_task`
**Feature Area:** `job-h5repack`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Worker task dequeue script for h5repack batch processing; fetches the next electrophysiology HDF5 data file from an MQTT message queue.

## Connections
- **Shared data:** Reads tasks enqueued by `job-h5repack/init.py`.
- **Shared data:** Uses `braingeneers.iot.messaging.MessageBroker`.

## Dependencies
- `braingeneers.data.datasets_electrophysiology` — external or unresolved local import; source import evidence.
- `braingeneers.iot.messaging.MessageBroker` — external or unresolved local import; source import evidence.
- `braingeneers.utils.common_utils` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
None

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env `UUID`: Target electrophysiology dataset UUID. |

## Data Shapes
- Input: Queue messages from `job-h5repack-{uuid}` containing S3 file paths.
- Output: Prints S3 file path to stdout, or prints `END` when queue is empty.

## Notes
- Runs non-blocking queue fetch via `MessageBroker().get_queue(queue_name).get(block=False)`.

# log.py

**Path:** `logging-s3/log.py`
**Module:** `logging-s3.log`
**Feature Area:** `logging-s3`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Telemetry daemon listening indefinitely to MQTT topic `telemetry/#` and streaming individual message payloads to S3 as single-message TSV files.

## Connections
- **Shared data:** Receives messages published by `experiment-dash` and IoT edge hardware.
- **Shared data:** Individual S3 log files are aggregated by `logging-s3-aggregator/log_aggregator.py`.

## Dependencies
- `braingeneers.iot.messaging` — external or unresolved local import; source import evidence.
- `braingeneers.utils.smart_open_braingeneers` — external or unresolved local import; source import evidence.
- `pytz` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
### `main()`
> Infinite event loop connecting to MQTT broker, subscribing to telemetry, and writing S3 TSVs.
> **Called by:** logging-s3/log.py:76 (named-call hint). **Side effects:** write call (static hint).
**Source:** `logging-s3/log.py:21`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| MQTT topic wildcard: `telemetry/#` |
| S3 destination prefix: `s3://braingeneers/logs/<UUID>/` |

## Data Shapes
- Input: MQTT message containing timestamp and payload.
- Output: TSV file per message written to S3 with columns `timestamp\tmessage`.

## Notes
- Topic format: `telemetry/{uuid}/log/{device}/{cmnd}`.
- Generates unique UUID for each singleton TSV file to prevent S3 overwrite collisions.

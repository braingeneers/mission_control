# stage4_keys.py

**Path:** `data-lifecycle/src/stage4_keys.py`
**Module:** `data-lifecycle.src.stage4_keys`
**Feature Area:** `data-lifecycle`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Provides S3 object key sanitization, URL decoding, rclone special dot-segment normalization, and source lookup candidate generation for Stage 4 backup transfers.

## Connections
- **Used by:** `data-lifecycle.src.generate_puts_deletes` — import consumer hint; not a proven runtime call.
- **Used by:** `data-lifecycle.src.stage4_process_puts_deletes` — import consumer hint; not a proven runtime call.
- **Shared data:** Imported by `generate_puts_deletes.py` and `stage4_process_puts_deletes.py`.

## Dependencies
None

## Classes
None

## Functions
### `normalize_put_key(raw_key)`
> Cleans leading slashes, s3 schemes, and stray carriage returns from put manifest keys.
> **Called by:** data-lifecycle/src/stage4_keys.py:73 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_keys.py:10`
### `normalize_bucket_object_key(raw_key)`
> Normalizes bucket-relative object keys, resolving percent-encodings.
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:186 (named-call hint); data-lifecycle/src/stage4_keys.py:129 (named-call hint); data-lifecycle/src/stage4_keys.py:32 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:269 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_keys.py:35`
### `normalize_object_key(object_key)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_keys.py:47 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_keys.py:53`
### `load_put_keys(puts_file)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:1141 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_keys.py:63`
### `normalize_rclone_dot_segments(object_key)`
> Translates rclone full-width dot characters to ASCII dots.
> **Called by:** data-lifecycle/src/stage4_keys.py:58 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_keys.py:94`
### `denormalize_rclone_dot_segments(object_key)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_keys.py:136 (named-call hint); data-lifecycle/src/stage4_keys.py:138 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_keys.py:107`
### `restore_embedded_s3_scheme(object_key)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_keys.py:59 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_keys.py:120`
### `collapse_embedded_s3_scheme(object_key)`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_keys.py:137 (named-call hint); data-lifecycle/src/stage4_keys.py:138 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_keys.py:124`
### `build_source_lookup_candidates(source_key)`
> Generates list of fallback key variations to probe on source Ceph S3.
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:675 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/stage4_keys.py:128`

## Config / CLI
None

## Data Shapes
- Input: Raw S3 object keys (strings or lines from put lists).
- Output: Canonical normalized S3 keys or candidate key lists.

## Notes
- Handles rclone Unicode full-width dot replacements (`．` for '.' and `．．` for '..').
- Strips carriage return symbols (`␍`) and extraneous leading `s3://` prefixes.

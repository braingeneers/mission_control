# lifecycle_controls.py

**Path:** `data-lifecycle/src/lifecycle_controls.py`
**Module:** `data-lifecycle.src.lifecycle_controls`
**Feature Area:** `data-lifecycle`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Implements control-object semantics for dataset retention, parsing zero-byte marker objects for atomic directories and individual files to compute effective last-modified dates.

## Connections
- **Used by:** `data-lifecycle.src.generate_puts_deletes` — import consumer hint; not a proven runtime call.
- **Used by:** `data-lifecycle.src.stage4_process_puts_deletes` — import consumer hint; not a proven runtime call.
- **Uses:** `FILE_RETENTION_SUFFIX` from `data-lifecycle.src.lifecycle_constants` — imports (static evidence).
- **Uses:** `NOBACKUP_MARKER_NAME` from `data-lifecycle.src.lifecycle_constants` — imports (static evidence).
- **Uses:** `RETENTION_MARKER_NAME` from `data-lifecycle.src.lifecycle_constants` — imports (static evidence).
- **Shared data:** Imports marker constants from `lifecycle_constants.py`.
- **Shared data:** Imported by `generate_puts_deletes.py`.

## Dependencies
- `pandas` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
### `normalize_atomic_directories(paths: Iterable[str] | None) -> list[str]`
> Normalizes atomic folder path prefixes with trailing slashes.
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:311 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:430 (named-call hint); data-lifecycle/src/lifecycle_controls.py:180 (named-call hint); data-lifecycle/src/lifecycle_controls.py:40 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/lifecycle_controls.py:26`
### `atomic_group_for_key(bucket_key: str, atomic_directories: Iterable[str] | None) -> str | None`
> Maps an S3 object key to its parent atomic dataset directory if applicable.
> **Called by:** data-lifecycle/src/lifecycle_controls.py:113 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/lifecycle_controls.py:38`
### `atomic_retention_marker(group_prefix: str) -> str`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/lifecycle_controls.py:58`
### `file_retention_marker(bucket_key: str) -> str`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/lifecycle_controls.py:65`
### `is_retention_marker(bucket_key: str) -> bool`
> Checks whether a key represents a folder or file retention marker object.
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:267 (named-call hint); data-lifecycle/src/lifecycle_controls.py:82 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:139 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:140 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:692 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/lifecycle_controls.py:72`
### `is_nobackup_marker(bucket_key: str) -> bool`
> Checks whether a key represents a `.NOBACKUP` marker.
> **Called by:** data-lifecycle/src/lifecycle_controls.py:82 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/lifecycle_controls.py:77`
### `is_lifecycle_control_key(bucket_key: str) -> bool`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/lifecycle_controls.py:81`
### `lifecycle_control_mask(keys: pd.Series) -> pd.Series`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:362 (named-call hint); data-lifecycle/src/lifecycle_controls.py:126 (named-call hint); data-lifecycle/src/lifecycle_controls.py:169 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/lifecycle_controls.py:85`
### `retention_marker_mask(keys: pd.Series) -> pd.Series`
> unclear — see source
> **Called by:** data-lifecycle/src/lifecycle_controls.py:153 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/lifecycle_controls.py:93`
### `retention_marker_target(marker_key: str, atomic_directories: Iterable[str] | None) -> tuple[str, str] | None`
> Return ``(scope, target)`` for a valid retention marker.
> **Called by:** data-lifecycle/src/lifecycle_controls.py:159 (named-call hint); data-lifecycle/src/lifecycle_controls.py:235 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/lifecycle_controls.py:98`
### `scientific_inventory(inventory: pd.DataFrame) -> pd.DataFrame`
> Return inventory rows that represent user data, not control objects.
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:261 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:279 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:373 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:374 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:432 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:442 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:445 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/lifecycle_controls.py:123`
### `apply_effective_last_modified(inventory: pd.DataFrame, atomic_directories: Iterable[str] | None, *, authoritative_markers: pd.DataFrame | None=None) -> pd.DataFrame`
> Joins retention marker timestamps against scientific objects to derive renewal dates.
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:312 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/lifecycle_controls.py:129`
### `marker_upload_mask(local_inventory: pd.DataFrame, glacier_inventory: pd.DataFrame, atomic_directories: Iterable[str] | None=None) -> pd.Series`
> Filters DataFrame for control markers that need synchronization to Glacier.
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:367 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/lifecycle_controls.py:215`

## Config / CLI
None

## Data Shapes
- Pandas DataFrame: Takes inventories containing `Key` and `LastModifiedDate`; returns updated DataFrames with `EffectiveLastModified`.

## Notes
- Scientific files are never rewritten to renew retention; a zero-byte marker `<dataset>/DATA_LIFECYCLE_RETENTION` or `<file>.DATA_LIFECYCLE_RETENTION` carries the timestamp.
- Marker file contents and user metadata are intentionally ignored; only S3 `LastModified` is used.

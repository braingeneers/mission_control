# generate_puts_deletes.py

**Path:** `data-lifecycle/src/generate_puts_deletes.py`
**Module:** `data-lifecycle.src.generate_puts_deletes`
**Feature Area:** `data-lifecycle`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Stage 3 comparison engine comparing Ceph/NRP scientific storage inventory against Glacier backup inventory; generates put lists for unbacked files, delete lists for expired files per policy, and badkeys lists.

## Connections
- **Used by:** `data-lifecycle.src.generate_cleanup_report` — import consumer hint; not a proven runtime call.
- **Uses:** `make_badkey_record` from `data-lifecycle.src.badkeys` — imports (static evidence).
- **Uses:** `write_badkeys_tsv` from `data-lifecycle.src.badkeys` — imports (static evidence).
- **Uses:** `apply_effective_last_modified` from `data-lifecycle.src.lifecycle_controls` — imports (static evidence).
- **Uses:** `is_retention_marker` from `data-lifecycle.src.lifecycle_controls` — imports (static evidence).
- **Uses:** `lifecycle_control_mask` from `data-lifecycle.src.lifecycle_controls` — imports (static evidence).
- **Uses:** `marker_upload_mask` from `data-lifecycle.src.lifecycle_controls` — imports (static evidence).
- **Uses:** `normalize_atomic_directories` from `data-lifecycle.src.lifecycle_controls` — imports (static evidence).
- **Uses:** `scientific_inventory` from `data-lifecycle.src.lifecycle_controls` — imports (static evidence).
- **Uses:** `normalize_bucket_object_key` from `data-lifecycle.src.stage4_keys` — imports (static evidence).
- **Shared data:** Imports `make_badkey_record` and `write_badkeys_tsv` from `badkeys.py`.
- **Shared data:** Imports `normalize_bucket_object_key` from `stage4_keys.py`.
- **Shared data:** Imports `apply_effective_last_modified`, `lifecycle_control_mask`, and `scientific_inventory` from `lifecycle_controls.py`.
- **Shared data:** Consumed downstream by `stage4_process_puts_deletes.py`.

## Dependencies
- `pandas` — external or unresolved local import; source import evidence.
- `yaml` — external or unresolved local import; source import evidence.

## Classes
### Stage3ProgressReporter()
> Background thread periodically reporting processed row counts and RSS memory consumption.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:41`
**Kind:** class. **Instantiated by:** data-lifecycle/src/generate_puts_deletes.py:749 (named-call hint)
**Constructor:** `__init__(self, interval_seconds=DEFAULT_PROGRESS_INTERVAL_SECONDS, memory_reader=read_process_memory_mib)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `interval_seconds` | inferred at runtime | `max(0.0, float(interval_seconds))` |
| `lock` | inferred at runtime | `threading.Lock()` |
| `memory_reader` | inferred at runtime | `memory_reader` |
| `phase` | inferred at runtime | `'starting'` |
| `started_at` | inferred at runtime | `time.monotonic()` |
| `stop_event` | inferred at runtime | `threading.Event()` |
| `thread` | inferred at runtime | `None` |
**Methods:**
#### `start(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:51`
#### `set_phase(self, phase, **details)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:57`
#### `_run(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:64`
#### `stop(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:78`

## Functions
### `read_process_memory_mib()`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:27`
### `parse_arguments()`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:862 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:84`
### `load_config_file(config_path)`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:619 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:754 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:131`
### `load_inventories(prp_inventory_path, aws_inventory_path, stats=None)`
> Loads scientific and backup S3 inventory files into memory-efficient Pandas DataFrames.
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:635 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:760 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:139`
### `build_comparison_summary(prp_inventory, aws_inventory, puts, deletes, bad_keys, no_backup_prefixes, inventory_stats=None)`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:828 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:252`
### `write_comparison_summary(output_path, summary)`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:855 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/src/generate_puts_deletes.py:295`
### `apply_last_modified_updates(prp_inventory, config, *, authoritative_markers=None)`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:636 (named-call hint); data-lifecycle/src/generate_cleanup_report.py:637 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:770 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:775 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:310`
### `find_no_backup_prefixes(prp_inventory: pd.DataFrame)`
> Scans inventory for `.NOBACKUP` marker files and returns prefix list to exclude.
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:435 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:795 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:319`
### `calculate_expire_date(expire_days)`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:790 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:326`
### `get_required_config_value(config, section, *candidate_keys)`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:783 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:787 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:792 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:330`
### `parse_days(value, config_key)`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:782 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:786 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:791 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:340`
### `generate_put_and_delete_lists(primary_inventory_df: pd.DataFrame, glacier_inventory_df: pd.DataFrame, expire_date, no_backup_prefixes=None, atomic_directories=None)`
> Core differential algorithm determining new puts, modified puts, and expired deletes.
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:799 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:347`
### `derive_atomic_group_info(bucket_key, atomic_directories)`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:477 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:382`
### `derive_folder_group(bucket_key, depth=3)`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:483 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:403`
### `build_cleanup_window_entries(primary_inventory_df: pd.DataFrame, glacier_inventory_df: pd.DataFrame, s3_expire_days, cold_storage_expire_days, notification_days, atomic_directories, now_utc=None)`
> Filters expired items within specified notification and deletion grace windows.
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:643 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:808 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:414`
### `build_cleanup_summary(cleanup_window_df: pd.DataFrame)`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:821 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:495`
### `build_cleanup_slack_message(cleanup_window_df: pd.DataFrame, cleanup_summary_df: pd.DataFrame, notification_days, now_utc=None, max_groups_per_phase=12, columns_per_row=3)`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:822 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:529`
### `output_puts_deletes_and_notifications(puts, deletes, bad_keys, notifications, cleanup_window, cleanup_summary, cleanup_slack_message, puts_output_filepath=None, deletes_output_filepath=None, bad_keys_output_filepath=None, notifications_output_filepath=None, cleanup_window_output_filepath=None, cleanup_summary_output_filepath=None, cleanup_slack_message_output_filepath=None)`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:838 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/src/generate_puts_deletes.py:645`
### `main(config: str, prp_inventory: str, aws_inventory: str, puts_output: str, deletes_output: str, bad_keys_output: str, notifications_output: str, cleanup_window_output: str, cleanup_summary_output: str, cleanup_slack_message_output: str, comparison_summary_output: str=None, progress_interval_seconds: float=DEFAULT_PROGRESS_INTERVAL_SECONDS)`
> CLI entry point running Stage 3 comparison pipeline.
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:863 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_puts_deletes.py:737`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| `--config PATH`: Path to `data-lifecycle.yaml` configuration file. |
| `--scientific-inventory PATH`: Path to scientific storage inventory CSV(.gz). |
| `--backup-inventory PATH`: Path to Glacier backup storage inventory CSV(.gz). |
| `--output-dir PATH`: Output directory for generated manifests. |
| `--progress-interval SECONDS`: Interval for logging memory and row processing progress. |

## Data Shapes
- Input: Dataframe of scientific objects (`[Key, Size, LastModifiedDate]`) and backup objects (`[Key, Size, LastModifiedDate]`).
- Output: `puts.txt`, `deletes.txt`, `badkeys.tsv`, `cleanup_window_entries.json`, `comparison_summary.json`.

## Notes
- Tracks peak RSS memory usage via `/proc/self/status` or ps.
- Applies atomic directory groupings so multi-file scientific runs expire or retain together.
- Respects `.NOBACKUP` marker prefixes to prune entire directory trees from Glacier backup.

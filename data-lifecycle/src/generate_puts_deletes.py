import argparse
import json
import math
import os
import re
import threading
import time
import pandas as pd
import yaml
from badkeys import make_badkey_record, write_badkeys_tsv
from datetime import datetime, timedelta, timezone
from stage4_keys import normalize_bucket_object_key
from lifecycle_controls import (
    apply_effective_last_modified,
    is_retention_marker,
    lifecycle_control_mask,
    marker_upload_mask,
    normalize_atomic_directories,
    scientific_inventory,
)
from urllib.parse import unquote

CONTROL_CHAR_PATTERN = re.compile(r'[\x00-\x1F\x7F\u2400-\u2426]')
DEFAULT_PROGRESS_INTERVAL_SECONDS = 60


def read_process_memory_mib():
    values = {'rss_mib': 0.0, 'peak_rss_mib': 0.0}
    try:
        with open('/proc/self/status', 'r', encoding='utf8') as status_file:
            for line in status_file:
                if line.startswith('VmRSS:'):
                    values['rss_mib'] = int(line.split()[1]) / 1024
                elif line.startswith('VmHWM:'):
                    values['peak_rss_mib'] = int(line.split()[1]) / 1024
    except (OSError, ValueError, IndexError):
        pass
    return values


class Stage3ProgressReporter:
    def __init__(self, interval_seconds=DEFAULT_PROGRESS_INTERVAL_SECONDS, memory_reader=read_process_memory_mib):
        self.interval_seconds = max(0.0, float(interval_seconds))
        self.memory_reader = memory_reader
        self.started_at = time.monotonic()
        self.phase = 'starting'
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.thread = None

    def start(self):
        if self.interval_seconds <= 0:
            return
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def set_phase(self, phase, **details):
        with self.lock:
            self.phase = phase
        detail_text = ' '.join(f'{key}={value}' for key, value in details.items())
        suffix = f' {detail_text}' if detail_text else ''
        print(f'[stage3][progress] phase={phase} status=started{suffix}', flush=True)

    def _run(self):
        while not self.stop_event.wait(self.interval_seconds):
            with self.lock:
                phase = self.phase
            memory = self.memory_reader()
            elapsed = max(0.0, time.monotonic() - self.started_at)
            print(
                (
                    f'[stage3][heartbeat] phase={phase} elapsed_seconds={elapsed:.0f} '
                    f'rss_mib={memory["rss_mib"]:.1f} peak_rss_mib={memory["peak_rss_mib"]:.1f}'
                ),
                flush=True,
            )

    def stop(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=max(1.0, self.interval_seconds + 1.0))


def parse_arguments():
    parser = argparse.ArgumentParser(description='Generate PUT and DELETE lists based on S3 and Glacier inventories.')
    parser.add_argument('--config', type=str, required=True, help='Path to data lifecycle configuration file')
    parser.add_argument('--prp-inventory', type=str, required=True, help='Path to NRP/S3 inventory file')
    parser.add_argument('--aws-inventory', type=str, required=True, help='Path to AWS/Glacier/S3 inventory file')
    parser.add_argument('--puts-output', type=str, default=None, help='Path to output PUTs file')
    parser.add_argument('--deletes-output', type=str, default=None, help='Path to output DELETEs file')
    parser.add_argument('--notifications-output', type=str, default=None, help='Path to output notifications file')
    parser.add_argument(
        '--badkeys-output',
        type=str,
        default=None,
        help='Path to output detected bad keys (control-character keys excluded from processing)',
    )
    parser.add_argument(
        '--cleanup-window-output',
        type=str,
        default=None,
        help='Path to output cleanup schedule entries due within notification window',
    )
    parser.add_argument(
        '--cleanup-summary-output',
        type=str,
        default=None,
        help='Path to output aggregated cleanup summary for long lists',
    )
    parser.add_argument(
        '--cleanup-slack-message-output',
        type=str,
        default=None,
        help='Path to output proposed Slack message text',
    )
    parser.add_argument(
        '--comparison-summary-output',
        type=str,
        default=None,
        help='Path to the machine-readable inventory comparison summary',
    )
    parser.add_argument(
        '--progress-interval-seconds',
        type=float,
        default=float(os.getenv('STAGE3_PROGRESS_INTERVAL_SECONDS', DEFAULT_PROGRESS_INTERVAL_SECONDS)),
        help='Heartbeat interval while Stage 3 is processing; set to 0 to disable',
    )
    return parser.parse_args()


def load_config_file(config_path):
    with open(config_path, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)


def load_inventories(prp_inventory_path, aws_inventory_path, stats=None):
    stats = stats if stats is not None else {}
    try:
        prp_inventory_raw = pd.read_csv(
            prp_inventory_path,
            header=None,
            dtype=str,
            keep_default_na=False,
        )
    except pd.errors.EmptyDataError:
        prp_inventory_raw = pd.DataFrame(columns=['LastModified', 'BucketKey', 'Size'])
    stats['nrp_input_rows'] = int(len(prp_inventory_raw))

    if prp_inventory_raw.shape[1] == 2:
        prp_inventory_raw.columns = ['LastModified', 'BucketKey']
        prp_inventory_raw['Size'] = pd.NA
    elif prp_inventory_raw.shape[1] == 3:
        prp_inventory_raw.columns = ['LastModified', 'BucketKey', 'Size']
    else:
        raise ValueError(
            f"Unexpected NRP inventory column count ({prp_inventory_raw.shape[1]}). "
            "Expected either 2 columns (LastModified,BucketKey) "
            "or 3 columns (LastModified,BucketKey,Size)."
        )

    prp_inventory_raw['LastModified'] = pd.to_datetime(prp_inventory_raw['LastModified'], errors='coerce', utc=True)
    prp_inventory_raw['Size'] = pd.to_numeric(prp_inventory_raw['Size'], errors='coerce').astype('Int64')
    prp_inventory = prp_inventory_raw

    aws_inventory = pd.read_csv(
        aws_inventory_path,
        names=['Bucket', 'BucketKey', 'Size', 'LastModified', 'StorageClass'],
        parse_dates=['LastModified'],
    )
    stats['aws_input_rows'] = int(len(aws_inventory))
    aws_inventory['LastModified'] = pd.to_datetime(aws_inventory['LastModified'], errors='coerce', utc=True)
    # AWS inventory keys are URL-encoded for special characters (for example %40, %20, %28).
    # Decode once so key comparisons with NRP inventory use canonical object-key strings.
    aws_inventory['BucketKey'] = aws_inventory['BucketKey'].map(
        lambda value: unquote(value) if isinstance(value, str) else value
    )

    def normalize_inventory_keys(df, inventory_name):
        filtered = df.copy()
        original_bucket_keys = filtered['BucketKey'].astype('string')
        stripped_bucket_keys = original_bucket_keys.str.strip()
        normalized_bucket_keys = stripped_bucket_keys.map(
            lambda value: normalize_bucket_object_key(value) if isinstance(value, str) and value else value
        )
        changed_mask = (
            stripped_bucket_keys.notna() &
            normalized_bucket_keys.notna() &
            (stripped_bucket_keys != normalized_bucket_keys)
        )
        changed = int(changed_mask.sum())
        stats[f'{inventory_name.lower()}_normalized_key_rows'] = changed
        if changed > 0:
            print(
                f"Normalized {changed} {inventory_name} inventory key(s) for canonical comparison "
                "(rclone dot segments and embedded s3:/ text)."
            )
        filtered['BucketKey'] = normalized_bucket_keys.astype('string')
        return filtered

    prp_inventory = normalize_inventory_keys(prp_inventory, 'NRP')
    aws_inventory = normalize_inventory_keys(aws_inventory, 'AWS')

    def drop_prefix_marker_rows(df, inventory_name):
        filtered = df.copy()
        bucket_keys = filtered['BucketKey'].astype('string')
        normalized_bucket_keys = bucket_keys.str.strip()
        drop_empty = normalized_bucket_keys.isna() | (normalized_bucket_keys.str.len() == 0)
        drop_prefix_markers = normalized_bucket_keys.str.endswith('/', na=False)
        drop_mask = drop_empty | drop_prefix_markers
        dropped = int(drop_mask.sum())
        stats[f'{inventory_name.lower()}_prefix_marker_or_empty_rows'] = dropped
        if dropped > 0:
            print(
                f"Skipping {dropped} {inventory_name} inventory row(s) with empty keys "
                "or prefix-marker keys ending in '/'."
            )
        filtered = filtered.loc[~drop_mask].copy()
        filtered['BucketKey'] = normalized_bucket_keys.loc[~drop_mask].astype('string')
        return filtered

    prp_inventory = drop_prefix_marker_rows(prp_inventory, 'NRP')
    aws_inventory = drop_prefix_marker_rows(aws_inventory, 'AWS')

    def split_bad_keys(df, inventory_name):
        bucket_keys = df['BucketKey'].astype('string')
        bad_mask = bucket_keys.str.contains(CONTROL_CHAR_PATTERN, na=False)
        bad_rows = df.loc[bad_mask, ['BucketKey']].copy()
        bad_rows['Issue'] = 'control_character'
        bad_rows['BucketKeyEscaped'] = [
            make_badkey_record('control_character', str(key)).bucket_key_escaped
            for key in bad_rows['BucketKey'].tolist()
        ]
        if not bad_rows.empty:
            print(
                f"Skipping {len(bad_rows)} {inventory_name} inventory row(s) with control-character keys; "
                "recording them in BADKEYS output."
            )
        stats[f'{inventory_name.lower()}_bad_key_rows'] = int(len(bad_rows))
        cleaned_df = df.loc[~bad_mask].copy()
        return cleaned_df, bad_rows[['Issue', 'BucketKeyEscaped', 'BucketKey']]

    prp_inventory, prp_bad_keys = split_bad_keys(prp_inventory, 'NRP')
    aws_inventory, aws_bad_keys = split_bad_keys(aws_inventory, 'AWS')
    bad_keys = pd.concat([prp_bad_keys, aws_bad_keys], ignore_index=True)

    return prp_inventory, aws_inventory, bad_keys


def build_comparison_summary(
    prp_inventory,
    aws_inventory,
    puts,
    deletes,
    bad_keys,
    no_backup_prefixes,
    inventory_stats=None,
):
    eligible_keys = scientific_inventory(prp_inventory)['BucketKey']
    if no_backup_prefixes:
        eligible_keys = eligible_keys[~eligible_keys.str.startswith(tuple(no_backup_prefixes))]

    eligible_distinct = int(eligible_keys.nunique(dropna=True))
    pending_distinct = int(puts.nunique(dropna=True))
    pending_control_mask = puts.astype('string').map(lambda value: is_retention_marker(str(value)))
    pending_data_puts = puts[~pending_control_mask]
    pending_data_distinct = int(pending_data_puts.nunique(dropna=True))
    pending_fraction = pending_data_distinct / eligible_distinct if eligible_distinct else 0.0

    return {
        'schema_version': 1,
        'generated_at_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'local_inventory_rows': int(len(prp_inventory)),
        'glacier_inventory_rows': int(len(aws_inventory)),
        'eligible_local_distinct_objects': eligible_distinct,
        'glacier_distinct_objects': int(
            scientific_inventory(aws_inventory)['BucketKey'].nunique(dropna=True)
        ),
        'pending_put_rows': int(len(puts)),
        'pending_put_distinct_objects': pending_distinct,
        'pending_data_put_rows': int(len(pending_data_puts)),
        'pending_data_put_distinct_objects': pending_data_distinct,
        'pending_control_put_rows': int(pending_control_mask.sum()),
        'pending_control_put_distinct_objects': int(puts[pending_control_mask].nunique(dropna=True)),
        'delete_rows': int(len(deletes)),
        'delete_distinct_objects': int(deletes.nunique(dropna=True)),
        'bad_key_rows': 0 if bad_keys is None else int(len(bad_keys)),
        'pending_upload_fraction': pending_fraction,
        'inventory_processing': dict(inventory_stats or {}),
    }


def write_comparison_summary(output_path, summary):
    with open(output_path, 'w', encoding='utf8') as summary_file:
        json.dump(summary, summary_file, indent=2, sort_keys=True)
        summary_file.write('\n')
    print(
        (
            f'Saved comparison summary to {output_path}: '
            f'eligible_local={summary["eligible_local_distinct_objects"]} '
            f'pending_puts={summary["pending_put_distinct_objects"]} '
            f'pending_upload_fraction={summary["pending_upload_fraction"]:.6f}'
        ),
        flush=True,
    )


def apply_last_modified_updates(prp_inventory, config, *, authoritative_markers=None):
    atomic_directories = normalize_atomic_directories((config.get('backup') or {}).get('atomic_directories'))
    return apply_effective_last_modified(
        prp_inventory,
        atomic_directories,
        authoritative_markers=authoritative_markers,
    )


def find_no_backup_prefixes(prp_inventory: pd.DataFrame):
    mask = prp_inventory['BucketKey'].str.endswith('/NOBACKUP')
    prefixes = prp_inventory.loc[mask, 'BucketKey'].str.rsplit('/', n=1).str[0]
    prefixes = [f"{prefix}/" for prefix in prefixes.dropna().unique() if prefix]
    return prefixes


def calculate_expire_date(expire_days):
    return datetime.now(timezone.utc) - timedelta(days=expire_days)


def get_required_config_value(config, section, *candidate_keys):
    section_values = config.get(section) or {}
    for key in candidate_keys:
        if key in section_values and section_values[key] is not None:
            return section_values[key]

    expected = ", ".join([f"{section}.{key}" for key in candidate_keys])
    raise KeyError(f"Missing required config key. Expected one of: {expected}")


def parse_days(value, config_key):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Expected integer days for '{config_key}', got: {value!r}") from None


def generate_put_and_delete_lists(primary_inventory_df: pd.DataFrame,
                                  glacier_inventory_df: pd.DataFrame,
                                  expire_date,
                                  no_backup_prefixes=None,
                                  atomic_directories=None):
    # Copy dataframes to not alter the original ones
    local_inventory = primary_inventory_df.copy()
    aws_inventory = glacier_inventory_df.copy()

    if no_backup_prefixes:
        no_backup_mask = local_inventory['BucketKey'].str.startswith(tuple(no_backup_prefixes))
        local_inventory_for_puts = local_inventory[~no_backup_mask]
    else:
        local_inventory_for_puts = local_inventory

    scientific_mask = ~lifecycle_control_mask(local_inventory_for_puts['BucketKey'])
    missing_mask = ~local_inventory_for_puts.BucketKey.isin(aws_inventory.BucketKey)
    # Scientific data remains upload-once. Retention markers are deliberately
    # tiny control objects and must be overwritten when their LastModified is
    # newer so the Glacier copy follows the current Ceph retention decision.
    refresh_marker_mask = marker_upload_mask(
        local_inventory_for_puts,
        aws_inventory,
        atomic_directories,
    )
    puts = local_inventory_for_puts[(scientific_mask & missing_mask) | refresh_marker_mask]
    scientific_aws = scientific_inventory(aws_inventory)
    scientific_local_keys = scientific_inventory(local_inventory)['BucketKey']
    deletes = scientific_aws[
        (~scientific_aws.BucketKey.isin(scientific_local_keys))
        & (scientific_aws.LastModified < expire_date)
    ]
    return puts['BucketKey'], deletes['BucketKey']


def derive_atomic_group_info(bucket_key, atomic_directories):
    for pattern in atomic_directories:
        if pattern.endswith('/*'):
            base = pattern[:-2].rstrip('/')
            prefix = f'{base}/'
            if not bucket_key.startswith(prefix):
                continue
            suffix = bucket_key[len(prefix):]
            group_id = suffix.split('/', 1)[0]
            if not group_id:
                continue
            return f'{prefix}{group_id}/', prefix

        prefix = pattern.rstrip('*')
        if prefix and not prefix.endswith('/'):
            prefix = f'{prefix}/'
        if prefix and bucket_key.startswith(prefix):
            return prefix, prefix
    return None, None


def derive_folder_group(bucket_key, depth=3):
    parts = [part for part in bucket_key.split('/') if part]
    if len(parts) <= 1:
        return bucket_key
    # Collapse non-atomic paths to folder-level grouping, not individual filenames.
    folder_depth = min(depth, len(parts) - 1)
    if folder_depth <= 0:
        return bucket_key
    return '/'.join(parts[:folder_depth]) + '/'


def build_cleanup_window_entries(primary_inventory_df: pd.DataFrame,
                                 glacier_inventory_df: pd.DataFrame,
                                 s3_expire_days,
                                 cold_storage_expire_days,
                                 notification_days,
                                 atomic_directories,
                                 now_utc=None):
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    now_ts = pd.Timestamp(now_utc)
    if now_ts.tzinfo is None:
        now_ts = now_ts.tz_localize('UTC')
    else:
        now_ts = now_ts.tz_convert('UTC')
    window_end = now_ts + timedelta(days=notification_days)
    atomic_directories = normalize_atomic_directories(atomic_directories)

    local_df = scientific_inventory(primary_inventory_df)[['BucketKey', 'LastModified']].dropna(
        subset=['BucketKey', 'LastModified']
    ).copy()
    no_backup_prefixes = find_no_backup_prefixes(primary_inventory_df)
    if no_backup_prefixes:
        local_df = local_df[~local_df['BucketKey'].str.startswith(tuple(no_backup_prefixes))]
    local_df['CleanupPhase'] = 's3'
    local_df['SourceLastModified'] = local_df['LastModified']
    local_df['ScheduledCleanupDate'] = local_df['SourceLastModified'] + timedelta(days=s3_expire_days)

    glacier_df = scientific_inventory(glacier_inventory_df)[['BucketKey', 'LastModified']].dropna(
        subset=['BucketKey', 'LastModified']
    ).copy()
    primary_scientific_keys = scientific_inventory(primary_inventory_df)['BucketKey']
    missing_in_primary_mask = ~glacier_df['BucketKey'].isin(primary_scientific_keys)
    glacier_df = glacier_df[missing_in_primary_mask]
    glacier_df['CleanupPhase'] = 'glacier'
    glacier_df['SourceLastModified'] = glacier_df['LastModified']
    glacier_df['ScheduledCleanupDate'] = glacier_df['SourceLastModified'] + timedelta(days=cold_storage_expire_days)

    cleanup_df = pd.concat(
        [
            local_df[['CleanupPhase', 'BucketKey', 'SourceLastModified', 'ScheduledCleanupDate']],
            glacier_df[['CleanupPhase', 'BucketKey', 'SourceLastModified', 'ScheduledCleanupDate']],
        ],
        ignore_index=True,
    )
    cleanup_df['SourceLastModified'] = pd.to_datetime(cleanup_df['SourceLastModified'], errors='coerce', utc=True)
    cleanup_df['ScheduledCleanupDate'] = pd.to_datetime(cleanup_df['ScheduledCleanupDate'], errors='coerce', utc=True)
    cleanup_df.dropna(subset=['SourceLastModified', 'ScheduledCleanupDate'], inplace=True)

    cleanup_df = cleanup_df[
        (cleanup_df['ScheduledCleanupDate'] >= now_ts) & (cleanup_df['ScheduledCleanupDate'] <= window_end)
    ].copy()

    if cleanup_df.empty:
        return cleanup_df

    day_delta = cleanup_df['ScheduledCleanupDate'] - now_ts
    cleanup_df['DaysUntilCleanup'] = day_delta.dt.total_seconds().apply(lambda seconds: max(0, math.ceil(seconds / 86400)))

    grouping_keys = []
    grouping_types = []
    atomic_roots = []
    for bucket_key in cleanup_df['BucketKey']:
        atomic_group, atomic_root = derive_atomic_group_info(bucket_key, atomic_directories)
        if atomic_group:
            grouping_keys.append(atomic_group)
            grouping_types.append('atomic')
            atomic_roots.append(atomic_root)
        else:
            grouping_keys.append(derive_folder_group(bucket_key))
            grouping_types.append('folder')
            atomic_roots.append('')

    cleanup_df['GroupingType'] = grouping_types
    cleanup_df['GroupingKey'] = grouping_keys
    cleanup_df['AtomicRoot'] = atomic_roots
    cleanup_df.sort_values(['CleanupPhase', 'ScheduledCleanupDate', 'BucketKey'], inplace=True)
    cleanup_df.reset_index(drop=True, inplace=True)
    return cleanup_df


def build_cleanup_summary(cleanup_window_df: pd.DataFrame):
    if cleanup_window_df.empty:
        return pd.DataFrame(
            columns=[
                'CleanupPhase',
                'GroupingType',
                'GroupingKey',
                'FileCount',
                'EarliestCleanupDate',
                'LatestCleanupDate',
            ]
        )

    summary_df = (
        cleanup_window_df.groupby(['CleanupPhase', 'GroupingType', 'GroupingKey'])
        .agg(
            FileCount=('BucketKey', 'count'),
            EarliestCleanupDate=('ScheduledCleanupDate', 'min'),
            LatestCleanupDate=('ScheduledCleanupDate', 'max'),
        )
        .reset_index()
    )

    summary_df['GroupingTypePriority'] = summary_df['GroupingType'].map({'atomic': 0, 'folder': 1}).fillna(2)
    summary_df.sort_values(
        ['CleanupPhase', 'GroupingTypePriority', 'FileCount', 'GroupingKey'],
        ascending=[True, True, False, True],
        inplace=True,
    )
    summary_df.drop(columns=['GroupingTypePriority'], inplace=True)
    summary_df.reset_index(drop=True, inplace=True)
    return summary_df


def build_cleanup_slack_message(cleanup_window_df: pd.DataFrame,
                                cleanup_summary_df: pd.DataFrame,
                                notification_days,
                                now_utc=None,
                                max_groups_per_phase=12,
                                columns_per_row=3):
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    def format_due_window(earliest_dt, latest_dt):
        earliest = pd.Timestamp(earliest_dt).strftime('%Y-%m-%d')
        latest = pd.Timestamp(latest_dt).strftime('%Y-%m-%d')
        if earliest == latest:
            return earliest
        return f'{earliest} to {latest}'

    def chunked(items, chunk_size):
        for idx in range(0, len(items), chunk_size):
            yield items[idx:idx + chunk_size]

    window_end = now_utc + timedelta(days=notification_days)
    total_count = len(cleanup_window_df)
    s3_count = int((cleanup_window_df['CleanupPhase'] == 's3').sum()) if not cleanup_window_df.empty else 0
    glacier_count = int((cleanup_window_df['CleanupPhase'] == 'glacier').sum()) if not cleanup_window_df.empty else 0
    lines = [
        '*Data-retention report*',
        'Details: https://data-explorer.braingeneers.gi.ucsc.edu',
        f'Scheduled deletion window for the next {notification_days} days',
        f'Generated at {now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")}',
        (
            f'Files in this report are scheduled for deletion between '
            f'{now_utc.strftime("%Y-%m-%d")} and {window_end.strftime("%Y-%m-%d")} (inclusive).'
        ),
        f'- Current Ceph/S3 candidates: {s3_count} file(s)',
        f'- Glacier-only candidates: {glacier_count} file(s)',
    ]

    if total_count == 0:
        lines.append('No files are scheduled for deletion in this date range.')
        return '\n'.join(lines) + '\n'

    for phase, label in [('s3', 'NRP/S3'), ('glacier', 'AWS/Glacier')]:
        phase_rows = cleanup_window_df[cleanup_window_df['CleanupPhase'] == phase]
        if phase_rows.empty:
            lines.append(f'{label}: no files become policy-eligible in this date range.')
            continue

        phase_atomic = phase_rows[phase_rows['GroupingType'] == 'atomic']
        phase_non_atomic = phase_rows[phase_rows['GroupingType'] != 'atomic']

        atomic_group_count = int(phase_atomic['GroupingKey'].nunique())
        atomic_file_count = int(len(phase_atomic))
        non_atomic_group_count = int(phase_non_atomic['GroupingKey'].nunique())
        non_atomic_file_count = int(len(phase_non_atomic))

        lines.append(
            f'{label} summary: atomic dataset candidates: '
            f'{atomic_group_count} folder(s), {atomic_file_count} file(s); '
            f'individual file candidates: {non_atomic_file_count} file(s) across {non_atomic_group_count} folder group(s)'
        )

        if atomic_group_count > 0:
            lines.append('Atomic dataset candidates:')
            atomic_per_group = (
                phase_atomic.groupby(['AtomicRoot', 'GroupingKey'])
                .agg(
                    FileCount=('BucketKey', 'count'),
                    EarliestCleanupDate=('ScheduledCleanupDate', 'min'),
                    LatestCleanupDate=('ScheduledCleanupDate', 'max'),
                )
                .reset_index()
                .sort_values(['AtomicRoot', 'GroupingKey'])
            )

            for atomic_root, root_df in atomic_per_group.groupby('AtomicRoot'):
                root_name = atomic_root or '(atomic root unknown)'
                lines.append(f'- Under {root_name} ({len(root_df)} folder(s))')
                code_items = []
                for _, row in root_df.iterrows():
                    group_key = row['GroupingKey']
                    short_name = group_key
                    if atomic_root and group_key.startswith(atomic_root):
                        short_name = group_key[len(atomic_root):]
                    short_name = short_name.rstrip('/')
                    due_label = format_due_window(row['EarliestCleanupDate'], row['LatestCleanupDate'])
                    code_items.append(f'{short_name}@{due_label}')
                lines.append('```')
                for row_items in chunked(code_items, max(1, int(columns_per_row))):
                    lines.append(' | '.join(row_items))
                lines.append('```')
        else:
            lines.append('Atomic dataset candidates: none')

        if non_atomic_group_count > 0:
            lines.append(
                f'Individual file candidates: {non_atomic_file_count} file(s) '
                f'across {non_atomic_group_count} folder group(s) (top {max_groups_per_phase})'
            )
            non_atomic_summary = (
                cleanup_summary_df[
                    (cleanup_summary_df['CleanupPhase'] == phase) & (cleanup_summary_df['GroupingType'] == 'folder')
                ]
                .sort_values(['FileCount', 'GroupingKey'], ascending=[False, True])
                .head(max_groups_per_phase)
            )
            for _, row in non_atomic_summary.iterrows():
                due_label = format_due_window(row['EarliestCleanupDate'], row['LatestCleanupDate'])
                lines.append(
                    f"- `{row['GroupingKey']}` :: {int(row['FileCount'])} file(s), policy-eligible: {due_label}"
                )
        else:
            lines.append('Individual file candidates: none')

    return '\n'.join(lines) + '\n'


def output_puts_deletes_and_notifications(puts,
                                          deletes,
                                          bad_keys,
                                          notifications,
                                          cleanup_window,
                                          cleanup_summary,
                                          cleanup_slack_message,
                                          puts_output_filepath=None,
                                          deletes_output_filepath=None,
                                          bad_keys_output_filepath=None,
                                          notifications_output_filepath=None,
                                          cleanup_window_output_filepath=None,
                                          cleanup_summary_output_filepath=None,
                                          cleanup_slack_message_output_filepath=None):
    if puts_output_filepath is not None:
        puts.to_csv(puts_output_filepath, index=False, header=False, encoding='utf8')
        print(f'Saved PUTs to {puts_output_filepath}')
    else:
        print("PUTs:")
        print(puts)

    if deletes_output_filepath is not None:
        deletes.to_csv(deletes_output_filepath, index=False, header=False, encoding='utf8')
        print(f'Saved DELETEs to {deletes_output_filepath}')
    else:
        print("\nDELETEs:")
        print(deletes)

    if bad_keys_output_filepath is not None:
        records = []
        if bad_keys is not None and not bad_keys.empty:
            for _, row in bad_keys.iterrows():
                records.append(
                    make_badkey_record(
                        row['Issue'],
                        row.get('BucketKey', row['BucketKeyEscaped']),
                    )
                )
        write_badkeys_tsv(bad_keys_output_filepath, records)
        bad_key_count = 0 if bad_keys is None else len(bad_keys)
        print(f'Saved BADKEYS ({bad_key_count}) to {bad_keys_output_filepath}')
    else:
        print("\nBADKEYS:")
        if bad_keys is None or bad_keys.empty:
            print('None')
        else:
            print(bad_keys[['Issue', 'BucketKeyEscaped']])

    if notifications_output_filepath is not None:
        notifications_output = notifications.copy()
        if not notifications_output.empty:
            if 'SourceLastModified' in notifications_output.columns:
                notifications_output['SourceLastModified'] = notifications_output['SourceLastModified'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            if 'ScheduledCleanupDate' in notifications_output.columns:
                notifications_output['ScheduledCleanupDate'] = notifications_output['ScheduledCleanupDate'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        notifications_output.to_csv(notifications_output_filepath, index=False, encoding='utf8')
        print(f'Saved NOTIFICATIONS to {notifications_output_filepath}')
    else:
        print("\nNOTIFICATIONS:")
        print(notifications)

    if cleanup_window_output_filepath is not None:
        cleanup_window_output = cleanup_window.copy()
        if not cleanup_window_output.empty:
            cleanup_window_output['SourceLastModified'] = cleanup_window_output['SourceLastModified'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            cleanup_window_output['ScheduledCleanupDate'] = cleanup_window_output['ScheduledCleanupDate'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        cleanup_window_output.to_csv(cleanup_window_output_filepath, index=False, encoding='utf8')
        print(f'Saved cleanup window entries to {cleanup_window_output_filepath}')
    else:
        print("\nCLEANUP WINDOW ENTRIES:")
        print(cleanup_window)

    if cleanup_summary_output_filepath is not None:
        cleanup_summary_output = cleanup_summary.copy()
        if not cleanup_summary_output.empty:
            cleanup_summary_output['EarliestCleanupDate'] = cleanup_summary_output['EarliestCleanupDate'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            cleanup_summary_output['LatestCleanupDate'] = cleanup_summary_output['LatestCleanupDate'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        cleanup_summary_output.to_csv(cleanup_summary_output_filepath, index=False, encoding='utf8')
        print(f'Saved cleanup summary to {cleanup_summary_output_filepath}')
    else:
        print("\nCLEANUP SUMMARY:")
        print(cleanup_summary)

    if cleanup_slack_message_output_filepath is not None:
        with open(cleanup_slack_message_output_filepath, 'w', encoding='utf8') as slack_message_file:
            slack_message_file.write(cleanup_slack_message)
        print(f'Saved cleanup Slack message proposal to {cleanup_slack_message_output_filepath}')
    else:
        print("\nCLEANUP SLACK MESSAGE PROPOSAL:")
        print(cleanup_slack_message)


def main(config: str,
         prp_inventory: str,
         aws_inventory: str,
         puts_output: str,
         deletes_output: str,
         bad_keys_output: str,
         notifications_output: str,
         cleanup_window_output: str,
         cleanup_summary_output: str,
         cleanup_slack_message_output: str,
         comparison_summary_output: str = None,
         progress_interval_seconds: float = DEFAULT_PROGRESS_INTERVAL_SECONDS):
    progress = Stage3ProgressReporter(progress_interval_seconds)
    progress.start()
    inventory_stats = {}
    try:
        progress.set_phase('load_config')
        config = load_config_file(config)
        progress.set_phase(
            'load_inventories',
            local_bytes=os.path.getsize(prp_inventory),
            glacier_bytes=os.path.getsize(aws_inventory),
        )
        df_prp_inventory, df_aws_inventory, bad_keys = load_inventories(
            prp_inventory,
            aws_inventory,
            stats=inventory_stats,
        )
        progress.set_phase(
            'apply_atomic_timestamps',
            local_rows=len(df_prp_inventory),
            glacier_rows=len(df_aws_inventory),
        )
        df_prp_inventory = apply_last_modified_updates(df_prp_inventory, config)
        # The current Ceph marker inventory is authoritative for both phases.
        # Glacier's own marker copy is recovery evidence, never a renewal
        # signal, while the newest scientific object still defines each
        # Glacier-only atomic dataset's baseline activity timestamp.
        df_aws_inventory = apply_last_modified_updates(
            df_aws_inventory,
            config,
            authoritative_markers=df_prp_inventory,
        )
        backup_config = config.get('backup') or {}

        s3_expire_days = parse_days(
            get_required_config_value(config, 'deletion', 's3_expire_days'),
            'deletion.s3_expire_days',
        )
        cold_storage_expire_days = parse_days(
            get_required_config_value(config, 'deletion', 'cold_storage_expire_days'),
            'deletion.cold_storage_expire_days',
        )
        expire_date = calculate_expire_date(cold_storage_expire_days)
        notification_days = parse_days(
            get_required_config_value(config, 'deletion', 'notification_days'),
            'deletion.notification_days',
        )
        no_backup_prefixes = find_no_backup_prefixes(df_prp_inventory)
        if no_backup_prefixes:
            print(f"Skipping PUTs under {len(no_backup_prefixes)} NOBACKUP prefix(es).", flush=True)
        progress.set_phase('compare_inventories')
        puts, deletes = generate_put_and_delete_lists(
            df_prp_inventory,
            df_aws_inventory,
            expire_date,
            no_backup_prefixes,
            backup_config.get('atomic_directories') or [],
        )
        progress.set_phase('build_cleanup_window', pending_put_rows=len(puts), delete_rows=len(deletes))
        now_utc = datetime.now(timezone.utc)
        cleanup_window = build_cleanup_window_entries(
            df_prp_inventory,
            df_aws_inventory,
            s3_expire_days=s3_expire_days,
            cold_storage_expire_days=cold_storage_expire_days,
            notification_days=notification_days,
            atomic_directories=backup_config.get('atomic_directories') or [],
            now_utc=now_utc,
        )
        # notifications.csv now uses the same schedule rows as cleanup-window output,
        # preserved as a stable path for downstream machine consumers.
        notifications = cleanup_window.copy()
        progress.set_phase('build_cleanup_summary', cleanup_rows=len(cleanup_window))
        cleanup_summary = build_cleanup_summary(cleanup_window)
        cleanup_slack_message = build_cleanup_slack_message(
            cleanup_window,
            cleanup_summary,
            notification_days=notification_days,
            now_utc=now_utc,
        )
        comparison_summary = build_comparison_summary(
            df_prp_inventory,
            df_aws_inventory,
            puts,
            deletes,
            bad_keys,
            no_backup_prefixes,
            inventory_stats=inventory_stats,
        )
        progress.set_phase('write_outputs')
        output_puts_deletes_and_notifications(
            puts=puts,
            deletes=deletes,
            bad_keys=bad_keys,
            notifications=notifications,
            cleanup_window=cleanup_window,
            cleanup_summary=cleanup_summary,
            cleanup_slack_message=cleanup_slack_message,
            puts_output_filepath=puts_output,
            deletes_output_filepath=deletes_output,
            bad_keys_output_filepath=bad_keys_output,
            notifications_output_filepath=notifications_output,
            cleanup_window_output_filepath=cleanup_window_output,
            cleanup_summary_output_filepath=cleanup_summary_output,
            cleanup_slack_message_output_filepath=cleanup_slack_message_output,
        )
        if comparison_summary_output is not None:
            write_comparison_summary(comparison_summary_output, comparison_summary)
        progress.set_phase('complete')
    finally:
        progress.stop()


if __name__ == "__main__":
    args = parse_arguments()
    main(
        args.config,
        args.prp_inventory,
        args.aws_inventory,
        args.puts_output,
        args.deletes_output,
        args.badkeys_output,
        args.notifications_output,
        args.cleanup_window_output,
        args.cleanup_summary_output,
        args.cleanup_slack_message_output,
        args.comparison_summary_output,
        args.progress_interval_seconds,
    )

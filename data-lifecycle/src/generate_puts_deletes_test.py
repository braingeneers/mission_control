import contextlib
import json
import os
import re
import sys
import tempfile
import time
import unittest
import warnings
from io import BytesIO, StringIO
from datetime import datetime, timedelta, timezone

import pandas as pd
from botocore.exceptions import ClientError, SSLError

sys.path.insert(0, os.path.dirname(__file__))

from generate_puts_deletes import (  # noqa: E402
    Stage3ProgressReporter,
    apply_last_modified_updates,
    build_comparison_summary,
    build_cleanup_slack_message,
    build_cleanup_summary,
    build_cleanup_window_entries,
    generate_put_and_delete_lists,
    load_inventories,
    main as generate_inventory_outputs,
    output_puts_deletes_and_notifications,
)
from lifecycle_controls import (  # noqa: E402
    RETENTION_MARKER_NAME,
    atomic_retention_marker,
    file_retention_marker,
    scientific_inventory,
)
from badkeys import (  # noqa: E402
    SOURCE_GET_FAILED_AFTER_HEAD_SUCCESS,
    append_source_get_failed_slack_section,
    make_badkey_record,
    parse_badkeys_tsv_text,
)
from stage4_process_puts_deletes import (  # noqa: E402
    ProgressStats,
    UploadFractionGuardError,
    copy_file,
    validate_upload_fraction_guard,
)
from stage4_keys import (  # noqa: E402
    build_source_lookup_candidates,
    load_put_keys,
    normalize_put_key,
)


class TestGeneratePutAndDeleteLists(unittest.TestCase):
    def setUp(self):
        self.expire_date = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def test_generate_put_and_delete_lists(self):
        aws_inventory_df = pd.DataFrame(
            {
                'LastModified': [
                    datetime(2025, 1, 1, tzinfo=timezone.utc),
                    datetime(2025, 1, 2, tzinfo=timezone.utc),
                ],
                'BucketKey': ['bucket/file1', 'bucket/file2'],
            }
        )
        local_inventory_df = pd.DataFrame(
            {
                'LastModified': [
                    datetime(2025, 1, 3, tzinfo=timezone.utc),
                    datetime(2025, 1, 4, tzinfo=timezone.utc),
                ],
                'BucketKey': ['bucket/file2', 'bucket/file3'],
            }
        )

        puts, deletes = generate_put_and_delete_lists(local_inventory_df, aws_inventory_df, self.expire_date)

        self.assertEqual(puts.tolist(), ['bucket/file3'])
        self.assertEqual(deletes.tolist(), ['bucket/file1'])

    def test_load_inventories_excludes_prefix_marker_keys(self):
        with tempfile.NamedTemporaryFile('w', delete=False) as prp_tmp, tempfile.NamedTemporaryFile(
            'w', delete=False
        ) as aws_tmp:
            prp_tmp.write('2025-01-01T00:00:00Z,bucket/prefix/\n')
            prp_tmp.write('2025-01-01T00:00:00Z,bucket/prefix/   \n')
            prp_tmp.write('2025-01-01T00:00:00Z,bucket/file_a\n')
            prp_tmp.write('2025-01-01T00:00:00Z,   bucket/file_c   \n')
            prp_tmp.write('2025-01-01T00:00:00Z,\n')
            prp_tmp.flush()

            aws_tmp.write('bucket,bucket/prefix/,1,2025-01-01T00:00:00Z,GLACIER\n')
            aws_tmp.write('bucket,bucket/prefix/   ,1,2025-01-01T00:00:00Z,GLACIER\n')
            aws_tmp.write('bucket,bucket/file_b,1,2025-01-01T00:00:00Z,GLACIER\n')
            aws_tmp.write('bucket,   bucket/file_d   ,1,2025-01-01T00:00:00Z,GLACIER\n')
            aws_tmp.write('bucket,,1,2025-01-01T00:00:00Z,GLACIER\n')
            aws_tmp.flush()

            prp_inventory, aws_inventory, bad_keys = load_inventories(prp_tmp.name, aws_tmp.name)

        os.unlink(prp_tmp.name)
        os.unlink(aws_tmp.name)

        self.assertEqual(prp_inventory['BucketKey'].tolist(), ['bucket/file_a', 'bucket/file_c'])
        self.assertEqual(aws_inventory['BucketKey'].tolist(), ['bucket/file_b', 'bucket/file_d'])
        self.assertTrue(bad_keys.empty)

    def test_load_inventories_extracts_control_character_bad_keys(self):
        with tempfile.NamedTemporaryFile('w', delete=False) as prp_tmp, tempfile.NamedTemporaryFile(
            'w', delete=False
        ) as aws_tmp:
            prp_tmp.write('2025-01-01T00:00:00Z,bucket/file_ok\n')
            prp_tmp.write('2025-01-01T00:00:00Z,bucket/file_\x01bad\n')
            prp_tmp.flush()

            aws_tmp.write('bucket,bucket/aws_ok,1,2025-01-01T00:00:00Z,GLACIER\n')
            aws_tmp.write('bucket,bucket/aws_\u240dbad,1,2025-01-01T00:00:00Z,GLACIER\n')
            aws_tmp.flush()

            prp_inventory, aws_inventory, bad_keys = load_inventories(prp_tmp.name, aws_tmp.name)

        os.unlink(prp_tmp.name)
        os.unlink(aws_tmp.name)

        self.assertEqual(prp_inventory['BucketKey'].tolist(), ['bucket/file_ok'])
        self.assertEqual(aws_inventory['BucketKey'].tolist(), ['bucket/aws_ok', 'bucket/aws_bad'])
        self.assertTrue((bad_keys['Issue'] == 'control_character').all())
        self.assertIn('bucket/file_\\x01bad', bad_keys['BucketKeyEscaped'].tolist())
        self.assertNotIn('bucket/aws_\\u240dbad', bad_keys['BucketKeyEscaped'].tolist())

    def test_load_inventories_decodes_url_encoded_aws_keys(self):
        with tempfile.NamedTemporaryFile('w', delete=False) as prp_tmp, tempfile.NamedTemporaryFile(
            'w', delete=False
        ) as aws_tmp:
            prp_tmp.write('2025-01-01T00:00:00Z,braingeneers/bulk_rna/sebas/brain_regions1/@md5Sum.md5\n')
            prp_tmp.write('2025-01-01T00:00:00Z,braingeneers/ephys/0000-00-00-e-zip1/original/batch (1).txt\n')
            prp_tmp.flush()

            aws_tmp.write(
                'bucket,braingeneers/bulk_rna/sebas/brain_regions1/%40md5Sum.md5,1,2025-01-01T00:00:00Z,GLACIER\n'
            )
            aws_tmp.write(
                'bucket,braingeneers/ephys/0000-00-00-e-zip1/original/batch%20%281%29.txt,1,2025-01-01T00:00:00Z,GLACIER\n'
            )
            aws_tmp.flush()

            prp_inventory, aws_inventory, bad_keys = load_inventories(prp_tmp.name, aws_tmp.name)

        os.unlink(prp_tmp.name)
        os.unlink(aws_tmp.name)

        self.assertIn(
            'braingeneers/bulk_rna/sebas/brain_regions1/@md5Sum.md5',
            aws_inventory['BucketKey'].tolist(),
        )
        self.assertIn(
            'braingeneers/ephys/0000-00-00-e-zip1/original/batch (1).txt',
            aws_inventory['BucketKey'].tolist(),
        )
        self.assertTrue(bad_keys.empty)

    def test_apply_last_modified_updates_handles_wildcard_atomic_directories(self):
        config = {
            'backup': {
                'atomic_directories': ['bucket/ephys/*'],
            }
        }

        prp_inventory = pd.DataFrame(
            {
                'LastModified': [
                    datetime(2025, 1, 1, tzinfo=timezone.utc),
                    datetime(2025, 1, 5, tzinfo=timezone.utc),
                    datetime(2025, 1, 2, tzinfo=timezone.utc),
                ],
                'BucketKey': [
                    'bucket/ephys/run1/file_a.bin',
                    'bucket/ephys/run1/file_b.bin',
                    'bucket/ephys/run2/file_c.bin',
                ],
            }
        )

        updated = apply_last_modified_updates(prp_inventory.copy(), config)

        run1_dates = updated[updated['BucketKey'].str.startswith('bucket/ephys/run1/')]['LastModified'].unique()
        run2_dates = updated[updated['BucketKey'].str.startswith('bucket/ephys/run2/')]['LastModified'].unique()

        self.assertEqual(len(run1_dates), 1)
        self.assertEqual(len(run2_dates), 1)
        self.assertEqual(pd.Timestamp(run1_dates[0]).date(), datetime(2025, 1, 5).date())
        self.assertEqual(pd.Timestamp(run2_dates[0]).date(), datetime(2025, 1, 2).date())

    def test_apply_last_modified_updates_does_not_emit_dtype_future_warning(self):
        config = {
            'backup': {
                'atomic_directories': ['bucket/ephys/*'],
            }
        }

        prp_inventory = pd.DataFrame(
            {
                'LastModified': pd.to_datetime(
                    [
                        '2025-12-10T01:09:06.000000000Z',
                        '2025-12-10T01:09:06.000000000Z',
                        '2025-12-10T01:09:06.000000000Z',
                        '2026-02-06T13:38:11.000000000Z',
                        '2024-03-15T23:25:14.000000000Z',
                    ],
                    utc=True,
                ),
                'BucketKey': [
                    'bucket/ephys/run1/a.bin',
                    'bucket/ephys/run1/b.bin',
                    'bucket/ephys/run1/c.bin',
                    'bucket/ephys/run2/a.bin',
                    'bucket/ephys/run2/b.bin',
                ],
            }
        )

        with warnings.catch_warnings():
            warnings.filterwarnings(
                'error',
                message='.*incompatible dtype.*',
                category=FutureWarning,
            )
            updated = apply_last_modified_updates(prp_inventory.copy(), config)

        self.assertEqual(str(updated['LastModified'].dtype), 'datetime64[ns, UTC]')

    def test_retention_markers_extend_atomic_dataset_and_individual_file(self):
        config = {'backup': {'atomic_directories': ['bucket/ephys/*']}}
        inventory = pd.DataFrame(
            {
                'BucketKey': [
                    'bucket/ephys/run1/a.bin',
                    'bucket/ephys/run1/b.bin',
                    atomic_retention_marker('bucket/ephys/run1/'),
                    'bucket/misc/c.bin',
                    file_retention_marker('bucket/misc/c.bin'),
                ],
                'LastModified': pd.to_datetime(
                    [
                        '2020-01-01T00:00:00Z',
                        '2021-01-01T00:00:00Z',
                        '2026-01-01T00:00:00Z',
                        '2022-01-01T00:00:00Z',
                        '2025-01-01T00:00:00Z',
                    ],
                    utc=True,
                ),
            }
        )

        updated = apply_last_modified_updates(inventory, config)

        run_dates = updated[updated['BucketKey'].str.startswith('bucket/ephys/run1/')]
        run_dates = scientific_inventory(run_dates)['LastModified'].unique()
        self.assertEqual(len(run_dates), 1)
        self.assertEqual(pd.Timestamp(run_dates[0]), pd.Timestamp('2026-01-01T00:00:00Z'))
        file_date = updated.loc[updated['BucketKey'] == 'bucket/misc/c.bin', 'LastModified'].iloc[0]
        self.assertEqual(file_date, pd.Timestamp('2025-01-01T00:00:00Z'))

    def test_newer_retention_marker_is_reuploaded_but_scientific_file_is_not(self):
        local = pd.DataFrame(
            {
                'BucketKey': ['bucket/file.bin', file_retention_marker('bucket/file.bin')],
                'LastModified': pd.to_datetime(
                    ['2026-01-01T00:00:00Z', '2026-02-01T00:00:00Z'], utc=True
                ),
            }
        )
        glacier = pd.DataFrame(
            {
                'BucketKey': ['bucket/file.bin', file_retention_marker('bucket/file.bin')],
                'LastModified': pd.to_datetime(
                    ['2020-01-01T00:00:00Z', '2026-01-15T00:00:00Z'], utc=True
                ),
            }
        )

        puts, _ = generate_put_and_delete_lists(local, glacier, self.expire_date)

        self.assertEqual(puts.tolist(), [f'bucket/file.bin.{RETENTION_MARKER_NAME}'])

    def test_stage4_does_not_skip_an_existing_retention_marker(self):
        marker = file_retention_marker('bucket/file.bin')
        stats = ProgressStats(1)
        head_calls = []

        def head_object(*_args, **_kwargs):
            head_calls.append(True)
            return {}

        def source_opener(_url, _mode):
            return BytesIO(b'')

        class Destination(BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        def destination_opener(_url, _mode, transport_params=None):
            self.assertTrue(transport_params['multipart_upload'])
            return Destination()

        result = copy_file(
            marker,
            'glacier-bucket',
            retries=0,
            retry_base_seconds=0,
            retry_max_seconds=0,
            stats=stats,
            head_object_func=head_object,
            source_opener=source_opener,
            destination_opener=destination_opener,
            s3_client=object(),
        )

        self.assertEqual(result['status'], 'uploaded')
        self.assertEqual(head_calls, [])

    def test_control_objects_do_not_appear_in_cleanup_window(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        local = pd.DataFrame(
            {
                'BucketKey': [
                    'bucket/ephys/run1/file.bin',
                    atomic_retention_marker('bucket/ephys/run1/'),
                    'bucket/ephys/run1/NOBACKUP',
                ],
                'LastModified': pd.to_datetime(
                    [now - timedelta(days=20), now - timedelta(days=20), now], utc=True
                ),
            }
        )
        glacier = pd.DataFrame(columns=['BucketKey', 'LastModified'])

        cleanup = build_cleanup_window_entries(
            local,
            glacier,
            s3_expire_days=30,
            cold_storage_expire_days=365,
            notification_days=90,
            atomic_directories=['bucket/ephys/*'],
            now_utc=now,
        )

        self.assertTrue(cleanup.empty)


class TestCleanupWindowArtifacts(unittest.TestCase):
    def setUp(self):
        self.now_utc = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.local_inventory_df = pd.DataFrame(
            {
                'BucketKey': [
                    'bucket/ephys/run1/file_a.bin',
                    'bucket/archive/file_b.bin',
                    'bucket/no_backup/NOBACKUP',
                ],
                'LastModified': [
                    self.now_utc - timedelta(days=20),   # S3 cleanup at +10 days when s3_expire_days=30.
                    self.now_utc - timedelta(days=200),  # S3 cleanup already overdue when s3_expire_days=30.
                    self.now_utc - timedelta(days=5),    # Sentinel should be excluded from S3 cleanup schedule.
                ],
            }
        )
        self.glacier_inventory_df = pd.DataFrame(
            {
                'BucketKey': [
                    'bucket/ephys/run2/file_c.bin',
                    'bucket/ephys/run1/file_a.bin',  # Present in local inventory, should not be glacier-delete candidate.
                    'bucket/old/file_d.bin',
                ],
                'LastModified': [
                    self.now_utc - timedelta(days=300),  # Glacier cleanup at +65 days when cold_storage_expire_days=365.
                    self.now_utc - timedelta(days=1000),
                    self.now_utc - timedelta(days=500),  # Glacier cleanup already overdue.
                ],
            }
        )

    def test_cleanup_window_contains_s3_and_glacier_items_due_soon(self):
        cleanup_window = build_cleanup_window_entries(
            self.local_inventory_df,
            self.glacier_inventory_df,
            s3_expire_days=30,
            cold_storage_expire_days=365,
            notification_days=90,
            atomic_directories=['bucket/ephys/*'],
            now_utc=self.now_utc,
        )

        keys = cleanup_window['BucketKey'].tolist()
        phases = cleanup_window['CleanupPhase'].tolist()

        self.assertIn('bucket/ephys/run1/file_a.bin', keys)
        self.assertIn('bucket/ephys/run2/file_c.bin', keys)
        self.assertNotIn('bucket/no_backup/NOBACKUP', keys)
        self.assertIn('s3', phases)
        self.assertIn('glacier', phases)
        self.assertTrue((cleanup_window['DaysUntilCleanup'] >= 0).all())
        self.assertTrue((cleanup_window['DaysUntilCleanup'] <= 90).all())

    def test_glacier_atomic_dataset_uses_newest_object_before_window_filter(self):
        glacier = pd.DataFrame(
            {
                'BucketKey': [
                    'bucket/ephys/run3/old.bin',
                    'bucket/ephys/run3/new.bin',
                ],
                'LastModified': [
                    self.now_utc - timedelta(days=300),
                    self.now_utc - timedelta(days=100),
                ],
            }
        )
        config = {'backup': {'atomic_directories': ['bucket/ephys/*']}}
        effective = apply_last_modified_updates(
            glacier,
            config,
            authoritative_markers=self.local_inventory_df,
        )

        cleanup_window = build_cleanup_window_entries(
            self.local_inventory_df,
            effective,
            s3_expire_days=30,
            cold_storage_expire_days=365,
            notification_days=90,
            atomic_directories=['bucket/ephys/*'],
            now_utc=self.now_utc,
        )

        self.assertFalse(cleanup_window['BucketKey'].str.startswith('bucket/ephys/run3/').any())

    def test_cleanup_summary_prefers_atomic_grouping_where_available(self):
        cleanup_window = build_cleanup_window_entries(
            self.local_inventory_df,
            self.glacier_inventory_df,
            s3_expire_days=30,
            cold_storage_expire_days=365,
            notification_days=90,
            atomic_directories=['bucket/ephys/*'],
            now_utc=self.now_utc,
        )
        summary = build_cleanup_summary(cleanup_window)

        self.assertTrue((summary['GroupingKey'] == 'bucket/ephys/run1/').any())
        self.assertTrue((summary['GroupingKey'] == 'bucket/ephys/run2/').any())

    def test_cleanup_slack_message_contains_counts_and_destination_link(self):
        cleanup_window = build_cleanup_window_entries(
            self.local_inventory_df,
            self.glacier_inventory_df,
            s3_expire_days=30,
            cold_storage_expire_days=365,
            notification_days=90,
            atomic_directories=['bucket/ephys/*'],
            now_utc=self.now_utc,
        )
        summary = build_cleanup_summary(cleanup_window)
        slack_message = build_cleanup_slack_message(
            cleanup_window,
            summary,
            notification_days=90,
            now_utc=self.now_utc,
            max_groups_per_phase=5,
        )

        self.assertTrue(slack_message.startswith('*Data-retention report*'))
        self.assertIn('Details: https://data-explorer.braingeneers.gi.ucsc.edu', slack_message)
        self.assertIn('Files in this report are scheduled for deletion between', slack_message)
        self.assertIn('Current Ceph/S3 candidates:', slack_message)
        self.assertIn('Glacier-only candidates:', slack_message)
        self.assertIn('NRP/S3 summary: atomic dataset candidates:', slack_message)
        self.assertIn('individual file candidates:', slack_message)
        self.assertIn('Individual file candidates:', slack_message)
        self.assertEqual(slack_message.count('https://data-explorer.braingeneers.gi.ucsc.edu'), 1)
        self.assertIn('Under bucket/ephys/', slack_message)
        self.assertIn('run1@', slack_message)
        self.assertIsNone(re.search(r'(\d{4}-\d{2}-\d{2}) to \1', slack_message))

    def test_cleanup_slack_message_can_append_source_access_badkeys(self):
        slack_message = '*Automated data-lifecycle notice*: this report shows what is scheduled for cleanup soon.\n'
        records = [
            make_badkey_record(SOURCE_GET_FAILED_AFTER_HEAD_SUCCESS, 'bucket/path/a.bin'),
            make_badkey_record(SOURCE_GET_FAILED_AFTER_HEAD_SUCCESS, 'bucket/path/b.bin'),
        ]

        updated = append_source_get_failed_slack_section(slack_message, records, max_examples=1)

        self.assertIn('Backup source access issues:', updated)
        self.assertIn('2 key(s) were listed by source inventory', updated)
        self.assertIn('`bucket/path/a.bin`', updated)
        self.assertIn('+1 more in `badkeys.tsv`', updated)

    def test_notifications_output_is_headered_csv(self):
        cleanup_window = build_cleanup_window_entries(
            self.local_inventory_df,
            self.glacier_inventory_df,
            s3_expire_days=30,
            cold_storage_expire_days=365,
            notification_days=90,
            atomic_directories=['bucket/ephys/*'],
            now_utc=self.now_utc,
        )
        summary = build_cleanup_summary(cleanup_window)
        slack_message = build_cleanup_slack_message(
            cleanup_window,
            summary,
            notification_days=90,
            now_utc=self.now_utc,
            max_groups_per_phase=5,
        )

        with tempfile.NamedTemporaryFile(delete=False) as notifications_tmp:
            notifications_path = notifications_tmp.name

        try:
            output_puts_deletes_and_notifications(
                puts=pd.Series([], dtype='object'),
                deletes=pd.Series([], dtype='object'),
                bad_keys=pd.DataFrame(columns=['Issue', 'BucketKeyEscaped', 'BucketKey']),
                notifications=cleanup_window,
                cleanup_window=cleanup_window,
                cleanup_summary=summary,
                cleanup_slack_message=slack_message,
                notifications_output_filepath=notifications_path,
            )
            with open(notifications_path, 'r', encoding='utf8') as notifications_file:
                header_line = notifications_file.readline().strip()
            self.assertIn('CleanupPhase', header_line)
            self.assertIn('ScheduledCleanupDate', header_line)
        finally:
            os.unlink(notifications_path)


class TestStage3ProgressAndSummary(unittest.TestCase):
    def test_progress_reporter_emits_phase_and_memory_heartbeat(self):
        output = StringIO()
        reporter = Stage3ProgressReporter(
            interval_seconds=0.01,
            memory_reader=lambda: {'rss_mib': 123.5, 'peak_rss_mib': 456.5},
        )

        with contextlib.redirect_stdout(output):
            reporter.start()
            reporter.set_phase('unit_test', rows=12)
            time.sleep(0.04)
            reporter.stop()

        rendered = output.getvalue()
        self.assertIn('[stage3][progress] phase=unit_test status=started rows=12', rendered)
        self.assertIn('[stage3][heartbeat] phase=unit_test', rendered)
        self.assertIn('rss_mib=123.5 peak_rss_mib=456.5', rendered)

    def test_comparison_summary_counts_distinct_eligible_objects(self):
        local_inventory = pd.DataFrame(
            {
                'BucketKey': [
                    'bucket/file-a',
                    'bucket/file-a',
                    'bucket/file-b',
                    'bucket/skip/NOBACKUP',
                    'bucket/skip/file-c',
                ]
            }
        )
        glacier_inventory = pd.DataFrame({'BucketKey': ['bucket/file-b', 'bucket/old']})
        puts = pd.Series(['bucket/file-a', 'bucket/file-a'])
        deletes = pd.Series(['bucket/old'])
        bad_keys = pd.DataFrame([{'Issue': 'control_character'}])

        summary = build_comparison_summary(
            local_inventory,
            glacier_inventory,
            puts,
            deletes,
            bad_keys,
            ['bucket/skip/'],
            inventory_stats={'nrp_input_rows': 5},
        )

        self.assertEqual(summary['schema_version'], 1)
        self.assertEqual(summary['eligible_local_distinct_objects'], 2)
        self.assertEqual(summary['pending_put_rows'], 2)
        self.assertEqual(summary['pending_put_distinct_objects'], 1)
        self.assertEqual(summary['pending_upload_fraction'], 0.5)
        self.assertEqual(summary['delete_distinct_objects'], 1)
        self.assertEqual(summary['bad_key_rows'], 1)
        self.assertEqual(summary['inventory_processing']['nrp_input_rows'], 5)

    def test_comparison_summary_separates_retention_markers_from_data_fraction(self):
        marker = 'bucket/ephys/run/DATA_LIFECYCLE_RETENTION'
        summary = build_comparison_summary(
            pd.DataFrame({'BucketKey': ['bucket/ephys/run/file.bin', marker]}),
            pd.DataFrame({'BucketKey': []}),
            pd.Series([marker]),
            pd.Series(dtype='string'),
            pd.DataFrame(columns=['Issue']),
            [],
        )

        self.assertEqual(summary['eligible_local_distinct_objects'], 1)
        self.assertEqual(summary['pending_put_distinct_objects'], 1)
        self.assertEqual(summary['pending_data_put_distinct_objects'], 0)
        self.assertEqual(summary['pending_control_put_distinct_objects'], 1)
        self.assertEqual(summary['pending_upload_fraction'], 0.0)

    def test_main_writes_comparison_summary_and_expected_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, 'config.yaml')
            local_path = os.path.join(temp_dir, 'local.csv')
            glacier_path = os.path.join(temp_dir, 'glacier.csv')
            output_names = {
                'puts': 'puts.txt',
                'deletes': 'deletes.txt',
                'badkeys': 'badkeys.tsv',
                'notifications': 'notifications.csv',
                'cleanup': 'cleanup.csv',
                'cleanup_summary': 'cleanup-summary.csv',
                'slack': 'cleanup-slack.txt',
                'comparison_summary': 'comparison-summary.json',
            }
            output_paths = {name: os.path.join(temp_dir, filename) for name, filename in output_names.items()}

            with open(config_path, 'w', encoding='utf8') as config_file:
                config_file.write(
                    'backup:\n'
                    '  atomic_directories: []\n'
                    'deletion:\n'
                    '  s3_expire_days: 30\n'
                    '  cold_storage_expire_days: 365\n'
                    '  notification_days: 90\n'
                )
            with open(local_path, 'w', encoding='utf8') as local_file:
                local_file.write('2026-01-01T00:00:00Z,bucket/local-only,10\n')
            with open(glacier_path, 'w', encoding='utf8') as glacier_file:
                glacier_file.write('archive,bucket/glacier-only,20,2025-01-01T00:00:00Z,GLACIER\n')

            generate_inventory_outputs(
                config_path,
                local_path,
                glacier_path,
                output_paths['puts'],
                output_paths['deletes'],
                output_paths['badkeys'],
                output_paths['notifications'],
                output_paths['cleanup'],
                output_paths['cleanup_summary'],
                output_paths['slack'],
                output_paths['comparison_summary'],
                progress_interval_seconds=0,
            )

            with open(output_paths['comparison_summary'], 'r', encoding='utf8') as summary_file:
                summary = json.load(summary_file)
            self.assertEqual(summary['eligible_local_distinct_objects'], 1)
            self.assertEqual(summary['pending_put_distinct_objects'], 1)
            self.assertEqual(summary['pending_upload_fraction'], 1.0)
            self.assertEqual(summary['inventory_processing']['nrp_input_rows'], 1)
            for output_path in output_paths.values():
                self.assertTrue(os.path.isfile(output_path), output_path)


class TestStage4UploadFractionGuard(unittest.TestCase):
    def _write_summary(self, *, eligible, pending_rows, pending_distinct, fraction):
        summary = {
            'schema_version': 1,
            'eligible_local_distinct_objects': eligible,
            'pending_put_rows': pending_rows,
            'pending_put_distinct_objects': pending_distinct,
            'pending_data_put_rows': pending_rows,
            'pending_data_put_distinct_objects': pending_distinct,
            'pending_control_put_rows': 0,
            'pending_control_put_distinct_objects': 0,
            'pending_upload_fraction': fraction,
        }
        summary_file = tempfile.NamedTemporaryFile('w', delete=False, encoding='utf8')
        json.dump(summary, summary_file)
        summary_file.close()
        return summary_file.name

    def test_guard_allows_fraction_below_limit(self):
        summary_path = self._write_summary(eligible=10, pending_rows=2, pending_distinct=2, fraction=0.2)
        try:
            summary = validate_upload_fraction_guard(['bucket/a', 'bucket/b'], summary_path, 0.5)
        finally:
            os.unlink(summary_path)
        self.assertEqual(summary['pending_upload_fraction'], 0.2)

    def test_guard_allows_fraction_exactly_at_limit(self):
        summary_path = self._write_summary(eligible=4, pending_rows=2, pending_distinct=2, fraction=0.5)
        try:
            validate_upload_fraction_guard(['bucket/a', 'bucket/b'], summary_path, 0.5)
        finally:
            os.unlink(summary_path)

    def test_guard_blocks_fraction_above_limit(self):
        summary_path = self._write_summary(eligible=3, pending_rows=2, pending_distinct=2, fraction=2 / 3)
        try:
            with self.assertRaisesRegex(UploadFractionGuardError, 'no uploads were started'):
                validate_upload_fraction_guard(['bucket/a', 'bucket/b'], summary_path, 0.5)
        finally:
            os.unlink(summary_path)

    def test_guard_rejects_summary_that_does_not_match_puts(self):
        summary_path = self._write_summary(eligible=10, pending_rows=1, pending_distinct=1, fraction=0.1)
        try:
            with self.assertRaisesRegex(UploadFractionGuardError, 'PUT row count mismatch'):
                validate_upload_fraction_guard(['bucket/a', 'bucket/b'], summary_path, 0.5)
        finally:
            os.unlink(summary_path)

    def test_guard_does_not_count_tiny_retention_marker_as_data_upload(self):
        marker = 'bucket/ephys/run/DATA_LIFECYCLE_RETENTION'
        summary = {
            'schema_version': 1,
            'eligible_local_distinct_objects': 1,
            'pending_put_rows': 1,
            'pending_put_distinct_objects': 1,
            'pending_data_put_rows': 0,
            'pending_data_put_distinct_objects': 0,
            'pending_control_put_rows': 1,
            'pending_control_put_distinct_objects': 1,
            'pending_upload_fraction': 0.0,
        }
        with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf8') as summary_file:
            json.dump(summary, summary_file)
            summary_path = summary_file.name
        try:
            validate_upload_fraction_guard([marker], summary_path, 0.5)
        finally:
            os.unlink(summary_path)


class TestStage4PutParsing(unittest.TestCase):
    def test_normalize_put_key(self):
        self.assertEqual(normalize_put_key('braingeneers/path/file.bin'), 'braingeneers/path/file.bin')
        self.assertEqual(normalize_put_key('s3://braingeneers/path/file.bin'), 'braingeneers/path/file.bin')
        self.assertEqual(normalize_put_key('"braingeneers/path/file.bin"'), 'braingeneers/path/file.bin')
        self.assertEqual(normalize_put_key('braingeneers/path\r/file.bin'), 'braingeneers/path/file.bin')
        self.assertEqual(normalize_put_key('braingeneers/path\u240d/file.bin'), 'braingeneers/path/file.bin')
        self.assertIsNone(normalize_put_key(''))
        self.assertIsNone(normalize_put_key('braingeneers_only'))
        self.assertEqual(normalize_put_key('streamscope//hoodoscope/file.bin'), 'streamscope//hoodoscope/file.bin')

    def test_load_put_keys_parses_csv_quoted_rows(self):
        with tempfile.NamedTemporaryFile('w', delete=False, newline='', encoding='utf8') as puts_tmp:
            puts_tmp.write('"braingeneers/path/file,with,commas.bin"\n')
            puts_tmp.write('braingeneers/path/normal.bin\n')
            puts_tmp.flush()
            puts_path = puts_tmp.name

        try:
            keys = load_put_keys(puts_path)
        finally:
            os.unlink(puts_path)

        self.assertEqual(
            keys,
            [
                'braingeneers/path/file,with,commas.bin',
                'braingeneers/path/normal.bin',
            ],
        )

    def test_load_put_keys_fails_fast_on_malformed_rows(self):
        with tempfile.NamedTemporaryFile('w', delete=False, newline='', encoding='utf8') as puts_tmp:
            puts_tmp.write('braingeneers/path/good.bin\n')
            puts_tmp.write('bad_key_without_slash\n')
            puts_tmp.flush()
            puts_path = puts_tmp.name

        try:
            with self.assertRaisesRegex(ValueError, 'malformed PUT key'):
                load_put_keys(puts_path)
        finally:
            os.unlink(puts_path)

    def test_build_source_lookup_candidates_recovers_rclone_dot_and_scheme_artifacts(self):
        dot_key = 'braingeneersdev/asrobbin/game_spikes/．/exp2_cartpole_long_7_logs.pkl'
        scheme_key = 'braingeneers/ephys/s3:/braingeneersdev/hschweig/20185_baseline.raw.h5'
        both_key = 'braingeneers/．/s3:/braingeneersdev/test.pkl'

        self.assertEqual(
            build_source_lookup_candidates(dot_key),
            [
                'braingeneersdev/asrobbin/game_spikes/./exp2_cartpole_long_7_logs.pkl',
                'braingeneersdev/asrobbin/game_spikes/．/exp2_cartpole_long_7_logs.pkl',
            ],
        )
        self.assertEqual(
            build_source_lookup_candidates(scheme_key),
            [
                'braingeneers/ephys/s3://braingeneersdev/hschweig/20185_baseline.raw.h5',
                'braingeneers/ephys/s3:/braingeneersdev/hschweig/20185_baseline.raw.h5',
            ],
        )
        self.assertEqual(
            build_source_lookup_candidates(both_key),
            [
                'braingeneers/./s3://braingeneersdev/test.pkl',
                'braingeneers/．/s3://braingeneersdev/test.pkl',
                'braingeneers/./s3:/braingeneersdev/test.pkl',
                'braingeneers/．/s3:/braingeneersdev/test.pkl',
            ],
        )

    def test_build_source_lookup_candidates_preserves_leading_slash_object_key(self):
        self.assertEqual(
            build_source_lookup_candidates('streamscope//hoodoscope/file.bin'),
            ['streamscope//hoodoscope/file.bin'],
        )

    def test_badkeys_tsv_round_trips_escaped_records(self):
        records = parse_badkeys_tsv_text(
            'source_get_failed_after_head_success\tbucket/path/file.bin\n'
            'control_character\tbucket/path/with\\x01control.bin\n'
        )

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].issue, 'control_character')
        self.assertEqual(records[0].bucket_key, 'bucket/path/with\x01control.bin')
        self.assertEqual(records[1].issue, SOURCE_GET_FAILED_AFTER_HEAD_SUCCESS)


class TestStage4UploadSeam(unittest.TestCase):
    def _missing_head_object(self, *_args, **_kwargs):
        raise ClientError(
            {
                'Error': {'Code': '404', 'Message': 'Not Found'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'HeadObject',
        )

    def _build_source_opener(self, payload_by_url):
        def opener(url, mode):
            self.assertEqual(mode, 'rb')
            return BytesIO(payload_by_url[url])

        return opener

    def _missing_source_opener(self, _url, _mode):
        raise ClientError(
            {
                'Error': {'Code': 'NoSuchKey', 'Message': 'Not Found'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetObject',
        )

    def test_copy_file_uploads_successfully_with_injected_transport(self):
        payload = b'abcdefghijklmnopqrstuvwxyz'
        writes = []

        class CaptureWriter:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def write(self, data):
                writes.append(data)

        def destination_opener(url, mode, transport_params):
            self.assertEqual(mode, 'wb')
            self.assertEqual(transport_params['min_part_size'], 8)
            self.assertEqual(url, 's3://glacier-bucket/bucket/large-file.bin')
            return CaptureWriter()

        stats = ProgressStats(total_files=1)
        result = copy_file(
            source_key='bucket/large-file.bin',
            glacier_bucket='glacier-bucket',
            retries=2,
            retry_base_seconds=1.0,
            retry_max_seconds=5.0,
            stats=stats,
            head_object_func=self._missing_head_object,
            source_opener=self._build_source_opener({'s3://bucket/large-file.bin': payload}),
            destination_opener=destination_opener,
            s3_client=object(),
            multipart_part_size_bytes=8,
            copy_chunk_bytes=8,
            sleep_func=lambda _seconds: None,
            uniform_func=lambda _low, _high: 1.0,
        )

        self.assertEqual(result['status'], 'uploaded')
        self.assertEqual(result['bytes_copied'], len(payload))
        self.assertEqual(b''.join(writes), payload)
        snapshot = stats.snapshot()
        self.assertEqual(snapshot['retry_count'], 0)
        self.assertEqual(snapshot['stream_bytes'], len(payload))

    def test_copy_file_retries_then_fails_on_repeatable_ssl_error(self):
        payload = b'0123456789ABCDEF'
        destination_calls = []

        class FailingWriter:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def write(self, _data):
                raise SSLError(endpoint_url='https://example.invalid', error='EOF occurred in violation of protocol')

        def destination_opener(_url, _mode, transport_params=None):
            destination_calls.append('attempt')
            return FailingWriter()

        stats = ProgressStats(total_files=1)
        with contextlib.redirect_stderr(StringIO()):
            result = copy_file(
                source_key='bucket/retry-file.bin',
                glacier_bucket='glacier-bucket',
                retries=2,
                retry_base_seconds=1.0,
                retry_max_seconds=5.0,
                stats=stats,
                head_object_func=self._missing_head_object,
                source_opener=self._build_source_opener({'s3://bucket/retry-file.bin': payload}),
                destination_opener=destination_opener,
                s3_client=object(),
                multipart_part_size_bytes=4,
                copy_chunk_bytes=4,
                sleep_func=lambda _seconds: None,
                uniform_func=lambda _low, _high: 1.0,
            )

        self.assertEqual(result['status'], 'failed')
        self.assertIsInstance(result['error'], SSLError)
        self.assertEqual(result['bytes_copied'], 0)
        self.assertEqual(len(destination_calls), 3)
        snapshot = stats.snapshot()
        self.assertEqual(snapshot['retry_count'], 2)
        self.assertEqual(snapshot['failure_count'], 0)
        self.assertIn('SSLError', snapshot['retry_error_counts'])

    def test_copy_file_eventually_succeeds_after_transient_ssl_error(self):
        payload = b'0123456789ABCDEF'
        attempts = {'count': 0}

        class FlakyWriter:
            def __init__(self, should_fail):
                self.should_fail = should_fail

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def write(self, _data):
                if self.should_fail:
                    raise SSLError(endpoint_url='https://example.invalid', error='EOF occurred in violation of protocol')

        def destination_opener(_url, _mode, transport_params=None):
            writer = FlakyWriter(should_fail=(attempts['count'] == 0))
            attempts['count'] += 1
            return writer

        stats = ProgressStats(total_files=1)
        with contextlib.redirect_stderr(StringIO()):
            result = copy_file(
                source_key='bucket/flaky-file.bin',
                glacier_bucket='glacier-bucket',
                retries=2,
                retry_base_seconds=1.0,
                retry_max_seconds=5.0,
                stats=stats,
                head_object_func=self._missing_head_object,
                source_opener=self._build_source_opener({'s3://bucket/flaky-file.bin': payload}),
                destination_opener=destination_opener,
                s3_client=object(),
                multipart_part_size_bytes=4,
                copy_chunk_bytes=4,
                sleep_func=lambda _seconds: None,
                uniform_func=lambda _low, _high: 1.0,
            )

        self.assertEqual(result['status'], 'uploaded')
        self.assertEqual(result['bytes_copied'], len(payload))
        snapshot = stats.snapshot()
        self.assertEqual(snapshot['retry_count'], 1)

    def test_copy_file_marks_missing_source_when_head_is_visible(self):
        def visible_source_head(bucket_key, source_s3_client=None):
            self.assertEqual(bucket_key, 'bucket/head-visible-get-missing.bin')
            self.assertIsNone(source_s3_client)
            return {'ContentLength': 123}

        stats = ProgressStats(total_files=1)
        result = copy_file(
            source_key='bucket/head-visible-get-missing.bin',
            glacier_bucket='glacier-bucket',
            retries=0,
            retry_base_seconds=1.0,
            retry_max_seconds=5.0,
            stats=stats,
            head_object_func=self._missing_head_object,
            source_opener=self._missing_source_opener,
            destination_opener=lambda *_args, **_kwargs: None,
            s3_client=object(),
            source_head_object_func=visible_source_head,
            sleep_func=lambda _seconds: None,
            uniform_func=lambda _low, _high: 1.0,
        )

        self.assertEqual(result['status'], 'missing_source')
        self.assertEqual(result['head_visible_source_key'], 'bucket/head-visible-get-missing.bin')


if __name__ == '__main__':
    unittest.main()

from __future__ import annotations

import gzip
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from generate_cleanup_report import (  # noqa: E402
    MAX_SLACK_TEXT_CHARS,
    main,
    parse_args,
    render_slack_summary,
)


class CleanupReportTest(unittest.TestCase):
    def test_report_groups_atomic_dataset_and_keeps_non_atomic_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            config = tmp_path / "config.yaml"
            config.write_text(
                """
backup:
  atomic_directories:
    - bucket/ephys/*
deletion:
  s3_expire_days: 30
  cold_storage_expire_days: 365
  notification_days: 90
""".strip()
                + "\n",
                encoding="utf-8",
            )
            local = tmp_path / "local.csv.gz"
            with gzip.open(local, "wt", encoding="utf-8") as output:
                output.write("2025-12-12T00:00:00Z,bucket/ephys/run-a/a.bin,10\n")
                output.write("2025-12-10T00:00:00Z,bucket/ephys/run-a/b.bin,20\n")
                output.write("2025-12-12T00:00:00Z,bucket/ephys/run-a/DATA_LIFECYCLE_RETENTION,0\n")
                output.write("2025-12-12T00:00:00Z,bucket/misc/file.bin,30\n")
            glacier = tmp_path / "glacier.csv.gz"
            with gzip.open(glacier, "wt", encoding="utf-8") as output:
                output.write("archive,bucket/ephys/run-a/a.bin,10,2025-12-12T00:00:00.000Z,DEEP_ARCHIVE\n")
                output.write("archive,bucket/ephys/run-a/b.bin,20,2025-12-10T00:00:00.000Z,DEEP_ARCHIVE\n")
                output.write("archive,bucket/misc/file.bin,30,2025-12-12T00:00:00.000Z,DEEP_ARCHIVE\n")
                output.write("archive,bucket/archive/only.bin,40,2025-03-02T00:00:00.000Z,DEEP_ARCHIVE\n")
            activity = tmp_path / "activity.log"
            activity.write_text(
                "CompletedAtUTC,RunStartedAtUTC,BucketKey,UploadedBucketKey,BytesCopied,GlacierBucket,Result\n",
                encoding="utf-8",
            )
            manifest = tmp_path / "backup.json"
            manifest.write_text(
                json.dumps({"schema_version": 1, "status": "complete", "run_id": "backup-1"}),
                encoding="utf-8",
            )
            output_dir = tmp_path / "report"
            argv = [
                "generate_cleanup_report.py",
                "--config",
                str(config),
                "--local-inventory",
                str(local),
                "--glacier-inventory",
                str(glacier),
                "--activity-log",
                str(activity),
                "--backup-manifest",
                str(manifest),
                "--output-dir",
                str(output_dir),
                "--run-id",
                "report-1",
                "--report-uri",
                "s3://bucket/reports/report-1/",
                "--report-url",
                "https://data-explorer.example/report-1",
                "--data-explorer-url",
                "https://data-explorer.example",
                "--as-of",
                "2026-01-01T00:00:00Z",
            ]

            with patch.object(sys, "argv", argv):
                main(parse_args())

            report = json.loads((output_dir / "cleanup-report.json").read_text(encoding="utf-8"))
            self.assertFalse(report["deletion_enabled"])
            self.assertEqual(report["candidate_count"], 3)
            atomic = [
                item for item in report["candidates"] if item["target_type"] == "atomic_dataset"
            ]
            self.assertEqual(len(atomic), 1)
            self.assertEqual(atomic[0]["object_count"], 2)
            self.assertTrue(
                all(
                    "DATA_LIFECYCLE_RETENTION" not in item["target"]
                    for item in report["candidates"]
                )
            )
            slack_summary = (output_dir / "cleanup-report-slack.txt").read_text(
                encoding="utf-8"
            )
            self.assertIn("*Monthly data retention policy report*", slack_summary)
            self.assertIn("Candidate entities: 3 (Ceph/S3: 2; Glacier-only: 1)", slack_summary)
            self.assertIn("*Earliest policy candidates*", slack_summary)
            self.assertIn("Full report:", slack_summary)
            self.assertLessEqual(len(slack_summary.rstrip("\n")), MAX_SLACK_TEXT_CHARS)
            self.assertFalse((output_dir / "completion-notification.json").exists())
            completion = json.loads(
                (output_dir / "completion-manifest.json").read_text(encoding="utf-8")
            )
            self.assertIn("cleanup-report-slack.txt", completion["artifacts"])
            self.assertNotIn("completion-notification.json", completion["artifacts"])
            self.assertGreater((output_dir / "cleanup-report.html").stat().st_size, 0)
            self.assertGreater((output_dir / "cleanup-report.pdf").stat().st_size, 0)

    def test_slack_summary_handles_an_empty_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cleanup-report-slack.txt"
            render_slack_summary(
                path,
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                [],
                "https://data-explorer.example/report-1",
            )
            summary = path.read_text(encoding="utf-8")

            self.assertIn("Candidate entities: 0 (Ceph/S3: 0; Glacier-only: 0)", summary)
            self.assertIn("No policy candidates were found", summary)
            self.assertNotIn("*Earliest policy candidates*", summary)
            self.assertLessEqual(len(summary.rstrip("\n")), MAX_SLACK_TEXT_CHARS)

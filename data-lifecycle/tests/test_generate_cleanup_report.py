from __future__ import annotations

import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from generate_cleanup_report import main, parse_args  # noqa: E402


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
                "--channel-id",
                "C0123456789",
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
            notification = json.loads(
                (output_dir / "completion-notification.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(notification["candidates"]), 3)
            self.assertGreater((output_dir / "cleanup-report.html").stat().st_size, 0)
            self.assertGreater((output_dir / "cleanup-report.pdf").stat().st_size, 0)

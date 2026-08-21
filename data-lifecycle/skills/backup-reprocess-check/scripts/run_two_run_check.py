#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_BUCKET = "braingeneers-backups-inventory"
DEFAULT_PREFIX = "braingeneers-backups-glacier/daily-inventory/"
DEFAULT_PROFILE = "aws-braingeneers-backups"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}Z$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_stamp() -> str:
    return utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def run_command(
    cmd: list[str],
    cwd: Path = REPO_ROOT,
    log_path: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    if log_path is None:
        return subprocess.run(cmd, cwd=str(cwd), env=env, text=True, capture_output=True)
    with log_path.open("a", encoding="utf8") as log:
        log.write(f"\n$ {' '.join(cmd)}\n")
        log.flush()
        process = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        assert process.stdout is not None
        for line in process.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
        return subprocess.CompletedProcess(cmd, process.wait())


def parse_manifest_uri(uri: str) -> tuple[str, str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError(f"Expected s3:// manifest URI, got {uri!r}")
    key = parsed.path.lstrip("/")
    parts = key.rstrip("/").split("/")
    if len(parts) < 2 or parts[-1] != "manifest.json":
        raise ValueError(f"Expected manifest URI ending in manifest.json, got {uri!r}")
    date = parts[-2]
    if not DATE_RE.match(date):
        raise ValueError(f"Could not parse manifest date from {uri!r}")
    prefix = "/".join(parts[:-2]) + "/"
    return parsed.netloc, prefix, date


def next_manifest_date(manifest_date: str) -> str:
    base = datetime.strptime(manifest_date, "%Y-%m-%dT%H-%MZ")
    return (base + timedelta(days=1)).strftime("%Y-%m-%dT%H-%MZ")


def manifest_uri(bucket: str, prefix: str, manifest_date: str) -> str:
    clean_prefix = prefix.strip("/")
    return f"s3://{bucket}/{clean_prefix}/{manifest_date}/manifest.json"


def manifest_key(prefix: str, manifest_date: str) -> str:
    return f"{prefix.strip('/')}/{manifest_date}/manifest.json"


def latest_manifest_date(bucket: str, prefix: str, profile: str) -> str:
    cmd = ["aws", "--profile", profile, "s3", "ls", f"s3://{bucket}/{prefix}"]
    result = run_command(cmd)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    dates = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if not parts:
            continue
        candidate = parts[-1].rstrip("/")
        if DATE_RE.match(candidate):
            dates.append(candidate)
    if not dates:
        raise RuntimeError(f"No manifest date folders found under s3://{bucket}/{prefix}")
    return sorted(dates)[-1]


def head_manifest(bucket: str, prefix: str, manifest_date: str, profile: str) -> subprocess.CompletedProcess:
    return run_command(
        [
            "aws",
            "--profile",
            profile,
            "s3api",
            "head-object",
            "--bucket",
            bucket,
            "--key",
            manifest_key(prefix, manifest_date),
        ]
    )


def wait_for_manifest(args: argparse.Namespace, artifact_root: Path) -> tuple[str, dict[str, object]]:
    if args.after_manifest_uri:
        bucket, prefix, previous_date = parse_manifest_uri(args.after_manifest_uri)
        target_date = next_manifest_date(previous_date)
    else:
        bucket = args.inventory_bucket
        prefix = args.inventory_prefix
        target_date = args.target_manifest_date or latest_manifest_date(bucket, prefix, args.aws_profile)

    uri = manifest_uri(bucket, prefix, target_date)
    wait_log = artifact_root / "manifest-wait.log"
    wait_log.write_text(f"{utc_stamp()} target {uri}\n", encoding="utf8")

    while True:
        result = head_manifest(bucket, prefix, target_date, args.aws_profile)
        if result.returncode == 0:
            metadata = json.loads(result.stdout)
            (artifact_root / "manifest-head.json").write_text(
                json.dumps(metadata, indent=2, default=str) + "\n",
                encoding="utf8",
            )
            copy_result = run_command(
                ["aws", "--profile", args.aws_profile, "s3", "cp", uri, str(artifact_root / "manifest.json")]
            )
            if copy_result.returncode != 0:
                raise RuntimeError(copy_result.stderr or copy_result.stdout)
            with wait_log.open("a", encoding="utf8") as log:
                log.write(f"{utc_stamp()} online {uri}\n")
            return target_date, metadata

        with wait_log.open("a", encoding="utf8") as log:
            log.write(f"{utc_stamp()} unavailable {uri}: {result.stderr.strip() or result.stdout.strip()}\n")
        print(f"[{utc_stamp()}] Manifest not online yet: {uri}. Sleeping {args.manifest_poll_seconds}s.", flush=True)
        time.sleep(args.manifest_poll_seconds)


def build_image(image_tag: str, artifact_root: Path) -> str:
    log_path = artifact_root / "docker-build.log"
    result = run_command(["docker", "build", "-f", "docker/Dockerfile", "-t", image_tag, "."], log_path=log_path)
    if result.returncode != 0:
        raise RuntimeError(f"Docker build failed; see {log_path}")
    inspect = run_command(["docker", "image", "inspect", image_tag, "--format", "{{.Id}}"])
    if inspect.returncode != 0:
        raise RuntimeError(inspect.stderr or inspect.stdout)
    return inspect.stdout.strip()


def write_repo_metadata(artifact_root: Path, image_tag: str, image_id: str, manifest_date: str) -> None:
    commit = run_command(["git", "rev-parse", "HEAD"]).stdout.strip()
    status = run_command(["git", "status", "--short"]).stdout
    metadata = {
        "created_at_utc": utc_stamp(),
        "commit": commit,
        "git_status_short": status,
        "image_tag": image_tag,
        "image_id": image_id,
        "manifest_date": manifest_date,
    }
    (artifact_root / "run-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf8")


def run_backup_once(args: argparse.Namespace, artifact_root: Path, image_tag: str, run_name: str) -> None:
    run_root = artifact_root / run_name
    tmp_root = run_root / "tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    (run_root / "start.utc").write_text(utc_stamp() + "\n", encoding="utf8")
    cmd = [
        "docker",
        "run",
        "--rm",
        "-t",
        "-v",
        f"{Path.home() / '.config' / 'rclone'}:/home/jovyan/.config/rclone:ro",
        "-v",
        f"{Path.home() / '.aws'}:/home/jovyan/.aws:ro",
        "-v",
        f"{tmp_root.resolve()}:/tmp",
        image_tag,
        "src/run_data_lifecycle.sh",
        "--stage2-workers",
        str(args.stage2_workers),
        "--stage4-workers",
        str(args.stage4_workers),
    ]
    result = run_command(cmd, log_path=run_root / "run.log")
    (run_root / "exit_code.txt").write_text(str(result.returncode) + "\n", encoding="utf8")
    (run_root / "end.utc").write_text(utc_stamp() + "\n", encoding="utf8")
    if result.returncode != 0:
        raise RuntimeError(f"{run_name} failed with exit code {result.returncode}; see {run_root / 'run.log'}")


def analyze(artifact_root: Path, report_path: Path) -> None:
    cmd = [sys.executable, str(SCRIPT_DIR / "analyze_two_run_check.py"), str(artifact_root), "--report-path", str(report_path)]
    result = run_command(cmd, log_path=artifact_root / "analysis.log")
    if result.returncode != 0:
        raise RuntimeError(f"Analysis failed; see {artifact_root / 'analysis.log'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a full two-run data-lifecycle backup reprocess check.")
    parser.add_argument("--after-manifest-uri", help="Wait for the daily manifest after this manifest URI.")
    parser.add_argument("--target-manifest-date", help="Use this manifest date directly, e.g. 2026-05-22T01-00Z.")
    parser.add_argument("--aws-profile", default=DEFAULT_PROFILE)
    parser.add_argument("--inventory-bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--inventory-prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--manifest-poll-seconds", type=int, default=3600)
    parser.add_argument("--stage2-workers", type=int, default=8)
    parser.add_argument("--stage4-workers", type=int, default=2)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / "plans")
    parser.add_argument("--image-tag", default="")
    parser.add_argument("--skip-build", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.after_manifest_uri and args.target_manifest_date:
        raise SystemExit("Use only one of --after-manifest-uri or --target-manifest-date.")
    if args.manifest_poll_seconds < 60:
        raise SystemExit("--manifest-poll-seconds must be at least 60.")

    if args.after_manifest_uri:
        _bucket, _prefix, previous_date = parse_manifest_uri(args.after_manifest_uri)
        output_date = next_manifest_date(previous_date)[:10]
    elif args.target_manifest_date:
        output_date = args.target_manifest_date[:10]
    else:
        output_date = utc_now().strftime("%Y-%m-%d")

    artifact_root = args.output_root / f"manifest-reprocess-check-{output_date}"
    if artifact_root.exists():
        suffix = utc_now().strftime("%Y%m%dT%H%M%SZ")
        artifact_root = args.output_root / f"manifest-reprocess-check-{output_date}-{suffix}"
    artifact_root.mkdir(parents=True)
    report_path = artifact_root.with_suffix(".md")

    print(f"[{utc_stamp()}] Artifacts: {artifact_root}", flush=True)
    manifest_date, _metadata = wait_for_manifest(args, artifact_root)
    image_tag = args.image_tag or f"braingeneers/data-lifecycle:manifest-reprocess-check-{manifest_date[:10]}"
    if args.skip_build:
        inspect = run_command(["docker", "image", "inspect", image_tag, "--format", "{{.Id}}"])
        if inspect.returncode != 0:
            raise RuntimeError(inspect.stderr or inspect.stdout)
        image_id = inspect.stdout.strip()
    else:
        image_id = build_image(image_tag, artifact_root)
    write_repo_metadata(artifact_root, image_tag, image_id, manifest_date)

    for run_name in ("run1", "run2"):
        print(f"[{utc_stamp()}] Starting {run_name}.", flush=True)
        run_backup_once(args, artifact_root, image_tag, run_name)
        print(f"[{utc_stamp()}] Completed {run_name}.", flush=True)

    analyze(artifact_root, report_path)
    print(f"[{utc_stamp()}] Report: {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

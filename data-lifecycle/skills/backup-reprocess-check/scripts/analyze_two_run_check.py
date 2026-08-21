#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


MISSING_SOURCE_RE = re.compile(r"Missing source \(skipped\): .*? s3://(.+)$")
SUMMARY_MISSING_SOURCE_RE = re.compile(r"^\s*s3://(.+)$")
SOURCE_ERROR_MARKERS = (
    " - unable to access bucket:",
    " - An error occurred",
)
SOURCE_ACCESS_ISSUE = "source_get_failed_after_head_success"


@dataclass
class RunSummary:
    name: str
    root: Path
    tmp: Path
    exit_code: str
    puts: list[str]
    puts_set: set[str]
    duplicate_puts: list[str]
    activity_rows: list[dict[str, str]]
    activity_by_key: dict[str, list[dict[str, str]]]
    activity_results: Counter
    uploaded_keys: set[str]
    already_present_keys: set[str]
    badkeys: set[tuple[str, str]]
    missing_sources: set[str]
    log_error_lines: list[str]


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf8", errors="replace")


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf8"))
    except json.JSONDecodeError:
        return {}


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.rstrip("\n") for line in path.read_text(encoding="utf8", errors="replace").splitlines() if line]


def read_puts(path: Path) -> list[str]:
    if not path.exists():
        return []
    keys: list[str] = []
    with path.open("r", encoding="utf8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            keys.append(",".join(row).strip())
    return [key for key in keys if key]


def duplicates(values: Iterable[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def read_activity(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_badkeys(path: Path) -> set[tuple[str, str]]:
    output: set[tuple[str, str]] = set()
    if not path.exists():
        return output
    for line in read_lines(path):
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0] and parts[1]:
            output.add((parts[0], parts[1]))
    return output


def strip_source_error(value: str) -> str:
    for marker in SOURCE_ERROR_MARKERS:
        if marker in value:
            return value.split(marker, 1)[0]
    return value.rsplit(" - ", 1)[0] if " - " in value else value


def parse_missing_sources(log_text: str) -> set[str]:
    missing: set[str] = set()
    in_summary = False
    for line in log_text.splitlines():
        match = MISSING_SOURCE_RE.search(line)
        if match:
            missing.add(strip_source_error(match.group(1)))
            continue
        if line.strip() == "Skipped Missing Source Files:":
            in_summary = True
            continue
        if in_summary:
            if not line.strip():
                in_summary = False
                continue
            summary_match = SUMMARY_MISSING_SOURCE_RE.search(line)
            if summary_match:
                missing.add(strip_source_error(summary_match.group(1)))
    return missing


def interesting_log_lines(log_text: str) -> list[str]:
    tokens = (
        "NoSuchKey",
        "Missing source",
        "Source access bad keys",
        "Upload failed",
        "WARNING:",
        "ERROR:",
        "bad key",
        "badkeys",
    )
    lines = []
    for line in log_text.splitlines():
        if any(token in line for token in tokens):
            lines.append(line)
    return lines[:500]


def load_run(root: Path, name: str) -> RunSummary:
    run_root = root / name
    tmp = run_root / "tmp"
    puts = read_puts(tmp / "puts.txt")
    activity_rows = read_activity(tmp / "activity.log")
    activity_by_key: dict[str, list[dict[str, str]]] = {}
    for row in activity_rows:
        key = row.get("BucketKey") or ""
        if key:
            activity_by_key.setdefault(key, []).append(row)
    activity_results = Counter(row.get("Result") or "unknown" for row in activity_rows)
    log_text = read_text(run_root / "run.log")
    return RunSummary(
        name=name,
        root=run_root,
        tmp=tmp,
        exit_code=read_text(run_root / "exit_code.txt").strip() or "missing",
        puts=puts,
        puts_set=set(puts),
        duplicate_puts=duplicates(puts),
        activity_rows=activity_rows,
        activity_by_key=activity_by_key,
        activity_results=activity_results,
        uploaded_keys={row.get("BucketKey", "") for row in activity_rows if row.get("Result") == "uploaded"},
        already_present_keys={
            row.get("BucketKey", "") for row in activity_rows if row.get("Result") == "already_present_skipped"
        },
        badkeys=read_badkeys(tmp / "badkeys.tsv"),
        missing_sources=parse_missing_sources(log_text),
        log_error_lines=interesting_log_lines(log_text),
    )


def write_list(path: Path, values: Iterable[str]) -> None:
    items = sorted(set(values))
    path.write_text("".join(f"{item}\n" for item in items), encoding="utf8")


def write_badkey_list(path: Path, values: Iterable[tuple[str, str]]) -> None:
    items = sorted(set(values))
    path.write_text("".join(f"{issue}\t{key}\n" for issue, key in items), encoding="utf8")


def md_list(items: Iterable[str], limit: int = 10) -> list[str]:
    values = list(items)
    if not values:
        return ["- none"]
    output = [f"- `{value}`" for value in values[:limit]]
    if len(values) > limit:
        output.append(f"- ... {len(values) - limit} more")
    return output


def artifact_line(path: Path) -> str:
    return f"`{path}`" if path.exists() else f"`{path}` (missing)"


def manifest_uri(metadata: dict[str, object]) -> str:
    manifest_date = metadata.get("manifest_date")
    if isinstance(manifest_date, str) and manifest_date:
        return (
            "s3://braingeneers-backups-inventory/braingeneers-backups-glacier/"
            f"daily-inventory/{manifest_date}/manifest.json"
        )
    return "unknown"


def build_report(root: Path, run1: RunSummary, run2: RunSummary, analysis_dir: Path) -> str:
    metadata = read_json(root / "run-metadata.json")
    manifest_head = read_json(root / "manifest-head.json")
    puts_intersection = run1.puts_set & run2.puts_set
    puts_only_run1 = run1.puts_set - run2.puts_set
    puts_only_run2 = run2.puts_set - run1.puts_set
    activity_keys1 = set(run1.activity_by_key)
    activity_keys2 = set(run2.activity_by_key)
    uploaded_both = run1.uploaded_keys & run2.uploaded_keys
    run1_uploaded_then_skipped = run1.uploaded_keys & run2.already_present_keys
    repeated_missing = run1.missing_sources & run2.missing_sources
    badkeys_repeated = run1.badkeys & run2.badkeys
    source_access_badkeys = {
        (issue, key)
        for issue, key in (run1.badkeys | run2.badkeys)
        if issue == SOURCE_ACCESS_ISSUE
    }

    findings: list[tuple[str, str]] = []
    if uploaded_both:
        findings.append(("critical", f"{len(uploaded_both)} key(s) were uploaded in both runs."))
    if run2.uploaded_keys - run1.uploaded_keys:
        findings.append(
            (
                "info",
                (
                    f"{len(run2.uploaded_keys - run1.uploaded_keys)} key(s) were uploaded only in run 2. "
                    "This is not duplicate reprocessing, but review it as source-listing drift or live source churn."
                ),
            )
        )
    if repeated_missing:
        findings.append(
            (
                "warning",
                (
                    f"{len(repeated_missing)} missing-source key(s) repeated across both runs. "
                    "This is suspicious and needs source key-shape or Head/GetObject analysis."
                ),
            )
        )
    if source_access_badkeys:
        findings.append(
            (
                "warning",
                f"{len(source_access_badkeys)} source HeadObject-success/GetObject-missing badkey(s) were reported.",
            )
        )
    if badkeys_repeated:
        findings.append(("info", f"{len(badkeys_repeated)} badkeys.tsv issue/key pair(s) repeated across both runs."))
    if not findings:
        findings.append(("ok", "No duplicate uploads or repeated source failure patterns were detected."))

    lines = [
        f"# Backup Reprocess Check - {root.name}",
        "",
        "## Check Metadata",
        "",
        f"- Manifest URI: `{manifest_uri(metadata)}`",
        f"- Manifest online/object LastModified: `{manifest_head.get('LastModified', 'unknown')}`",
        f"- Manifest ETag: `{manifest_head.get('ETag', 'unknown')}`",
        f"- Docker image: `{metadata.get('image_tag', 'unknown')}`",
        f"- Docker image ID: `{metadata.get('image_id', 'unknown')}`",
        f"- Commit: `{metadata.get('commit', 'unknown')}`",
        f"- Captured at UTC: `{metadata.get('created_at_utc', 'unknown')}`",
        "",
        "## Run Summary",
        "",
        "| Metric | Run 1 | Run 2 |",
        "| --- | ---: | ---: |",
        f"| Exit code | {run1.exit_code} | {run2.exit_code} |",
        f"| PUT lines | {len(run1.puts)} | {len(run2.puts)} |",
        f"| Unique PUT keys | {len(run1.puts_set)} | {len(run2.puts_set)} |",
        f"| Duplicate PUT keys | {len(run1.duplicate_puts)} | {len(run2.duplicate_puts)} |",
        f"| Activity rows | {len(run1.activity_rows)} | {len(run2.activity_rows)} |",
        f"| Uploaded | {run1.activity_results.get('uploaded', 0)} | {run2.activity_results.get('uploaded', 0)} |",
        (
            f"| Already present skipped | {run1.activity_results.get('already_present_skipped', 0)} | "
            f"{run2.activity_results.get('already_present_skipped', 0)} |"
        ),
        f"| Missing sources parsed from log | {len(run1.missing_sources)} | {len(run2.missing_sources)} |",
        f"| badkeys.tsv entries | {len(run1.badkeys)} | {len(run2.badkeys)} |",
        "",
        "## Cross-Run Comparison",
        "",
        f"- PUT set intersection: `{len(puts_intersection)}`",
        f"- PUTs only in run 1: `{len(puts_only_run1)}`",
        f"- PUTs only in run 2: `{len(puts_only_run2)}`",
        f"- Activity key intersection: `{len(activity_keys1 & activity_keys2)}`",
        f"- Activity keys only in run 1: `{len(activity_keys1 - activity_keys2)}`",
        f"- Activity keys only in run 2: `{len(activity_keys2 - activity_keys1)}`",
        f"- Uploaded in both runs: `{len(uploaded_both)}`",
        f"- Run 1 uploaded then run 2 already-present skipped: `{len(run1_uploaded_then_skipped)}`",
        f"- Repeated missing-source keys: `{len(repeated_missing)}`",
        f"- Repeated badkeys.tsv issue/key pairs: `{len(badkeys_repeated)}`",
        "",
        "## Findings",
        "",
    ]
    for severity, text in findings:
        lines.append(f"- **{severity.upper()}**: {text}")

    if repeated_missing:
        lines.extend(
            [
                "",
                "## Repeated Missing-Source Keys",
                "",
                (
                    "These keys repeated across both runs. Treat this as an unresolved steady-state risk until "
                    "manual checks prove the source objects truly disappeared or the repeated pattern is expected."
                ),
                "",
                *md_list(sorted(repeated_missing), limit=20),
            ]
        )

    if source_access_badkeys:
        lines.extend(
            [
                "",
                "## Source HeadObject/GetObject Badkeys",
                "",
                *md_list([f"{issue}\t{key}" for issue, key in sorted(source_access_badkeys)], limit=20),
            ]
        )

    if badkeys_repeated:
        lines.extend(
            [
                "",
                "## Repeated badkeys.tsv Entries",
                "",
                *md_list([f"{issue}\t{key}" for issue, key in sorted(badkeys_repeated)], limit=20),
            ]
        )

    manual_probe = read_text(analysis_dir / "manual_source_probe.txt").strip()
    if manual_probe:
        lines.extend(
            [
                "",
                "## Manual Source Probe",
                "",
                manual_probe,
            ]
        )

    lines.extend(
        [
            "",
            "## Analysis Artifacts",
            "",
            f"- Repeated missing sources: {artifact_line(analysis_dir / 'repeated_missing_sources.txt')}",
            f"- Uploaded in both runs: {artifact_line(analysis_dir / 'uploaded_in_both_runs.txt')}",
            f"- Repeated badkeys: {artifact_line(analysis_dir / 'repeated_badkeys.tsv')}",
            f"- PUTs only in run 1: {artifact_line(analysis_dir / 'puts_only_run1.txt')}",
            f"- PUTs only in run 2: {artifact_line(analysis_dir / 'puts_only_run2.txt')}",
            f"- Run 1 notable log lines: {artifact_line(analysis_dir / 'run1_notable_log_lines.txt')}",
            f"- Run 2 notable log lines: {artifact_line(analysis_dir / 'run2_notable_log_lines.txt')}",
            "",
            "## Operator Notes",
            "",
            (
                "- Repeated missing-source keys require root-cause checks. Inspect raw rclone paths, source "
                "`HeadObject`, source `GetObject`, and alternate key shapes with leading or doubled slashes."
            ),
            "- `already_present_skipped` in run 2 is the expected durable signal for keys uploaded in run 1.",
        ]
    )
    return "\n".join(lines) + "\n"


def analyze(root: Path, report_path: Path | None = None) -> tuple[str, list[tuple[str, str]]]:
    root = root.resolve()
    analysis_dir = root / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    run1 = load_run(root, "run1")
    run2 = load_run(root, "run2")

    repeated_missing = run1.missing_sources & run2.missing_sources
    uploaded_both = run1.uploaded_keys & run2.uploaded_keys
    repeated_badkeys = run1.badkeys & run2.badkeys
    write_list(analysis_dir / "repeated_missing_sources.txt", repeated_missing)
    write_list(analysis_dir / "uploaded_in_both_runs.txt", uploaded_both)
    write_badkey_list(analysis_dir / "repeated_badkeys.tsv", repeated_badkeys)
    write_list(analysis_dir / "puts_only_run1.txt", run1.puts_set - run2.puts_set)
    write_list(analysis_dir / "puts_only_run2.txt", run2.puts_set - run1.puts_set)
    write_list(analysis_dir / "run1_notable_log_lines.txt", run1.log_error_lines)
    write_list(analysis_dir / "run2_notable_log_lines.txt", run2.log_error_lines)

    report = build_report(root, run1, run2, analysis_dir)
    if report_path is None:
        report_path = root.with_suffix(".md")
    report_path.write_text(report, encoding="utf8")

    findings: list[tuple[str, str]] = []
    if uploaded_both:
        findings.append(("critical", f"{len(uploaded_both)} uploaded in both runs"))
    if repeated_missing:
        findings.append(("warning", f"{len(repeated_missing)} repeated missing-source keys"))
    if repeated_badkeys:
        findings.append(("info", f"{len(repeated_badkeys)} repeated badkeys"))
    return report, findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze a two-run data-lifecycle backup reprocess check.")
    parser.add_argument("artifact_root", type=Path, help="Directory containing run1/ and run2/ artifacts.")
    parser.add_argument("--report-path", type=Path, default=None, help="Markdown report output path.")
    parser.add_argument("--fail-on-issues", action="store_true", help="Exit nonzero if suspicious findings exist.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report, findings = analyze(args.artifact_root, args.report_path)
    print(report)
    if args.fail_on_issues and any(severity in {"critical", "warning"} for severity, _ in findings):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

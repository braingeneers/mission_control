from __future__ import annotations

import codecs
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CONTROL_CHARACTER_ISSUE = "control_character"
SOURCE_GET_FAILED_AFTER_HEAD_SUCCESS = "source_get_failed_after_head_success"

ISSUE_DESCRIPTIONS = {
    CONTROL_CHARACTER_ISSUE: "Inventory key contains control characters and was excluded from processing.",
    SOURCE_GET_FAILED_AFTER_HEAD_SUCCESS: (
        "Source object metadata was visible with HeadObject, but GetObject returned missing-key during backup."
    ),
}


@dataclass(frozen=True)
class BadKeyRecord:
    issue: str
    bucket_key_escaped: str
    bucket_key: str


def escape_bucket_key(bucket_key: str) -> str:
    return str(bucket_key).encode("unicode_escape").decode("ascii")


def unescape_bucket_key(bucket_key_escaped: str) -> str:
    try:
        return codecs.decode(bucket_key_escaped, "unicode_escape")
    except Exception:
        return bucket_key_escaped


def describe_issue(issue: str) -> str:
    return ISSUE_DESCRIPTIONS.get(issue, "Data lifecycle reported this key in badkeys.tsv.")


def make_badkey_record(issue: str, bucket_key: str) -> BadKeyRecord:
    clean_key = str(bucket_key or "").strip()
    return BadKeyRecord(
        issue=str(issue or "").strip(),
        bucket_key_escaped=escape_bucket_key(clean_key),
        bucket_key=clean_key,
    )


def parse_badkeys_tsv_text(tsv_text: str) -> list[BadKeyRecord]:
    records: list[BadKeyRecord] = []
    for raw_line in (tsv_text or "").splitlines():
        line = raw_line.rstrip("\n")
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        issue = parts[0].strip()
        bucket_key_escaped = parts[1].strip()
        if not issue or not bucket_key_escaped:
            continue
        records.append(
            BadKeyRecord(
                issue=issue,
                bucket_key_escaped=bucket_key_escaped,
                bucket_key=unescape_bucket_key(bucket_key_escaped),
            )
        )
    return dedupe_badkey_records(records)


def read_badkeys_tsv(path: str | os.PathLike[str]) -> list[BadKeyRecord]:
    badkeys_path = Path(path)
    if not badkeys_path.exists():
        return []
    return parse_badkeys_tsv_text(badkeys_path.read_text(encoding="utf8"))


def dedupe_badkey_records(records: Iterable[BadKeyRecord]) -> list[BadKeyRecord]:
    by_key: dict[tuple[str, str], BadKeyRecord] = {}
    for record in records:
        if not record.issue or not record.bucket_key_escaped:
            continue
        by_key[(record.issue, record.bucket_key_escaped)] = record
    return [by_key[key] for key in sorted(by_key)]


def merge_badkey_records(*record_groups: Iterable[BadKeyRecord]) -> list[BadKeyRecord]:
    merged: list[BadKeyRecord] = []
    for records in record_groups:
        merged.extend(records)
    return dedupe_badkey_records(merged)


def write_badkeys_tsv(path: str | os.PathLike[str], records: Iterable[BadKeyRecord]) -> list[BadKeyRecord]:
    sorted_records = dedupe_badkey_records(records)
    with open(path, "w", encoding="utf8") as file_handle:
        for record in sorted_records:
            file_handle.write(f"{record.issue}\t{record.bucket_key_escaped}\n")
    return sorted_records


def source_get_failed_records(records: Iterable[BadKeyRecord]) -> list[BadKeyRecord]:
    return [
        record
        for record in dedupe_badkey_records(records)
        if record.issue == SOURCE_GET_FAILED_AFTER_HEAD_SUCCESS
    ]


def render_source_get_failed_slack_section(
    records: Iterable[BadKeyRecord],
    max_examples: int = 5,
) -> str:
    source_records = source_get_failed_records(records)
    if not source_records:
        return ""

    example_count = max(0, int(max_examples))
    examples = source_records[:example_count]
    lines = [
        "Backup source access issues:",
        (
            f"- {len(source_records)} key(s) were listed by source inventory and had source HeadObject metadata, "
            "but GetObject returned missing-key during backup."
        ),
        "- Details are recorded in `badkeys.tsv` as `source_get_failed_after_head_success`.",
    ]
    if examples:
        lines.append("Examples:")
        for record in examples:
            lines.append(f"- `{record.bucket_key}`")
    remaining = len(source_records) - len(examples)
    if remaining > 0:
        lines.append(f"- +{remaining} more in `badkeys.tsv`")
    return "\n".join(lines) + "\n"


def append_source_get_failed_slack_section(
    slack_message: str,
    records: Iterable[BadKeyRecord],
    max_examples: int = 5,
) -> str:
    section = render_source_get_failed_slack_section(records, max_examples=max_examples)
    base = (slack_message or "").rstrip()
    marker = "\nBackup source access issues:"
    if marker in f"\n{base}":
        base = f"\n{base}".split(marker, 1)[0].lstrip().rstrip()
    if not section:
        return base + "\n" if base else ""
    if base:
        return base + "\n\n" + section
    return section

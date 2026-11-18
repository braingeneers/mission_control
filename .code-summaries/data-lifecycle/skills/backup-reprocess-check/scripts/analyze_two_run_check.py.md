# analyze_two_run_check.py

**Path:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py`
**Module:** `data-lifecycle.skills.backup-reprocess-check.scripts.analyze_two_run_check`
**Feature Area:** `data-lifecycle`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Analyzes and compares two consecutive backup pipeline execution runs (Run 1 and Run 2) to detect anomalies, regressions, missing source objects, duplicate puts, and activity discrepancies.

## Connections
- **Shared data:** Consumes activity and badkey logs produced by `run_two_run_check.py` and `stage4_process_puts_deletes.py`.
- **Shared data:** Formats badkey records defined in `data-lifecycle/src/badkeys.py`.

## Dependencies
None

## Classes
### RunSummary()
> Dataclass aggregating per-run state, exit code, put keys, duplicate puts, activity counts, and badkey sets.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:25`
**Kind:** class. **Instantiated by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:158 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None

## Functions
### `read_text(path: Path) -> str`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:157 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:162 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:350 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:43`
### `read_json(path: Path) -> dict[str, object]`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:214 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:215 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:49`
### `read_lines(path: Path) -> list[str]`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:93 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:58`
### `read_puts(path: Path) -> list[str]`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:149 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:64`
### `duplicates(values: Iterable[str]) -> list[str]`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:165 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:77`
### `read_activity(path: Path) -> list[dict[str, str]]`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:150 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:82`
### `read_badkeys(path: Path) -> set[tuple[str, str]]`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:173 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:89`
### `strip_source_error(value: str) -> str`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:113 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:124 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:100`
### `parse_missing_sources(log_text: str) -> set[str]`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:174 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:107`
### `interesting_log_lines(log_text: str) -> list[str]`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:175 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:128`
### `load_run(root: Path, name: str) -> RunSummary`
> Loads and parses output artifacts, logs, puts, activity records, and badkeys from a run directory.
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:391 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:392 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:146`
### `write_list(path: Path, values: Iterable[str]) -> None`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:397 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:398 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:400 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:401 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:402 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:403 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:179`
### `write_badkey_list(path: Path, values: Iterable[tuple[str, str]]) -> None`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:399 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:184`
### `md_list(items: Iterable[str], limit: int=10) -> list[str]`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:326 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:336 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:346 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:189`
### `artifact_line(path: Path) -> str`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:366 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:367 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:368 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:369 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:370 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:371 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:372 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:199`
### `manifest_uri(metadata: dict[str, object]) -> str`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:271 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:203`
### `build_report(root: Path, run1: RunSummary, run2: RunSummary, analysis_dir: Path) -> str`
> Renders a comprehensive Markdown comparative report contrasting Run 1 and Run 2 results.
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:405 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:213`
### `analyze(root: Path, report_path: Path | None=None) -> tuple[str, list[tuple[str, str]]]`
> Top-level orchestrator comparing two runs and writing report markdown and missing-source TSVs.
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:430 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:386`
### `parse_args() -> argparse.Namespace`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:429 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:420`
### `main() -> int`
> CLI entry point parsing directory arguments and invoking analyze.
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:438 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py:428`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| `--run1-dir PATH`: Directory containing Run 1 outputs and logs. |
| `--run2-dir PATH`: Directory containing Run 2 outputs and logs. |
| `--output-dir PATH`: Target directory for generated comparison reports. |
| `--archive-metadata PATH`: Metadata JSON from manifest archives. |
| `--manifest1 URI`: S3 URI for Run 1 inventory manifest. |
| `--manifest2 URI`: S3 URI for Run 2 inventory manifest. |

## Data Shapes
- Input: `activity.tsv` (columns: timestamp, status, key, size, duration), `puts.txt` (newline-delimited keys), `badkeys.tsv` (issue, escaped_key, key).
- Output: `analysis_report.md` (Markdown diff and stats), `run1_missing_sources.tsv`, `run2_missing_sources.tsv`, `run1_badkeys.tsv`, `run2_badkeys.tsv`.

## Notes
- Matches missing source lines using regex `Missing source (skipped): .*? s3://(.+)$`.
- Identifies transient head-visible vs get-failed discrepancies (`source_get_failed_after_head_success`).

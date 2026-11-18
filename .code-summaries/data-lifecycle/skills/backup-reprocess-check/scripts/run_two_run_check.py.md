# run_two_run_check.py

**Path:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py`
**Module:** `data-lifecycle.skills.backup-reprocess-check.scripts.run_two_run_check`
**Feature Area:** `data-lifecycle`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Orchestrates two consecutive containerized backup pipeline execution runs against S3/Glacier inventory manifests to verify idempotent reprocessing and differential correctness.

## Connections
- **Shared data:** Invokes `analyze_two_run_check.py` to compare generated runs.
- **Shared data:** Builds and executes docker containers packaging `data-lifecycle/src/`.

## Dependencies
None

## Classes
None

## Functions
### `utc_now() -> datetime`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:250 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:254 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:30 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:25`
### `utc_stamp() -> str`
> Returns current ISO-8601 UTC timestamp string.
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:134 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:150 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:154 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:155 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:174 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:188 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:209 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:259 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:272 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:274 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:277 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:29`
### `run_command(cmd: list[str], cwd: Path=REPO_ROOT, log_path: Path | None=None, env: dict[str, str] | None=None) -> subprocess.CompletedProcess`
> Executes shell commands logging stdout/stderr to specified files.
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:108 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:144 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:161 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:164 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:171 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:172 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:207 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:216 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:263 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:91 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:33`
### `parse_manifest_uri(uri: str) -> tuple[str, str, str]`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:125 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:245 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:60`
### `next_manifest_date(manifest_date: str) -> str`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:126 (named-call hint); data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:246 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:75`
### `manifest_uri(bucket: str, prefix: str, manifest_date: str) -> str`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:132 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:80`
### `manifest_key(prefix: str, manifest_date: str) -> str`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:118 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:85`
### `latest_manifest_date(bucket: str, prefix: str, profile: str) -> str`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:130 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:89`
### `head_manifest(bucket: str, prefix: str, manifest_date: str, profile: str) -> subprocess.CompletedProcess`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:137 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:107`
### `wait_for_manifest(args: argparse.Namespace, artifact_root: Path) -> tuple[str, dict[str, object]]`
> Polls AWS S3 until a requested inventory manifest JSON exists.
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:260 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:123`
### `build_image(image_tag: str, artifact_root: Path) -> str`
> Builds docker container image for data-lifecycle backup processing.
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:268 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:159`
### `write_repo_metadata(artifact_root: Path, image_tag: str, image_id: str, manifest_date: str) -> None`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:269 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:170`
### `run_backup_once(args: argparse.Namespace, artifact_root: Path, image_tag: str, run_name: str) -> None`
> Executes a single backup run inside a docker container or host environment.
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:273 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:184`
### `analyze(artifact_root: Path, report_path: Path) -> None`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:276 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:214`
### `parse_args() -> argparse.Namespace`
> unclear — see source
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:238 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:221`
### `main() -> int`
> CLI entry point orchestrating two runs and downstream analysis.
> **Called by:** data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:282 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py:237`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| `--inventory-bucket NAME`: S3 bucket containing daily inventories (default: `braingeneers-backups-inventory`). |
| `--inventory-prefix PREFIX`: S3 key prefix for daily inventory manifests (default: `braingeneers-backups-glacier/daily-inventory/`). |
| `--profile NAME`: AWS CLI profile for inventory access (default: `aws-braingeneers-backups`). |
| `--manifest1 URI` / `--manifest2 URI`: Explicit inventory manifest URIs to test. |
| `--output-dir PATH`: Directory where run logs, reports, and run directories are stored. |
| `--build-image`: Whether to build the backup docker image before executing. |

## Data Shapes
- Input: Daily S3 inventory manifest JSON metadata and target repo code.
- Output: `run1/` and `run2/` directories containing stdout/stderr logs, activity TSVs, metadata JSON, and `analysis_report.md`.

## Notes
- Spawns subprocesses running `docker run` or local commands for Stage 3/4 pipeline execution.
- Polls `wait_for_manifest` until tomorrow's inventory manifest appears if comparing against the latest.

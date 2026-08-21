---
name: backup-reprocess-check
description: Run and analyze Braingeneers data-lifecycle two-run backup validation checks. Use when Codex needs to wait for an AWS Glacier inventory manifest, run the backup pipeline twice, compare artifacts/logs, detect steady-state reprocessing problems, investigate repeated missing-source or badkey patterns, and write a persisted operational report.
---

# Backup Reprocess Check

## Overview

Use this skill to validate that the data-lifecycle backup pipeline reaches steady state after one run. The core check is: wait for a fresh AWS Glacier inventory, run the backup twice from the same pinned image, compare the artifacts, and report any keys that would be repeatedly processed or repeatedly fail in nightly operation.

Do not treat "zero duplicate uploads" as sufficient. Repeated `missing_source`, repeated `NoSuchKey`, or repeated `badkeys.tsv` entries can still indicate real steady-state problems, including key-shape bugs such as leading slash or doubled slash handling.

## Quick Start

From the `mission_control/data-lifecycle` component directory:

```bash
python skills/backup-reprocess-check/scripts/run_two_run_check.py \
  --after-manifest-uri s3://braingeneers-backups-inventory/braingeneers-backups-glacier/daily-inventory/YYYY-MM-DDT01-00Z/manifest.json
```

If there is already a completed two-run artifact directory, analyze it without rerunning backup:

```bash
python skills/backup-reprocess-check/scripts/analyze_two_run_check.py \
  plans/manifest-reprocess-check-YYYY-MM-DD
```

## Workflow

1. Establish the manifest target.
   - If the user gives a manifest URI, wait for the next daily manifest after it.
   - If no prior manifest is supplied, use the latest currently available AWS inventory manifest.
   - Poll with long intervals after initial discovery; 30-60 minutes is preferred for long waits.

2. Build a pinned Docker image from the current checkout.
   - Record the image tag, image ID, commit SHA, and dirty/clean worktree state.
   - Use the same image for both runs.

3. Run the backup twice.
   - Mount AWS and rclone config into the container.
   - Mount each run's scratch directory to container `/tmp`.
   - Preserve `run.log`, `start.utc`, `end.utc`, `exit_code.txt`, and all `/tmp` artifacts.
   - Do not discard failed attempts; move them aside with a clear name and continue only when the failure is operationally transient.

4. Analyze both runs.
   - Compare `puts.txt` counts, unique keys, duplicates, and set differences.
   - Compare `activity.log` by `BucketKey`, `UploadedBucketKey`, and `Result`.
   - Parse logs for `Missing source (skipped)` and `NoSuchKey` source failures.
   - Compare `badkeys.tsv` issue/key pairs.
   - Write machine-readable analysis files plus a Markdown report in `plans/`.

5. Investigate suspicious repeated failures.
   - Any repeated missing-source set across both runs is suspicious unless manually explained.
   - For repeated missing-source keys, inspect whether source inventory saw a different raw key shape, especially leading `/`, doubled `//`, rclone dot substitutions, embedded `s3:/`, or carriage-return artifacts.
   - Check whether source `HeadObject` succeeds while source `GetObject` fails; report these via `badkeys.tsv` if the pipeline supports it.

## Issue Heuristics

Report an issue if any of these occur:

- A key is uploaded in both runs.
- Run 2 uploads keys that run 1 already uploaded successfully.
- A key remains in both `puts.txt` files and does not become `already_present_skipped`.
- The exact missing-source set repeats across both runs.
- `badkeys.tsv` has repeated non-accepted issue/key pairs.
- `source_get_failed_after_head_success` appears.
- Logs show repeated malformed path, source `NoSuchKey`, destination precheck errors, or artifact upload failures.

When repeated missing-source cases appear, phrase the finding as an unresolved steady-state risk. Do not call it transient solely because source files can disappear between inventory and upload; identical repeated counts or sets across runs are evidence that the condition may be persistent.

## Reports

Persist reports under the component directory:

- `plans/manifest-reprocess-check-YYYY-MM-DD/`
- `plans/manifest-reprocess-check-YYYY-MM-DD.md`

The report must include:

- Manifest URI, online time, and manifest metadata.
- Docker image tag/ID and commit SHA.
- Per-run counts for PUTs, uploads, already-present skips, missing sources, failures, and badkeys.
- Cross-run comparison and issue findings.
- Root-cause notes for repeated missing-source or badkey patterns.
- Paths to raw artifacts.

Keep the final user-facing summary concise, but make the persisted report complete enough for follow-up debugging.

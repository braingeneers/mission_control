---
name: summarize-codebase
description: Build and refresh a navigable source code map with reviewed per-file summaries, feature areas, and import connections. Use for "summarize codebase", "refresh code map", or "update code summaries" in Python/JavaScript repositories.
---

# Summarize codebase

Create `.code-summaries/` from static source facts and source-reviewed annotations.
Requires Python 3.10+, Git, and bash for the refresh wrapper; no third-party packages.
Never import or execute project code to inspect it.

## Quick path

Run from the target repository (SKILL is the absolute installed skill directory):

```bash
python3 "$SKILL/scripts/summaries.py" check
WORK=/tmp/my-code-map bash "$SKILL/scripts/refresh.sh"
# Follow WORK/PROMPT.md for the printed batches, then resume:
WORK=/tmp/my-code-map bash "$SKILL/scripts/refresh.sh"
```

A pending annotation phase exits 1 without building. Use a new WORK for a new selection.
The default annotation step asks the calling agent to spawn children/subagents;
each reads PROMPT.md and assigned batches and writes `out/<batch>.json`.
Use only available, authorized delegation. If unavailable, annotate the batches directly.
See [annotators](references/annotators.md) for agent and CLI options.

## First-run setup

Config is optional. Default feature areas follow top-level directories, adding a
second level when the top level is a Python package containing multiple subpackages.
Obvious figures/plots/scratch directories receive brief reviews; other files receive full reviews.
For custom areas, exclusions, or import rewrites, create `.code-summaries.json`
using the [configuration schema](references/configuration.md).
The helper finds the repository via Git from cwd; pass `--root PATH` explicitly otherwise.
Installation location is independent of the repository being summarized.

## Incremental refresh

No selection arguments means stale/missing source summaries and removed files.
Use `--all`, `--since REF`, or quoted paths/globs for a chosen scope.
Pass selection flags to refresh.sh on the first run; the same WORK retains them.
An explicit subset may leave other files stale; inspect `WORK/check.txt`.
Public symbol removal also selects known consumers for review.

## Quality rules

Read [annotation format](references/annotation-format.md) before annotating.
Read every assigned file completely. Describe concrete inputs/outputs, shapes,
CLI/config, state, side effects, and verified connections. Never invent callers.
Use `unclear — see source` when evidence is insufficient.
Preserve manifest source hashes; source changes during review require a new plan.
Full-tier annotations need overview plus config/data_shapes/notes/connections lists;
Python API facts come from AST. Supply symbol purposes when docstrings are insufficient.
Validate every batch before building. Failed, timed-out, or quota-skipped batches
remain pending; rerun the same WORK to retry them. Do not claim completion until check passes.

## Artifacts and freshness

The map contains `_INDEX.md`, `_FEATURES.md`, `_GRAPH.md`, `_META.json`,
and mirrored `<source-path>.md` summaries. Simple package markers appear in the index.
Optional hand-maintained `_STATUS.json` survives rebuilds (file/area status and replacements).
Hashes normalize CRLF to LF; commit IDs provide context, not freshness authority.
Run `python3 "$SKILL/scripts/summaries.py" check --json` before relying on the map.
Exit 0 means current; exit 1 means stale/missing/deleted source or missing indexes.
Tests are excluded unless `--include-tests` is passed consistently.

## Using the map

Check freshness first, then read `_INDEX.md` → `_FEATURES.md` → per-file summary.
Use `_GRAPH.md` for conservative import hints; confirm runtime behavior in source.
Brief summaries prioritize overview and connections; source holds implementation detail.

# Batch review format

Read each assigned source file fully (chunk long files). Return a JSON object keyed by
repo-relative POSIX source path. `source_sha256` must be the hash of the bytes actually
reviewed (the batch manifest supplies it; `shasum -a 256 FILE` recomputes it). The helper
rejects annotations whose hash no longer matches the file.

Feature areas are derived from the path by the helper; do not supply one.

## Full tier (core modules, analysis pipelines, training code)

```json
{
  "src/jobs/example.py": {
    "source_sha256": "<sha256>",
    "overview": "What this file does and its role. When and how it is run (CLI, NRP job, imported).",
    "config": ["`--bin_ms` (default 20): spike-count bin width in ms.", "Env `DATA_ROOT`: input root."],
    "data_shapes": ["Input: spike rows (time_s, unit_id); output: units × time_bins float32 array saved as .npz key `counts`."],
    "notes": ["Hardcoded path `/Users/.../data` (line 12).", "Mutates module-level CACHE dict."],
    "connections": ["Reads checkpoints written by `train.py`; writes metrics CSV consumed by figures/general_metrics/."],
    "purposes": {
      "ClassName": "Purpose and system role.",
      "ClassName.method": "What and why, not line-by-line how.",
      "function_name": "Purpose; side effects and actual callers when verified."
    }
  }
}
```

All four lists are required; empty means `None`, not unreviewed. For JavaScript, HTML and
CSS add `symbols`: a list of `{name, signature, purpose, line}` (one-based lines). Python
signatures, classes, imports and line numbers come from the AST — do not restate them.
Supply purposes for public functions/classes and key nontrivial methods; documented ones
may rely on their docstrings.

## Brief tier (figure, plotting, derive_data and scratch scripts)

```json
{
  "figures/drift/panel_a.py": {
    "source_sha256": "<sha256>",
    "overview": "Plots panel A of the busy-drift figure: per-session prediction error vs. days in vitro from derived CSV X; saves PNG/SVG to Y.",
    "connections": ["Reads `derive_data/drift_metrics.csv`."]
  }
}
```

Only `overview` is required (1–2 sentences: what it plots/derives, from which inputs, to which
outputs). `connections`, `config`, `notes` and `purposes` are optional; include inputs/outputs
paths when visible because they are the most useful facts for navigation.

## Quality rules

- Specific > generic. "Streams parquet shards windowed by session" beats "loads data".
- Always record shapes/schemas, CLI args, config keys, input/output file paths.
- Flag global state, env reads, hardcoded paths/IDs, NRP/S3 locations.
- Never invent. If unsure write `unclear — see source`.
- Do not import or run source to inspect it.

## Generated summary layout

Each `<source>.md` has: `**Path**`, `**Module**`, `**Feature Area**`, `**Tier**`, `**Entry point**`,
then `## Overview`, `## Connections` (Uses / Library / Used by / Shared data), `## Dependencies`,
`## Classes`, `## Functions`, `## Config / CLI`, `## Data Shapes`, `## Notes`. Connections precede
long API details so short bounded reads are useful.

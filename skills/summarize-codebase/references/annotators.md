# Annotator choices

Nothing requires T3 or a specific vendor. All annotators follow WORK/PROMPT.md,
read source without executing it, and write WORK/out/<batch>.json.

## Any coding agent

Run refresh.sh, then give each available subagent/child PROMPT.md plus batch names.
Assign around five batches per child (fewer for large files); wait for completion,
fix failed outputs, and resume with the same WORK. Direct annotation also works.

## Claude Code

Use the `Agent` tool with an available cheap model. Task text:
`Follow <WORK>/PROMPT.md for batches: full_000 brief_001`.
Wait for children to finish before resuming refresh.sh.

## T3 / Antigravity route (example)

Use `delegate_task` with provider `antigravity`, model `gemini-3.8-flash`, async,
one child per approximately five batches. Task text:
`Follow <WORK>/PROMPT.md for batches: ...`.
Use the tool's supported settings and completion mechanism; if that provider/model
is unavailable, choose another authorized annotator explicitly.

## Generic CLI

```bash
WORK=/tmp/my-map PARALLEL=4 ANNOTATOR_TIMEOUT=1200 \
  ANNOTATOR_CMD='my-annotation-cli --batch "$1" --prompt-stdin --output "$WORK/out/$(basename "$1")"' \
  bash "$SKILL/scripts/refresh.sh"
```

`my-annotation-cli` is a placeholder for your own CLI or wrapper. ANNOTATOR_CMD is
trusted bash code, invoked per batch with its absolute path as `$1`, WORK exported,
and PROMPT.md on stdin. It must write the JSON file itself. PARALLEL defaults to 6;
ANNOTATOR_TIMEOUT is seconds per command (default 1200). Logs go to WORK/logs/.
Exit 10 indicates quota exhaustion: queued work skips, running commands may finish.
Other errors/timeouts leave invalid batches pending. No automatic retry loop;
rerun explicitly after fixing the cause. Valid outputs are skipped on resume.
All batches must validate before a build. A source edit invalidates its annotation;
start a fresh WORK to replan rather than copying old hashes into new annotations.

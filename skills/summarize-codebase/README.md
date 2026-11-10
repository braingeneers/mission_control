# Portable code map skill

Produces `.code-summaries/`: navigable file summaries, feature flows, static import
connections, API facts, and hash-based freshness metadata for Python/JS/HTML/CSS.
Python 3.10+, Git, bash; standard library only. Source is read, never executed.

Three-command quickstart from a target repository (set SKILL to this folder):

```bash
python3 "$SKILL/scripts/summaries.py" plan --json
WORK=/tmp/my-map bash "$SKILL/scripts/refresh.sh"
WORK=/tmp/my-map bash "$SKILL/scripts/refresh.sh"
```

Between commands two and three, have your coding agent follow the generated
PROMPT.md for the printed batch names and write the requested JSON outputs.
Use a new WORK for each new refresh. Reusing WORK resumes the original selection.
Pending batches exit 1; a complete refresh builds and checks freshness.

Run `bash install.sh` in this directory to link the skill into both user skill
locations. It refuses to replace a real directory. Repo-path skill installers may
instead install `skills/summarize-codebase` directly from this repository.

Optional repository-root `.code-summaries.json` customizes areas, brief directories,
exclusions, library notes and import rewrites: see [configuration](references/configuration.md).
No config is needed. Default area names follow directories.

Default annotation uses your agent's children/subagents (or direct review).
CLI users can set ANNOTATOR_CMD, PARALLEL and ANNOTATOR_TIMEOUT;
see [annotators](references/annotators.md) for examples and quota handling.
See [SKILL.md](SKILL.md) for incremental selection, quality rules, artifacts and map usage.

# Registering a task

`nrp-watchdog task add TASK.json` validates the file, copies it into the watchdog's state, and the next pass starts
it. A task is refused (nothing is registered) with a list of every problem found.

## Fields

Required: `name` (lowercase letters, digits and `-`, at most 40), `goal`, `approved`, `stages`.

- `approved`: the user's approval in their own words with the date. Not a summary of your own judgment.
- `notes` (at most 4 KB): what a fresh agent needs: how the Job works, what a good result looks like, where outputs go.
- `code`: `{repo, subdir?, commit?}`. Registers a clone the fix agents may edit on a branch `watchdog/<task>`.
- `namespace` (default `braingeneers`), `mode` (`auto`: agents repair and resubmit, `watch`: any failure goes to the
  person), `max_retries` (0-10, default 4), `label`.
- `origin`: `{title, link, assistant?, collaborator?}` of the chat or ticket the work came from (attribution only).
  Missing origin is a warning (`NRP_WATCHDOG_REQUIRE_ORIGIN=1` makes it a refusal).
- Continuation, at least one of (a task with none is a warning, or a refusal with
  `NRP_WATCHDOG_REQUIRE_CONTINUATION=1`):
  - `on_done`: `{"plan": "path/PLAN.md#plan-id", "from_step": "N"}`. The plan section needs a run header with the
    approved range and stops. A continue agent checks the step's "done when" and may register the next approved step.
  - `followup`: text (at most 2 KB) saying what a one-shot read-only agent should report when the task is done.
  - `digest_only`: a reason (8-300 characters) nothing else is pending.
- `handoff`: path to the markdown handoff the registering agent writes from `scripts/templates/handoff.md` (absolute,
  `~`, or relative to the task file's folder); `task add` validates it and copies it into the task's folder, where the
  fix and continue agents read it. Missing, empty or thin (a `## Registrar` of under 200 characters) is a warning, or a
  refusal with `NRP_WATCHDOG_REQUIRE_HANDOFF=1`. It is usually written after the task is registered, so
  `nrp-watchdog task handoff NAME FILE` attaches it later. Format and ownership: [handoff](handoff.md).

Util flags: a util fix agent may answer `UTIL_OK: evidence` for a healthy Job flagged only by the lab floor; the script accepts it
a limited number of times per task (utilization.md, "Util waiver"). Task-level settings `util_waiver_max` and
`util_waiver_hours` are in `config.json`, not in the task file.

Per stage: `job` (the Job's DNS name, must equal `metadata.name` in the manifest), `manifest` (path to the Job YAML),
`done_s3` (full `s3://bucket/key` URIs of single objects that exist only when the stage succeeded; checked exactly,
never as a prefix), and optionally `id`, `after` (stage ids), `after_s3` (URIs that must all exist before submitting, a
gate on another task's success marker), `state` (`pending`, `running` to adopt a Job already submitted, `done`),
`gpu_ok_until` (`YYYY-MM-DD`, required when the manifest requests a GPU and no approved plan covers it), and `resumable` (`true` only when
re-running the stage skips items whose outputs already exist; then a deadline timeout is resubmitted once with 2x the deadline without
any agent. Never set it for a stage that restarts from scratch).

## Manifest rules checked at registration

`activeDeadlineSeconds` set, `backoffLimit: 0`, `ttlSecondsAfterFinished` of at least 3600, no long sleep, name matches.
Derive the deadline from measured runtime with margin; the queue counts toward it.

## Example

```json
{
  "name": "demo-extract",
  "goal": "Extract features for dataset X with the approved image",
  "approved": "Alice, 2026-11-09 in chat: go ahead with the extract run",
  "notes": "One Job per dataset. A good result is features.npz plus DONE. Resources were sized from the 2026-11-08 pilot.",
  "origin": {"title": "Dataset X features", "link": "https://example.org/the-chat"},
  "digest_only": "Terminal step; the results are read by hand",
  "stages": [
    {"id": "extract", "job": "demo-extract-a", "manifest": "manifests/demo-extract-a.yaml",
     "done_s3": ["s3://braingeneersdev/alice/demo/extract/DONE"]}
  ]
}
```

## Commands

`nrp-watchdog task list`, `task show NAME`, `task handoff NAME FILE`, `task watch NAME`, `task resume NAME` (continue after a person or the coordinator chat decided, from
`NEEDS_OWNER` or `WITH_COORDINATOR`; `--gpu-ok-until DATE` after extending a GPU approval), `task needs-owner NAME --reason TEXT` (run by the
coordinator chat only when the owner is truly needed: sets `NEEDS_OWNER`, sends the one DM), `task cancel NAME`, `status`, `digest --hours N`,
`origin task NAME --title .. --link ..` (add or fix attribution later). Agents use `nrp-task`, a wrapper that validates
every argument; it is their only shell tool for task work.

# Registering a task

`nrp-watchdog task add TASK.json` validates the file, copies it into the watchdog's state, and the next pass starts
it. A task is refused (nothing is registered) with a list of every problem found.

## Fields

Required: `name` (lowercase letters, digits and `-`, at most 40), `goal`, `approved`, `stages`.

- `approved`: the user's approval in their own words with the date. Not a summary of your own judgment.
- `notes` (at most 4 KB): what a fresh agent needs: how the Job works, what a good result looks like, where outputs go.
- `code`: `{repo, subdir?, commit?, pkg_dir?, extra_pkg_dirs?}`. Registers a clone the fix agents may edit on a branch `watchdog/<task>`.
  For pv3 Jobs that run shipped code, `nrp-task reship` packs **every code dir the task declares**: the `predictor_v3` package
  (`pkg_dir`, else `subdir` when it is `predictor_v3`, else `<clone>/predictor_v3`) plus each `extra_pkg_dirs` entry, packed beside it
  exactly as `--ship-code` with `PV3_CODE_EXTRA_PACKAGES` did at submission (`finetune/...`, `bwb/...` next to `predictor_v3/...`).
  A relative extra dir is inside `repo` (cloned with the task, so agents can fix it); an absolute or `~` one is another checkout, read in
  place at reship (not editable by agents). At most 8, each a distinct package name, no `..`. Declare them for a task registered without
  them with `nrp-watchdog task code NAME --pkg-dir DIR --extra-pkg-dir finetune --extra-pkg-dir bwb`.
- `namespace` (default `braingeneers`), `mode` (`auto`: agents repair and resubmit, `watch`: any failure goes to the
  person), `max_retries` (0-10, default 4), `label`.
- `origin` (**required** for `task add`): `{title, link, assistant?, collaborator?}` of the chat or ticket the work came from. Without it
  the task is refused (v3; an alert would name no chat and wake nobody). Pass it in the file or with `--origin-title/--origin-link`.
  A continuation registered by a continue agent inherits its parent's origin (only a warning if the parent had none).
- Continuation, at least one of (a task with none is a warning, or a refusal with
  `NRP_WATCHDOG_REQUIRE_CONTINUATION=1`):
  - `on_done`: `{"plan": "path/PLAN.md#plan-id", "from_step": "N"}`. The plan section needs a run header with the
    approved range and stops. A continue agent checks the step's "done when" and may register the next approved step.
    **Several tasks may share one step** (per-cell fan-outs): register each with the same `from_step`. The step is done when all of
    its tasks are (cancelled ones do not count; one that needs the owner holds it), and its continuation runs once, when the last
    one finishes; the others are closed as `COVERED`. A continue agent may register several tasks for the next step in one run.
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
`gpu_ok_until` (`YYYY-MM-DD`, required when the manifest requests a GPU and no approved plan covers it).

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

`nrp-watchdog task list`, `task show NAME`, `task code NAME` (declare reship's code dirs), `task handoff NAME FILE`, `task watch NAME`, `task resume NAME` (continue after a person decided,
`--gpu-ok-until DATE` after extending a GPU approval), `task cancel NAME`, `status`, `digest --hours N`,
`origin task NAME --title .. --link ..` (add or fix attribution later). Agents use `nrp-task`, a wrapper that validates
every argument; it is their only shell tool for task work.

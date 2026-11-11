# Operations and escalation

## One pass (every 5 minutes, no model unless a decision is needed)

- Submit stages whose `after` and `after_s3` conditions hold, while fewer than `max_concurrent_jobs` of the user's Jobs are
  unfinished (400 in the shared policy; a local override may lower it; utilization.md).
- Mark a stage done only when every `done_s3` object exists (exact `head-object`); an Indexed Job counts as succeeded
  only when all its completions are done.
- Save the last log lines and `kubectl describe` of each Job, then delete finished Jobs by name (only its own).
- Check utilization (see utilization.md).
- When a task finishes: record it, start the continuation (`on_done`, `followup`) if declared, otherwise list it in the
  digest as `no-continuation`. A task with no (or a thin) handoff is also listed, as `no-handoff` (see handoff.md).

## Tier 0 rules (no model, before any agent)

Applied to a failed stage of an `auto` task before a fix agent is started. Each resubmit goes through the same checks as an agent's
(retry cap, class budget, GPU approval date, manifest rules); a rule that cannot decide, or whose resubmit is refused, leaves the
manifest untouched and hands the failure to the ladder below. Tier 0 resubmits are recorded with `by tier0` in the task's attempts and show "(Tier 0 rule)" in `task show`.

- **OOM**: the OOMKilled container's memory limit becomes `max(observed peak, limit it hit) x 1.3`, rounded up (peak = max working
  set since submit from NRP's Prometheus; no number, no change). The request keeps the limit within the shared
  `limit_to_request_tolerance` (20%). Once per stage; above `tier0_mem_cap_gi` (config.json, default 128) or a second OOM goes to the agents.
- **Known node fault** (pod status/conditions or the log tail of a single-pod Job show an Xid/uncorrectable ECC, no CUDA device,
  nvidia-container-cli, sandbox or volume-mount failure, NodeLost, ContainerStatusUnknown): the node is added to the manifest's
  `kubernetes.io/hostname NotIn` anti-affinity and the stage resubmitted. At most 3 nodes per stage; the same failure signature again
  goes to the agents.
- **Long Pending** (no container started 30 minutes after submit): the scheduler's PodScheduled message is recorded once in the
  task events and the digest (`pending`), again when it changes or after 6 hours, with the node restrictions of our own manifest
  (for example a GPU allow-list) when the message blames affinity/selector. Read-only: nothing is resubmitted or extended.
- **Finished Jobs** are deleted only after every `done_s3` marker is verified by an exact `head-object`; a succeeded Job whose marker is
  missing is kept (class `outputs`) for diagnosis.

## Escalation ladder

A failure is handled by the cheapest thing that can fix it; a person hears about it only after that has failed, with one
Slack DM.

1. **No model.** The script classifies the failure (resources, util, code, queue, infra, outputs, slow) and handles
   routine events.
2. **Cheap triage.** For a registered Job with a resume file, one read-only agent looks first and returns a result or
   `ESCALATE` with evidence.
3. **Repair.** Up to two repair attempts for a job follow-up. A task failure starts one fresh fix agent directly, with a
   retry budget of 4 total and 3 per failure class. Code fixes are committed on `watchdog/<task>`. The agent's prompt
   carries the task's handoff, and its `HANDOFF_ENTRY:` block is appended to the handoff's Fix log (handoff.md).
   A single bad item is skipped and logged; a pattern (more than 5% of items, by default; the `skip_limit_fraction`
   setting, install.md) goes to a person.
   A util fix agent that finds the Job healthy may answer `UTIL_OK: evidence` instead of a stop (a **util waiver**,
   utilization.md): the script accepts it only for a flag from the lab floor alone, on a Job that still runs, at most 3
   times per task; otherwise it is the stop below.
4. **A person.** The task becomes `NEEDS_OWNER` (tasks stored under the earlier name `NEEDS_HUNTER` are read as this) and the owner gets one DM when a
   run is slow, the same failure repeats, the retry budget is used up, an agent stops, or it has been blocked 6 hours.
   `nrp-watchdog task resume NAME` continues after they decide.

The ladder for job follow-ups is configurable (agents.md). An accepted util waiver sends no DM, uses no retry and adds a
`util-waived` line to the digest. Retries are silent. When no agent can run (every runner is out of
usage), the work waits without using a retry and the owner gets one DM saying so.

## The digest

Everything routine is silent. `nrp-watchdog digest --hours N` lists events, what needs a person, plans waiting, tasks with
no continuation, and a warning when the notification token is near expiry. `nrp-watchdog status` shows scheduler heartbeat
age (exit 3 when stale while work is active), tasks that need the owner, and runners out of usage.

## Completion continuation (`on_done`)

When a task with `on_done` finishes, one continue agent reads the outputs and the plan, checks the step's "done when",
and registers the next approved step as a new task (which carries its own `on_done`). It cannot pass the plan's approved
range, a named stop, or the files the plan lets it touch. Night code goes on a branch for review, never to main.

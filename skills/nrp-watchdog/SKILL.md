---
name: nrp-watchdog
description: Follow approved NRP Nautilus work unattended instead of polling it. Register staged Jobs as a task with exact S3 success markers; a background pass submits stages, saves logs, checks utilization against the shared NRP Cluster numbers, repairs failures with cheap agents, continues the approved plan when work finishes, and contacts the owner once only if needed. Use after the user approves NRP compute, for "keep an eye on this", overnight pipelines and utilization enforcement. Not for deciding what to run or for ad-hoc one-off Jobs.
---

# NRP Watchdog

The `nrp-cluster` skill covers how to build and submit NRP Jobs. This skill covers what happens **after the user
approves the work**: nobody polls. The session registers a **task**, returns, and a scheduled pass on the user's
machine does the waiting. Agents start only when a decision is needed, cheapest first, and the person hears about it
only after that has failed.

Installing this skill authorizes nothing by itself. It does not install the scheduler, change settings, submit Jobs or
send messages. Do those only as the user asks, following the procedures below.

## When to use it

- The user has approved NRP work (a Job or a staged pipeline) and it will run longer than a short wait.
- Several stages depend on each other, or a stage should start only when another task's output exists.
- Work must continue overnight, and a finished stage should lead to the next approved step or to analysis.
- The user wants resources and utilization held to the NRP Cluster skill's numbers without watching.

For a short wait inside one session, use one background wait and do not register anything. Never poll in the foreground
and never start an agent whose only job is to wait.

## Procedure

1. **Check the watchdog exists and is alive.** Run `nrp-watchdog status`. Exit 3 or "has never run" means the
   scheduler is not running; tell the user, do not register work that nothing will advance. If it is not installed,
   read [install](references/install.md) and ask before installing: it creates a background job.
2. **Follow `nrp-cluster` first** (manifest rules, sizing, GPU approval, deadlines). The watchdog refuses a manifest
   that breaks the Job rules but does not replace judging the resources.
3. **Write `TASK.json`** from [tasks](references/tasks.md): the user's approval in their own words with the date, one
   stage per Job, and for each stage the exact S3 object that exists only when the stage succeeded (`done_s3`).
   Put what a fresh agent needs in `notes` (4 KB).
4. **Declare what happens when it finishes.** One of: `on_done` (a plan step, so a continue agent moves the approved
   plan on), `followup` (a one-shot read-only report), or `digest_only` with a reason nothing else is pending. A task
   with none of these only lands in the digest and nothing acts on it; do not hand back unattended work that still has
   requested analysis, review or delivery remaining.
5. **Record the origin**: the chat or ticket the work came from (`origin.title`, `origin.link`). It is attribution, not
   a callback.
6. **Register and verify**: `nrp-watchdog task add TASK.json`, then `nrp-watchdog task show NAME` and
   `nrp-watchdog status`. Report what is registered and what will and will not resume on its own.
7. **Write the handoff before you return.** Once the monitor is started, copy `scripts/templates/handoff.md` and fill
   its `## Registrar` section for the agents that will take over later: what is being done and why, what each stage
   produces, what to check when it finishes and when it fails, decisions already made, what NOT to do, where the code
   and outputs are (worked example in [handoff](references/handoff.md)). Attach it with
   `nrp-watchdog task handoff NAME FILE` (or name it in the task's `handoff` field before `task add`), then confirm
   `nrp-watchdog task show NAME` prints `handoff: accepted`. A task without one only gets a warning, and its fix and
   continue agents start with nothing but the task fields.
8. **Return.** Do not wait. Later: `nrp-watchdog digest --hours 6` shows what happened and what needs a person.

If a Job already belongs to a chain, feeder or earlier registration, inspect that first and do not register a second
submitter.

## What the watchdog does on its own

- Submits stages whose conditions hold (`after`, `after_s3`), checks success with an exact S3 `head-object` per key
  (never a prefix listing), saves logs, deletes only its own finished Jobs.
- Checks utilization with `nrp-util-check`. The shared numbers (GPU floor, job cap) are the `nrp-cluster` skill's own, in its
  `references/utilization-policy.json`; a person may add stricter local rules in an optional override; see
  [utilization](references/utilization.md).
- Handles a failure at the cheapest level that can fix it (script rules, Haiku triage, a Sonnet fixer, then the task's own coordinator
  chat; the person hears only if that chat says so): see
  [operations](references/operations.md). Which agent runs, in what order, and what happens when one is out of usage is
  configured in `agents.json`: see [agents](references/agents.md). A healthy Job that only the lab floor flags can be waived
  (`UTIL_OK`, limited per task, decided by the script): see [utilization](references/utilization.md).
- When a task finishes with `on_done`, runs one continue agent that checks the plan step's "done when" and registers the
  next approved step. It never goes past the approved range or a named stop.
- Gives fix and continue agents the task's handoff and appends what each one tried or checked to the handoff's own
  log sections, from the `HANDOFF_ENTRY:` block that ends its answer. The agents never edit the file and cannot change
  the Registrar: see [handoff](references/handoff.md).

## Boundaries

- Only the user's own Jobs and pods. Never another owner's work, the namespace, or admission settings.
- Approval is recorded, not assumed: `task add` refuses a plan step that is past the approved range or marked as a stop.
- Agents the watchdog starts have the same permissions as the user's own agents, run unattended, and are limited by
  allowlisted commands plus a time limit (Claude agents also have turn and dollar limits). Codex agents can read any file
  the user can.
- The one notification is a Slack DM to the configured owner through the lab notification service. Never print the
  service token. Never message a channel or another person on the watchdog's behalf.
- Local session work in a plan (anything marked as not for NRP) never runs automatically.

## References

- [Registering a task](references/tasks.md): fields, example, commands.
- [The handoff](references/handoff.md): format, who owns which section, what a good Registrar contains.
- [Operations and escalation](references/operations.md): what one pass does, the ladder, the digest.
- [Agents and fallback](references/agents.md): `agents.json`, runners, usage limits.
- [Utilization](references/utilization.md): the checker, shared numbers, optional local rules, strikes.
- [Install](references/install.md): installing, the owner settings, the scheduler.
- [Known issues](references/known-issues.md): what is broken or unproven.
- [v3 plan](references/v3-plan.md): agreed next design (rename to nrp-monitor, tiered Haiku/Sonnet/manager escalation, one coordinator thread); not built yet.

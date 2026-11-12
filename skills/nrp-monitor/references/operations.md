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

- **OOM**: prefer the saved `NRP_MEMORY_PEAK` cgroup reading for the failed container and attempt;
  otherwise use the maximum sampled working set since submit from NRP's Prometheus. Memory becomes
  `max(peak, OOM limit) x 1.3`, rounded up. Without a true peak, a sample below half the OOM limit
  is unreliable: use twice that limit instead. With neither reading, leave sizing to the agents. The request keeps the limit within the shared
  `limit_to_request_tolerance` (20%). Once per stage; above `tier0_mem_cap_gi` (config.json, default 128) or a second OOM goes to the agents.
- **Known node fault** (pod status/conditions or the log tail of a single-pod Job show an Xid/uncorrectable ECC, no CUDA device,
  nvidia-container-cli, sandbox or volume-mount failure, NodeLost, ContainerStatusUnknown): the node is recorded in a shared fault list and the stage resubmitted with
  `kubernetes.io/hostname NotIn` node affinity. Every task submission uses the shared list;
  each node expires 24 hours after the last observed fault, with new faults refreshing expiry.
  Status and digest show active nodes and expiry. A vanished pod with empty/unavailable diagnostics
  uses historical Thanos `kube_pod_info` placement since submit; ambiguous multi-node results
  are left to the agents. The submitted copy receives automatic exclusions so expiry allows
  the node again without editing manifests. At most 3 nodes per stage; the same failure signature again
  goes to the agents.
- **Long Pending** (no container started 30 minutes after submit): the scheduler's PodScheduled message is recorded once in the
  task events and the digest (`pending`), again when it changes or after 6 hours, with the node restrictions of our own manifest
  (for example a GPU allow-list) when the message blames affinity/selector. Read-only: nothing is resubmitted or extended.
- **Finished Jobs** are deleted only after every `done_s3` marker is verified by an exact `head-object`; a succeeded Job whose marker is
  missing is kept (class `outputs`) for diagnosis.

## Escalation ladder

A failure is handled by the cheapest thing that can fix it; a person hears about it only after that has failed, with one
Slack DM. The triage judge reviews, the fixer changes work, a fresh deputy tries bounded recovery, and the chat that owns the work helps if the deputy cannot. Only that chat decides
the owner is needed.

### Tasks (v3)

0. **Tier 0, script rules, no model.** Task-scoped coordinator decisions are checked first, then classification, success markers, utilization, and the timeout rules below.
1. **Tier 1, triage judge** (agent tier `triage`, read-only `nrp-task show|logs|describe|util|s3`). Runs once per failure when a
   benign answer is possible: the Job is still running, pending or finished, or the class is `unknown`/`slow`. A plain terminal failure
   the rules already classified (OOM, traceback, image pull) skips straight to Tier 2. Running utilization flags instead use a separate observation event and always start with the judge; they never fail the stage. Menu: `CLOSE: why`, `ESCALATE: evidence` (anything else counts as
   ESCALATE). CLOSE closes the event: the failure is cleared, the stage goes back to running (or done when its
   outputs exist), the task's events and the digest (`triage-closed`) record it, no retry is used and nobody is notified. The script
   refuses to close it when the Job is dead and the outputs are missing; the event then goes on to Tier 2.
2. **Tier 2, fixer** (agent tier `task`, `templates/task_agent.md`; it sees Tier 1's text). Fixes and resubmits within the retry
   budget. It reports STOPPED when it is not confident, needs a scientific or design choice, or its waiver is refused. A failure that
   repeats after a fix of its own, or a used-up retry budget, skips triage/fixer and goes to the deputy before Tier 3.
- **Deputy, before Tier 3** (agent tier `deputy`, Claude Sonnet by default). One fresh run per task/failure fingerprint and retry generation. It sees goal, approval, the copied plan section when present, handoff, decisions, attempts and saved log paths. It may record/apply task decisions, edit unfinished manifests using measured resources or routine environment repairs, make only the code fixes allowed to the fixer, and resubmit within existing class budgets. `nrp-task retry-cap N` may raise the task cap only up to `max(4, ceil(stages/4))`. It cannot change scientific thresholds, checks, selection or method, act on another task, cancel the task or contact the owner. `RESOLVED` is accepted only when task state proves recovery (or a decision passes script checks); `ESCALATE` supplies a coordinator brief of at most 120 words. Errors, timeouts and unavailable runners escalate. Set `"deputy_enabled": false` in owner `config.json` to restore the earlier path.
3. **Tier 3, the task's coordinator chat.** The task becomes `WITH_COORDINATOR` (not `NEEDS_OWNER`) and the monitor sends an
   `escalation` event through the task's wake route (session resume, T3 CLI or configured webhook, also used for completion wakes) whose
   `summary` leads with the deputy brief when present, then names the fingerprint, task, event and pointers (`task show`, saved logs, the handoff's Fix log). The chat then runs one of:
   `nrp-monitor task resume NAME --note TEXT` (hand back: the failed stage is resubmitted, budgets restart), `task cancel NAME`, or,
   only when the owner is truly needed, `task needs-owner NAME --reason TEXT` (sets `NEEDS_OWNER` and sends the one DM).
   Nothing is lost silently: with no wake target configured for the task, a wake that fails delivery 6 passes in a row (about 30 minutes),
   or a delivered wake nobody answers for 24 hours, falls back to `NEEDS_OWNER` with that reason. Watch-only tasks, GPU approval
   expiry and a 6-hour utilization block still go straight to the owner: only a person can decide those.

Tier backends are the `tiers` entries `triage` (Tier 1), `task` (Tier 2), and `deputy` of `agents.json`. Setup chooses the first two and optionally accepts `--deputy`; deputy defaults to Claude Sonnet and uses the same backend/model/limits schema (agents.md). Tier 3 uses no model: it wakes the chat that already
has the context.

### Waking the coordinator chat (any harness)

The task's `origin` says how to reach its chat: `harness` t3 (thread link, or configured webhook relay), `claude` (a Claude Code session id) or
`codex` (a Codex session id), plus the session's `cwd`. Register with `--origin-harness claude|codex [--origin-session ID] [--origin-cwd DIR]`
(without `--origin-session` the id is read from `CLAUDE_CODE_SESSION_ID` / `CODEX_THREAD_ID` of the shell that runs the command, only when the
harness is named; a delegated child session gets a warning) or `nrp-monitor origin task NAME --harness ... --session ... --evidence ...`.
For a closed session, for `claude` the monitor runs `claude -p --resume ID` in the chat's directory, for `codex` `codex exec resume
ID -` (prompt on stdin), so the wake lands in that chat's history. The Claude wake may run only `nrp-monitor task show|resume|cancel|needs-owner`,
`digest` and `status`. Before Claude resume, the monitor checks for a running process naming the session or
transcript activity within five minutes. An open/recent session is deferred, never reported
as delivered, because headless resume can fork an unseen sibling. Uncertain process inspection
also defers. These deferrals count toward `WAKE_MAX_TRIES` exactly like a failed webhook (an escalation falls back to
`NEEDS_OWNER`; a done/failure wake is dropped with a digest `fault` line).

T3 origins can use `origin.link: "t3-thread://v2/ENV/THREAD"` (angle brackets around the link are accepted).
A configured `<state>/webhooks/<task>` remains the preferred T3 route. Otherwise the monitor sends the wake text
on stdin to `t3 thread send THREAD -`. It selects `NRP_MONITOR_T3_BIN`, then `~/.t3/bin/t3`, then `t3` on PATH.
Missing binaries, nonzero exits, timeouts and an unavailable server count as unavailable delivery: retry up to
`WAKE_MAX_TRIES` (six passes), then fall back to NEEDS_OWNER for an escalation. No new thread is created.
Claude and Codex origins still resume their recorded sessions. Plan-step completion keeps one aggregate wake per step.

**What wakes the chat:** (1) once when a plan step finishes (several tasks of one step send one wake, from the last task to finish, naming
all of them); (2) as a last resort, once per escalation, when Tier 0/1/2 could not fix a failure (`escalation`); (3) a watch-only task's final
failure. A failure that is still going up the ladder no longer sends its own `failure` wake (v2 woke the chat at the failure and again at
escalation). Per-Job callback Secrets do not exist: the monitor sends every wake. Escalations are per task (a step's sibling tasks that fail
separately each escalate). If the last waiting sibling of a step is cancelled, the finished ones never send the step wake (known-issues.md).
The registering agent's handoff must say all this (SKILL.md step 7); `task add` prints the text to write and warns about a handoff that never
mentions it.

### Deadline timeouts (Tier 0, tasks)

`activeDeadlineSeconds` counts from the Job's start, Pending time included. Each pass, for a running stage's Job:
- **Credit queue time.** Once the pod has started after waiting Pending 10 minutes or more, the Job's deadline is patched in place to
  the original plus the wait (once).
- **Pending near the deadline** (under max(20% of the deadline, 15 min), at most 1 hour): kept alive in place to elapsed + original,
  up to 8 times, unless the pod is stuck on an image or config error.
- **Progressing near the deadline:** when the Job's log tail changed between two passes, the deadline is extended in place by the
  original, at most 2 times. A Job whose log did not advance is left to expire (an event says so).
- **Already dead (`slow`) and the stage resumes by skipping finished items** (`resumable: true` on the stage, or `--skip-existing` /
  `--resume` in its manifest command; nothing else is assumed): resubmitted once with 2x the deadline, silently.
- Anything else enters the ladder at Tier 1. A timeout never pages the owner directly; a second timeout of the same stage is a repeat
  after a fix, so it goes to Tier 3.

### Legacy jobs (`add`) and the person step

1. **No model.** The script classifies the failure (resources, util, code, queue, infra, outputs, slow) and handles
   routine events.
2. **Cheap triage.** For a registered Job with a resume file, one read-only agent looks first and returns a result or
   `ESCALATE` with evidence.
3. **Repair.** Up to two repair attempts for a legacy job follow-up (the ladder is configurable: agents.md). A task's Tier 2 agent has a
   task-wide retry cap (`max_retries`, default `max(4, ceil(stages/4))`; explicit values win) and class budgets (resources: 3 per stage; other classes remain task-wide). Code fixes are committed on `monitor/<task>`. The agent's prompt
   carries the task's handoff, and its `HANDOFF_ENTRY:` block is appended to the handoff's Fix log (handoff.md).
   A single bad item is skipped and logged; a pattern (more than 5% of items, by default; the `skip_limit_fraction`
   setting, install.md) goes to a person.
   A util fix agent that finds the Job healthy may answer `UTIL_OK: evidence` instead of a stop (a **util waiver**,
   utilization.md): the script accepts it only for a flag from the lab floor alone, on a Job that still runs, at most 3
   times per task; otherwise it is the stop below.
4. **A person.** The task becomes `NEEDS_OWNER` (tasks stored under the earlier name `NEEDS_HUNTER` are read as this) and the owner gets
   one DM. For a task that is: when its coordinator chat runs `task needs-owner`, when Tier 3 cannot reach the chat (above), for a
   watch-only task, GPU approval expiry, or a 6-hour utilization block. For a legacy job: when the follow-up ladder is used up.
   `nrp-monitor task resume NAME` continues after they decide.

An accepted util waiver sends no DM, uses no retry and adds a `util-waived` line to the digest. Retries are silent. When no agent can
run (every runner is out of usage), the work waits without using a retry and the owner gets one DM saying so.

## The digest

Everything routine is silent. `nrp-monitor digest --hours N` lists events, what needs a person, plans waiting, tasks with
no continuation, and a warning when the notification token is near expiry. `nrp-monitor status` shows scheduler heartbeat
age (exit 3 when stale while work is active), tasks that need the owner, tasks waiting on their coordinator chat, and runners out of usage.
The digest has a "With the coordinator chat, owner not notified" section next to "Needs the owner".

## Completion continuation (`on_done`)

When a task with `on_done` finishes, one continue agent reads the outputs and the plan, checks the step's "done when",
and registers the next approved step as a new task (which carries its own `on_done`). It cannot pass the plan's approved
range, a named stop, or the files the plan lets it touch. Night code goes on a branch for review, never to main.

Terminal Job replacement is separate from normal successful-stage cleanup: an explicitly
resumed/retried stage saves diagnostics, deletes its old Failed/Complete Job and submits again.
Running/pending Jobs are never deleted by the submit path; unknown status fails closed.

## Cost and wake evidence

Each new agent run, rule/decision resolution, coordinator wake queue event and owner notification appends a JSON line to `<state>/costs.jsonl`. Rows include task/stage, kind, tier, runner/model, outcome, fingerprint when relevant, USD cost and runner usage (null when unreported). Claude structured usage is retained; Gemini stats and Codex's reported token total are retained when available. No prices or token counts are invented. Reported Claude coordinator-session consumption is appended as a linked `coordinator_result` delivery event; coordinator routes that do not return usage have null cost. A wake is counted when queued, once per event id, rather than on every delivery retry; delivery success/failure remains in task events.

After handling a wake, run `nrp-monitor wake-review TASK --by rule|agent|coordinator --why TEXT`. This records who should have handled it, linked to that task's latest queued coordinator wake. Later reviews of the same wake supersede earlier reviews in the report while preserving the ledger history. `nrp-monitor costs --days 7 [--task NAME]` prints wakes per task/kind, recorded resolution percentages by tier, reported agent costs per tier/model and wake-review counts per intended handler/reason. Unreviewed wakes cannot be called avoidable from this evidence alone. Resolution percentages describe recorded recovery events, not eventual scientific correctness.

Completion wakes retain their existing behavior in this batch. Their volume is measured, not grouped or suppressed. Historical logs do not contain enough usage to reconstruct total coordinator-chat cost.

Baseline snapshot, 2026-11-12 at 22:34 UTC (read-only, UTC date in existing logs): 35 delivered wakes across four origin chats, comprising 19 escalations and 16 completions. Per anonymized origin: A 16 escalation + 2 done; B 0 + 2; C 3 + 2; D 0 + 10. `digest.log` records 20 escalation queues (A 17, C 3), versus 19 deliveries in `monitor.log`; one queued escalation had no delivery recorded at the snapshot. Task event rings keep only 80 entries, so aggregate counts use the append-only logs, mapped to current task origin metadata. Counts reflect the snapshot, not an immutable full-day total; no historical costs or avoidable-wake judgments are inferred. No historical events were imported into the new ledger.

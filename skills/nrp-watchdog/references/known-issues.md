# NRP watchdog: known issues (2026-11-09)

Each item says how well it is established. "Checked" means I confirmed it directly on
2026-11-09. "From logs" means taken from the watchdog's own logs and docs, not reproduced.
"Tested" means covered by the test suite (199 tests, none failing on 2026-11-09 in the repository layout, 1 skipped because the
nrp-cluster skill is not installed there; from the skill layout 197 pass and 2 skip: one needs the author's code-shipping helper, one needs the nrp-cluster
policy file installed). "Unverified"
means suspected or not confirmed.

**Deployment.** The fixes below are in the repository (`tools/nrp-watchdog/`). The copy that
launchd actually runs (`~/.local/bin/nrp-watchdog`) is still the old script until
`tools/nrp-watchdog/install.sh` is run. Items marked "in the repo" do nothing live until then.

## Changed since the first version of this list

- **Agent type, fallback and escalation are now configurable (was item 7).** *(In the repo; Tested.)*
  `~/.local/state/nrp-watchdog/agents.json` sets the runners in order (for example Claude, then
  Codex), a model per tier, and the job follow-up ladder (default triage, repair, repair). With no
  file the behaviour is what it was. `nrp-watchdog agents` shows it, `agents test` sends one tiny
  prompt through each runner. Checked live: both Claude (haiku) and Codex (`gpt-6.1-sol`) answered.
- **A usage limit no longer looks like a failed fix (was item 2).** *(In the repo; Tested with fake
  binaries.)* A "weekly limit" answer blocks that runner until its reset time and the next runner
  takes over. With every runner out of usage, fix agents, continue agents and job follow-ups wait
  without using a retry, and one Slack DM says so. Before this, on 11-06 and 11-07, two fix agents
  and a continue agent were recorded as failures and sent "needs you" DMs.
- **Completion without a continuation is now visible (part of item 5).** *(In the repo; Tested.)*
  `task add` warns (and refuses when `NRP_WATCHDOG_REQUIRE_CONTINUATION=1`) if a task has none of
  `on_done`, `followup` or `digest_only`. A finished task with none of them is listed in the digest
  as `no-continuation`. In the live state today, of 62 finished tasks 5 had a plan continuation, 17
  a one-shot read-only report, and 40 were digest-only; all 12 running tasks are digest-only.
- **A handoff document per task, so fix and continue agents inherit the registering agent's context.** *(In the repo; Tested
  with fake binaries.)* The registering agent writes a markdown handoff after the monitor is started
  (`## Registrar`, template `templates/handoff.md`) and attaches it with the task's `handoff` field or
  `nrp-watchdog task handoff NAME FILE`; the copy in the task folder is the one agents see. `task add` warns without
  one (`NRP_WATCHDOG_REQUIRE_HANDOFF=1` refuses) and a finished task with none is listed in the digest as `no-handoff`.
  Fix and continue agents get it in their prompt and end their answer with a `HANDOFF_ENTRY:` block that the script
  appends to the Fix log or Continuation section (a `FOR_OWNER:` line goes to the owner's section; no block gives an
  automatic line). The Registrar's hash is checked around every append and restored from the original if it changed.
  Not verified: a live Claude or Codex agent actually ending its answer with the block (the tests use a fake agent),
  and whether the Registrar guidance in the template produces good briefings in practice. Existing tasks have no
  handoff and run as before.
- **Shared numbers, optional local rules.** *(In the repo; Tested.)* The nrp-cluster skill's
  `references/utilization-policy.json` (proposed in `proposal/out/mission_control.patch`, not in the shared repo) holds
  only numbers that skill states (GPU floor 40%, limits within 20% of requests, 400 concurrent jobs). Stricter rules are an
  optional local override, `<state dir>/utilization-policy.local.json`, that can only be stricter; a key in neither file
  means that check is off. `nrp-util-check` and the watchdog's Job cap read this one effective policy; `nrp-util-check
  --policy` prints it and where each key came from. A built-in copy is the fallback and a test checks it equals the shared
  file. The 20% limit tolerance is documented only (no check uses it). The 5% skip limit is the `skip_limit_fraction`
  setting (default 0.05). Not done on the live machine yet: the local override file is not created.
- **Util waiver: a healthy Job flagged by the lab floor stops costing a DM.** *(In the repo; Tested with fake binaries; not yet
  seen live.)* A util fix agent may end with `UTIL_OK: evidence`. The script accepts it only when the failure is class util,
  the flag's rule is `lab` (`nrp-util-check` now ends each flag line with `rule=lab|nrp|gpu`; never an NRP-band or GPU flag, not
  a GPU stage), the Job is Running at that moment, and the task has used fewer than `util_waiver_max` (3) waivers. Then the task
  stays running, no retry or DM is used, the Job's lab-floor flag is suppressed for `util_waiver_hours` (6) or until the Job
  ends, and the digest gets a `util-waived` line; `task show` lists the waivers. Refused: the usual stop, with the reason.
  Limits: the rule comes from the flag line that raised the failure (plus the task's recent flag notes), not from a fresh
  check of every pod. Today only an NRP-counted flag at strike 2 raises a util failure (a lab-floor-only flag is recorded and
  never acted on), so in the current flow a waiver is mostly refused; it matters if lab-floor flags are ever escalated. A pod
  whose request is just above `small_pod_exempt` (for example 2 GiB against a 2,000,000,000-byte exemption) is an NRP-band
  flag, and is refused too.
- **Documentation that disagreed with the code is fixed.** The 10-minute claim (script docstring,
  strike-gap comment, house rules) is now 5 minutes; the docstring's `--min-age 600` is now 300;
  `WATCHDOG_ON_DONE.md` no longer says the `on_done.enabled` file is absent.
- **`nrp-util-check` was not in the repository.** It is now (`tools/nrp-watchdog/nrp-util-check`)
  and `install.sh` installs it.
- **An empty `--allowedTools` list made `claude -p` fail** (it needs a value). The flag is now
  left out when the list is empty. The lists are non-empty in practice, so I do not think it ever
  happened live.

## Still broken or unreliable

1. **Webhook delivery failed every time; the cause is found and fixed in the repo.** *(Checked 2026-11-09.)* About 2,090
   "webhook delivery failed; will retry" lines since 2026-11-06 across three tasks. The relay sits behind Cloudflare, which
   rejects Python's default User-Agent (error 1010, HTTP 403); the same request with a normal User-Agent is accepted (HTTP 202).
   The script now sends `nrp-watchdog/1.0`, a test checks it, and failures now log the HTTP status. *(In the repo, not yet
   deployed, so the three stuck outboxes are still queued; they are old, finished lit-map tasks.)* Whether a delivery then wakes
   the intended chat is not tested. A failing delivery also blocks the later events of that task.
2. **Claude push notifications are unreliable.** *(From logs.)* Entries read "not sent,
   terminal active". Slack DMs are the dependable channel; all 41 logged DMs show as delivered.
3. **Stale-heartbeat warning.** *(Wired on the author's machine 2026-11-09; Claude Code only.)* A SessionStart entry runs
   `nrp-watchdog status --quiet`, which prints a warning when the heartbeat is more than 25 minutes old while work is active,
   and lists tasks that need the owner. Other assistants have no equivalent; run `nrp-watchdog status` by hand.
4. **Completion does not wake the chat that asked for the work.** *(By design.)*
   An `origin` link records where a task came from. It is not a callback. Instead, the registering agent writes a handoff
   document before it returns, and the monitor starts fix and continue agents from it. The plan continuation (`on_done`)
   is one of those: a continue agent checks the plan step's "done when" and registers the next approved step, so the work
   moves on without the chat. It only runs for tasks registered with `on_done`, and only for plan steps that are approved
   and not marked as stops. Waking the original conversation would need the webhook (item 1, fixed in the repo but untested
   end to end).
5. **Registration is manual outside Claude Code.** *(Documented.)* The auto-arm hook does
   not run in Codex.

## Limits of the design

- **Codex agents are less restricted than Claude agents.** *(Checked with a live test on
  2026-11-09.)* Both are started with the same allowlist. For Claude, anything not on the list
  is denied, and file reads are limited to listed paths. For Codex, a command on the list may use
  the network and everything else runs in a sandbox with no network and writes only to the agent's
  own directories (with `/tmp` excluded), but the agent can still read any file the user can,
  including the lab token. Codex has a time limit but no dollar cap, and no turn limit.
- Agents have the same permissions as the user's own agents, no more, but they run
  unattended. Claude agents have a turn limit and a dollar cap. One mode, `code-test`, runs
  agent-written code with those rights. *(From the docs.)*
- The scheduler runs under launchd, which cannot read `~/Desktop`, so a follow-up agent
  started from there cannot read or edit the repo directly. The code is cloned into a cache.
- Plan steps marked as local session work never run automatically.
- The deadline rule ("derive from measured runtime") is enforced by the docs and the
  agents. The watchdog only checks that a deadline exists.
- The one-shot completion report (`followup`) is not retried: if every runner is out of usage at
  the moment a task finishes, the digest says the report was not written.
- A Codex allow rule matches a command prefix, so `kubectl delete job X` also allows extra flags
  after it. Claude's pattern does the same for the "exact" entries.

## Fixed earlier, worth knowing about

- On 11-06 the success check used a prefix listing, so `DONE.1` satisfied `DONE`, and an
  Indexed Job counted as succeeded when its first shard finished. A task closed at 34 of
  50 rows and its pods were deleted. *(From the log.)* It is fixed with an exact
  `head-object` check and a 21-test file. The job-side writer still does not invalidate a
  root `DONE` marker on re-run; that is a recommendation, not a change.
- Laptop access to S3 returned 503 on 11-07. It is mitigated by an in-cluster S3 fallback
  Job. *(From the log.)*

## Unverified

- A real fix agent running on Codex against the real cluster. The fallback is tested with fake
  `claude` and `codex` programs, and each runner answered a tiny live prompt, but I did not
  start a real repair through Codex.
- What Codex's real usage-limit message looks like. The detection is tested on Claude's real
  message (copied from the logs) and on a Codex-style message I wrote from memory of its wording.
- Whether the permission patterns for the fix agent's `claude -p` runs behave as designed.
  The offline test used a fake agent that ran commands directly.
- How much policy is baked into the script beyond the skip limit (now a setting) and the Job cap (now from the policy).
- Several tasks have no `origin` recorded, so their completions have nowhere to point.

## Built 2026-11-11 (tiered task ladder, Tier 0 deadlines; tested with fakes, not yet seen live)
- Tasks now run Haiku triage, then the Sonnet fixer, then wake the task's coordinator chat (`WITH_COORDINATOR`), and the owner is told only
  when the chat runs `task needs-owner`; a timeout never pages the owner directly (operations.md). Fixes the false-STUCK page below.
- Not verified: a real Haiku answering with a verdict line, and what the relay does with the `summary` field of an `escalation` event.
  The existing per-failure `failure` wake still fires for tasks with a webhook, so the chat can be woken at the failure and again at
  the escalation until the aggregate per-step wake replaces it.
- Deadline progress is judged by the log tail changing between passes. Per-item S3 output counts are not used (a stage's `done_s3` is a
  single marker). A resume-capable stage must say so (`resumable`); the script never infers it beyond `--skip-existing` / `--resume`.
- Several coordinator wakes for one task are not merged; one escalation is queued per Tier 3 entry.

## v3 changes in the repo (2026-11-11; Tested with fake kubectl/aws/claude and a stub Prometheus, not seen live)
- `nrp-task reship` packs every declared code dir (`code.pkg_dir`, `code.extra_pkg_dirs`) with the real `codeship.build` layout; the
  identical-code no-op check covers all of them. `nrp-watchdog task code NAME ...` declares them for a task registered without (ft-tables-w6).
  Not verified on a live pv3 Job: that a pod imports the reshipped `finetune`/`bwb` (the layout equals `--ship-code`'s by construction).
  An absolute `pkg_dir`/extra dir is read live at reship time, so a changed checkout changes the hash even when the clone did not.
- `task add` without `origin` is refused (continuations only warn). Chains and legacy `add` still only warn.
- Tier 0 rules (OOM x1.3, node-fault exclusion, long-Pending reason): operations.md. The node-fault pattern list is fixed in the script
  (`NODE_FAULT_RE`); extend it as new faults are seen. The OOM rule needs NRP's Prometheus; without a number it does nothing.
- Several tasks per plan step; the step is done when all are (tasks.md).

## v3 steps 2 and 5 (2026-11-11; fake claude/codex programs and mocked runners, nothing run live)
- Not verified live: that `claude -p --resume ID` with `--permission-mode dontAsk` reaches a session that is open interactively at the same
  time (Claude may start a copy; its `--bg --resume` help says so for background sessions); that `codex exec resume --all ID -` accepts a
  session from another directory and runs the shell commands the wake names under the user's own Codex sandbox/approval settings (the resume
  subcommand has no sandbox flags); that `CODEX_THREAD_ID` equals the id `codex exec resume` takes (it is in the Codex binary's environment
  list; not run). A wake that does not land is retried for `WAKE_MAX_TRIES` passes, then falls back to the owner.
- A wake blocks the pass while it runs (timeout 600 s). Several failing wakes in one pass can make a pass long; the pass lock keeps the next one from overlapping.
- If the last waiting task of a plan step is cancelled, the finished tasks of that step never send the step wake (nothing re-checks the step).
- Gemini runner: the allowlist rests on Gemini CLI's policy engine (admin policy, `commandPrefix`, `argsPattern`) as documented in the CLI's own docs;
  it was not run against the live model. `gemini -m ALIAS` with a custom alias and `thinkingLevel MINIMAL` for "lowest" are per those docs; a model
  that rejects MINIMAL needs `thinking: low` or a budget. Hence it is limited to the triage tier.

## Seen live 2026-11-10 (T71 step 6 fan-out, braindance_proj)
- False STUCK: a pod flagged "stuck creating 142 min" at the moment it started; the fix agent correctly left it running, but the
  task then went NEEDS_OWNER (owner had to `task resume --skip`). A "no fix needed" verdict should close the event, not page the owner.
- One task per plan step: a second TASK.json for the same step was refused, so per-cell tasks had to be merged into one. (Fixed in v3, above.)
- Queue time counts against activeDeadlineSeconds: GPU pods Pending for hours needed manual deadline extensions.
- Every pod exit woke the coordinator chat (12 large-context wakes for clerk work); v3 plan moves that to the script with one wake per step.

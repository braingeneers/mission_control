# v3: rename to nrp-monitor, tiered escalation, one coordinator thread  <!-- plan:nrp-monitor-v3 -->

Status: design agreed with Hunter 2026-11-10. Built so far (2026-11-11): the task ladder (Tier 1 Haiku, Tier 2 Sonnet, Tier 3 coordinator chat via `WITH_COORDINATOR`, `task needs-owner`) and the Tier 0 deadline rules; see operations.md. Built 2026-11-11 (step 2 and 5): one coordinator chat woken whatever harness it runs in (T3 webhook, Claude Code session, Codex session), one wake per plan step, per-tier backends chosen by `nrp-monitor setup` (Claude / Codex / Gemini CLI). Built 2026-11-11 (step 1): rename, state/launchd migration, compatibility shim and capped smoke/profile registration. Source of truth for the monitor is this skill (mission_control skills/nrp-monitor); the copy in braindance_proj/tools/nrp-monitor is stale. Review answers still open: the PR #7 questions (repo location, delete-after-two-flags).
**Central question:** can the script do almost all monitoring, with models woken only for judgement, all in the plan's own thread?
**What changes with the answer:** models stop polling and doing clerk work (12 manager wakes for one T71 fan-out, 2026-11-10);
Hunter hears only when he is truly needed.

```run
plan: nrp-monitor-v3
approval: none yet (design agreed in chat 2026-11-10, see Hunter's decisions; implementation plan still to be approved)
steps: 1, 2, 3, 4, 5
approved_through: none
stop_for_hunter: 1
may_touch: tools/nrp-monitor/, docs/agents/
```

**Hunter's decisions** (chat rt-sort-3d_A2, 2026-11-10, verbatim):
- "the way I want these monitors to function is for you the manager to be able to be called if needed but have the python script
  do most of the monitoring. if there is something that needs judgement a haiku agent can decide and escalate from there where a
  sonnet agent should try and fix. if it cant or is not confident then would escalate to the main agent but starting new threads is annoying."
- Goal (as told to a friend): avoid a long-context subagent that "would sit and poll the job every XX minutes then possibly losing
  the cache or just overally being more expensive call than it should", while still getting it "to properly iterate and catch if
  resources werent being used properly becuase that is also bad".
- "a model should get notified upon success or failure and only when I am absolutely needed after teh escalation should I get notified"
- Plan rules as monitor rules: "yes and that should follow the nrp skill"
- Name nrp-monitor: "I like that better"
- "the subagents shuolid be attached to that chat not a new thread. we should also have this be able to be used for others subs if
  it works with claude code, codex, or t3 type of deal with multiple subscriptions"

**Hunter's decisions** (chat "BWB FT prep", 2026-11-11, verbatim):
- On the ladder: "escalation from a haiku to a sonnet for general fixing and then opus if sonnet cant and only then to notify me".
- Tier 3 is the coordinator chat, not a separate Opus fixer: "I think the chat since it has all of the context to help fix".
- "we need to actually implement and push to main not a PR for this".

**Hunter's answers to the open questions** (build session, 2026-11-11, verbatim):
- Q1, how a non-T3 coordinator binds to "the coordinator thread": "regardless of claude code or codex or t3 it should wake the same chat yeah. and then importantly I hope this is how it would work is if there is a long running agent that built and sent the job it would write in the handoff for this and let the subagents handle only going to the main chat as a last resort and me as a last last resort"
- Q2, one subscription per tier or failover: "that should be prompted when the user downloads the skill as to what subscription the user has and what they want to use for each. for instance I think for me I would actually like to have my low level agent be changed to gemini flash with lowest tier thinking for this and escalate to a sonnet agent and then opus agent"
- Follow-up (asked whether to add a separate Opus agent between Sonnet and the coordinator chat), verbatim: "close and yes update but after the sonnet agent just send to the coordinator chat"
- Resulting ladder: Tier 1 Gemini Flash (lowest thinking) -> Tier 2 Sonnet -> Tier 3 coordinator chat -> Hunter. No separate Opus agent.

**Added 2026-11-11 (seen live on ft-tables-w6, spike-tokenizer-scaling):**
- Deadline timeouts (`slow` class) go straight to NEEDS_OWNER in v2 (`handle_failure`), skipping every agent. v3: Tier 0 first
  (pod still progressing, i.e. per-item outputs or log lines advancing -> extend `activeDeadlineSeconds` in place, or resubmit once
  with 2x deadline when the job resumes by skipping finished items); then the normal ladder. Never page Hunter for a timeout directly.
  W6 lost a whole stage at 495/510 because one slow node (pas.pitt.net.internet2.edu) ran one pod 10x slower.
- Tasks get the full ladder too (v2: one Sonnet `task` agent, then NEEDS_OWNER; the Haiku->Sonnet ladder exists only for legacy jobs).
- `nrp-task reship` only packs `code.subdir` = the predictor_v3 package; tasks whose code also ships extra package dirs (e.g.
  `finetune/` from spike-tokenizer-scaling via codeship `extra_pkg_dirs`) could not be reshipped, so four correct Sonnet fixes on
  ft-tables-w6 stalled waiting for a person. v3: reship packs every dir the task's spec declares.
- `task add` without `origin` must be refused (v2 only warns); ft-tables-w6 had none, so its alert named no chat and no chat was woken.

**Agreed design:**
- Tier 0, script (no model): submit, track states, success markers, DCGM/thanos utilization against the nrp-cluster skill and house
  rules; fixed rules applied without a model (OOM -> peak x1.3; known node fault -> exclude node, resubmit; Pending near deadline ->
  extend; finished Jobs deleted after markers verified; profile -> model decides full sizing inside approved limits).
  Long Pending reports the scheduler's reason (e.g. our own GPU allow-list).
- Tier 1, Haiku triage on events Tier 0 cannot classify: small event packet (state, log tail, metrics), answers benign / menu action /
  escalate. (2026-11-10 false STUCK on a pod that had just started should have ended here as benign.)
- Tier 2, Sonnet fixer: code/config/resize inside may_touch, resubmits, fix log; escalates when not confident, on a repeat after a fix,
  or on any scientific choice.
- Tier 3 (Opus step of the ladder), manager model in the plan's coordinator thread (Hunter 2026-11-11: the chat, it has the context): woken on step success or failure (one aggregate wake per step, not per pod)
  and on Tier 2 escalations; wake = short summary + pointers. Hunter is notified only when the manager needs him.
- All agent activity (Haiku, Sonnet, manager) posts into the plan's bound coordinator thread; never a new thread.
- The monitor sends the wake (covers OOM/node loss, no per-Job callback Secrets).
- Harness-agnostic: agents runnable through Claude Code, Codex or T3 delegation, across several subscriptions (configurable backend per tier).
- Fix in passing: allow several tasks per plan step; queue time must not eat the run deadline.

**Fan-out question answered (Hunter):** "we shouldnt send out a hundred jobs to see what the memory is best but maybe a few? i think we just need to cap the smoke tests"; "the subagent handling this should make the decision, probably sonnet or the coordinator chat".
Use shared `smoke_max_jobs` (default 3), include the largest/longest item, and leave full sizing to Tier 2 or the coordinator within approved limits. The script never launches the full fan-out on its own.

ANSWERED 2026-11-11 (above, built): how a non-T3 harness binds to "the coordinator thread" (the
origin records harness + session id; the monitor resumes that session), and one subscription per tier vs failover (each tier has an ordered
backend list chosen at install time; the next entry only on unavailable/auth/limit errors).

## Start here (handoff for the build session, 2026-11-10)
- Approved by Hunter 2026-11-10: "I think that this all sounds good as a plan!" and push straight to main (no PR needed). Build v3 in
  this repo, `skills/nrp-monitor/` renamed to `skills/nrp-monitor/`, commit and push to main.
- State: v2 merged to main (60a779b) and installed live on Hunter's laptop (`~/.local/bin/nrp-*`, launchd every 5 min, state in
  `~/.local/state/nrp-monitor/`). Live tasks are running on it (t72 validation build, finch, lit-map): keep it working through the
  rename (compat alias `nrp-monitor` -> `nrp-monitor`, same state dir or a migration) and install only after tests pass.
- Tests: `cd skills/nrp-monitor/scripts && python -m pytest -q tests` (249 passed, 1 skipped at 1aea3fa, ~3 min).
  Repo tests: `python -m pytest -q tests` (1 pre-existing failure on main, test_skill_authenticate paste test).
- Suggested order: (1) rename + compat; (2) per-step aggregate wake from the script (monitor sends the T3 webhook, bound to the plan's
  coordinator thread), drop per-Job callback Secrets; (3) Tier-0 rules: auto deadline extension for Pending, node-fault exclusion,
  OOM resize, cleanup, capped profile then model sizing decision; (4) Haiku triage tier with a fixed action menu
  ("no fix needed" closes the event, never NEEDS_OWNER); (5) per-tier backend config (Claude Code / Codex / T3, several subscriptions);
  (6) several tasks per plan step.
- Open questions for (2) and (5) answered 2026-11-11 (see Hunter's answers); built in the same session.
- Delegation: Sonnet/Sol agents for coding and tests (Hunter's preference); keep the build session small and relay with a handoff.

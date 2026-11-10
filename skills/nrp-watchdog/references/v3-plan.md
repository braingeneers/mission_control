# v3: rename to nrp-monitor, tiered escalation, one coordinator thread  <!-- plan:nrp-monitor-v3 -->

Status: design agreed with Hunter 2026-11-10, NOT built. Source of truth for the monitor is this skill (mission_control skills/nrp-watchdog); the copy in braindance_proj/tools/nrp-watchdog is stale. Review answers still open: questions in "Open questions" below, plus the PR #7 questions (repo location, delete-after-two-flags).
**Central question:** can the script do almost all monitoring, with models woken only for judgement, all in the plan's own thread?
**What changes with the answer:** models stop polling and doing clerk work (12 manager wakes for one T71 fan-out, 2026-11-10);
Hunter hears only when he is truly needed.

```run
plan: nrp-monitor-v3
approval: none yet (design agreed in chat 2026-11-10, see Hunter's decisions; implementation plan still to be approved)
steps: 1, 2, 3, 4, 5
approved_through: none
stop_for_hunter: 1
may_touch: tools/nrp-watchdog/, docs/agents/
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

**Agreed design:**
- Tier 0, script (no model): submit, track states, success markers, DCGM/thanos utilization against the nrp-cluster skill and house
  rules; fixed rules applied without a model (OOM -> peak x1.3; known node fault -> exclude node, resubmit; Pending near deadline ->
  extend; finished Jobs deleted after markers verified; profile inside the plan's sizing rules -> render and submit the fan-out).
  Long Pending reports the scheduler's reason (e.g. our own GPU allow-list).
- Tier 1, Haiku triage on events Tier 0 cannot classify: small event packet (state, log tail, metrics), answers benign / menu action /
  escalate. (2026-11-10 false STUCK on a pod that had just started should have ended here as benign.)
- Tier 2, Sonnet fixer: code/config/resize inside may_touch, resubmits, fix log; escalates when not confident, on a repeat after a fix,
  or on any scientific choice.
- Tier 3, manager model in the plan's coordinator thread: woken on step success or failure (one aggregate wake per step, not per pod)
  and on Tier 2 escalations; wake = short summary + pointers. Hunter is notified only when the manager needs him.
- All agent activity (Haiku, Sonnet, manager) posts into the plan's bound coordinator thread; never a new thread.
- The monitor sends the wake (covers OOM/node loss, no per-Job callback Secrets).
- Harness-agnostic: agents runnable through Claude Code, Codex or T3 delegation, across several subscriptions (configurable backend per tier).
- Fix in passing: allow several tasks per plan step; queue time must not eat the run deadline.

**Open questions:** whether the monitor may launch a fan-out on its own when the profile is inside the plan's rules (my recommendation:
yes, those rules are already approved); how a non-T3 harness binds to "the coordinator thread" (Codex/Claude Code session ids vs T3 threads);
one subscription per tier or failover between them.

## Start here (handoff for the build session, 2026-11-10)
- Approved by Hunter 2026-11-10: "I think that this all sounds good as a plan!" and push straight to main (no PR needed). Build v3 in
  this repo, `skills/nrp-watchdog/` renamed to `skills/nrp-monitor/`, commit and push to main.
- State: v2 merged to main (60a779b) and installed live on Hunter's laptop (`~/.local/bin/nrp-*`, launchd every 5 min, state in
  `~/.local/state/nrp-watchdog/`). Live tasks are running on it (t72 validation build, finch, lit-map): keep it working through the
  rename (compat alias `nrp-watchdog` -> `nrp-monitor`, same state dir or a migration) and install only after tests pass.
- Tests: `cd skills/nrp-watchdog/scripts && python -m pytest -q tests` (249 passed, 1 skipped at 1aea3fa, ~3 min).
  Repo tests: `python -m pytest -q tests` (1 pre-existing failure on main, test_skill_authenticate paste test).
- Suggested order: (1) rename + compat; (2) per-step aggregate wake from the script (monitor sends the T3 webhook, bound to the plan's
  coordinator thread), drop per-Job callback Secrets; (3) Tier-0 rules: auto deadline extension for Pending, node-fault exclusion,
  OOM resize, cleanup, fan-out from a profile inside the plan's sizing rules; (4) Haiku triage tier with a fixed action menu
  ("no fix needed" closes the event, never NEEDS_OWNER); (5) per-tier backend config (Claude Code / Codex / T3, several subscriptions);
  (6) several tasks per plan step.
- Answer the open questions with Hunter before (2) and (5).
- Delegation: Sonnet/Sol agents for coding and tests (Hunter's preference); keep the build session small and relay with a handoff.

# Handoff: nrp-monitor modular rewrite  (2026-11-18, R2 answers session)
**Plan and active steps:** PLAN.md (nrpmon-rewrite). Hunter answered DESIGN.md §4 (verbatim in PLAN.md). Running in
parallel: P (utilization patch, main) and R3a (cuts + package scaffold, branch `nrp-monitor-rewrite`). Stop for Hunter
before R4 (installing the new package) and before R6.
**Where we are:** C5 done (state-dir clutter trashed; chains state moved to `S/backup/chains-20261118/`; the running
monitor tolerates the missing dir). Cut register is in PLAN.md.
**In flight (T3 delegates; completion wakes the parent thread):**
- P (codex gpt-6.1-sol, main checkout): utilization patch; commits to main, installs, reports first live pass.
- R3b (claude opus, worktree ~/.t3/worktrees/mission_control/t3-5d6f3948-7a71276ff0751a9b): state machine, ladder as
  data, one cluster layer, one runner. Branch `nrp-monitor-rewrite`.
R3a DONE: cuts C1-C4 + package split pushed (4e1a038); full suite verified by main session: 587 passed (645 minus 58
cut-feature tests listed in the branch's Cut register). Code map deferred until R3b lands (would go stale);
work dir: scratchpad nrpmon-codemap, rerun `refresh.sh` with a new WORK on the R3b head.
Check from outside: `git log origin/main -3`, `git log origin/nrp-monitor-rewrite -5`, `cat ~/.local/state/nrp-monitor/INSTALLED`.
**Next:**
1. P report: run tests, check live pass, tell the t71 chat (c38c20f5) what changed.
2. R3b report: line counts before/after, test diff only import/patch lines; then code map (summarize-codebase via
   Gemini on scripts/nrp_monitor), then R3c port P, then stop for Hunter before R4.
**Open for Hunter:** decision 5 (Workflows stage type), explained in chat; recommendation: R6 after the swap.
**Read first:** PLAN.md, DESIGN.md, LOG.md top entry.

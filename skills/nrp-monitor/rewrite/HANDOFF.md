# Handoff: nrp-monitor modular rewrite  (2026-11-18, R2 answers session)
**Plan and active steps:** PLAN.md (nrpmon-rewrite). Hunter answered DESIGN.md §4 (verbatim in PLAN.md). Running in
parallel: P (utilization patch, main) and R3a (cuts + package scaffold, branch `nrp-monitor-rewrite`). Stop for Hunter
before R4 (installing the new package) and before R6.
**Where we are:** C5 done (state-dir clutter trashed; chains state moved to `S/backup/chains-20261118/`; the running
monitor tolerates the missing dir). Cut register is in PLAN.md.
**In flight:** one T3 delegate (codex gpt-6.1-sol) in worktree ~/.t3/worktrees/mission_control/t3-5d6f3948-7a71276ff0751a9b:
finish R3b (piece 3 cluster snapshot: 1 failing test; piece 4 runner table), drop unused imports, then R3c (port
patch P bdb03a4 from main). The branch's own HANDOFF.md has the detailed steps; completion wakes the parent thread.
**Done:** P live on main (bdb03a4, installed 09:37, 662 tests; t71 chat told). R3a pushed (587 tests, main-session
verified). R3b pieces 1 (state machine 316f168) and 2 (ladder as data b8bcff9; handle_failure 112 -> 17 lines) pushed.
**Size reality (7df136a):** package 8,998 lines = code 6,610 + imports 927 + blank 1,020 + docstrings 305 + comments 136.
Structure is better, but it is not condensed yet; the DESIGN.md 5,500 estimate needs real dedupe after R3c.
**Next:**
1. Review the delegate's report: tests vs main minus cut tests; line counts; its 5 duplication opportunities.
2. Code map: summarize-codebase on scripts/nrp_monitor (Gemini delegate) with a new WORK dir.
3. Give Hunter the size numbers and dedupe options as a decision; then R4 shadow run; stop before install.
**Open for Hunter:** decision 5 (Workflows stage type), explained in chat; recommendation: R6 after the swap.
**Read first:** PLAN.md, DESIGN.md, LOG.md top entry.

# Handoff: nrp-monitor modular rewrite  (2026-11-18, R2 answers session)
**Plan and active steps:** PLAN.md (nrpmon-rewrite). Hunter answered DESIGN.md §4 (verbatim in PLAN.md). Running in
parallel: P (utilization patch, main) and R3a (cuts + package scaffold, branch `nrp-monitor-rewrite`). Stop for Hunter
before R4 (installing the new package) and before R6.
**Where we are:** C5 done (state-dir clutter trashed; chains state moved to `S/backup/chains-20261118/`; the running
monitor tolerates the missing dir). Cut register is in PLAN.md.
**In flight (T3 delegate tasks, codex gpt-6.1-sol; completion wakes the parent thread):**
- P: [nrp-monitor utilization patch (P)] — commits to main, installs, reports first live pass.
- R3a: [nrp-monitor rewrite R3a (branch)] — worktree, pushes branch `nrp-monitor-rewrite`.
Check from outside: `git log origin/main -3`, `git log origin/nrp-monitor-rewrite -5`, `cat ~/.local/state/nrp-monitor/INSTALLED`.
**Next:**
1. Review P's report: run `python3 -m pytest tests -q`, check live pass, tell the t71 chat (c38c20f5) what changed.
2. Review R3a: test diff has only import/patch lines; module sizes; then code map (`summarize-codebase` on
   scripts/nrp_monitor via Gemini delegate).
3. R3b (state machine, ladder as data, one cluster layer, one runner): Opus-level; then R3c port P.
**Open for Hunter:** decision 5 (Workflows stage type), explained in chat; recommendation: R6 after the swap.
**Read first:** PLAN.md, DESIGN.md, LOG.md top entry.

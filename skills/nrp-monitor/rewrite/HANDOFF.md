# Handoff: nrp-monitor R4 day shadow  (2026-11-18 12:00, main session)
**Plan and active steps:** nrpmon-rewrite, PLAN.md R4. Approved through the shadow; STOP for Hunter before install/swap. R5 later; R6 unapproved.
**Where we are:** comparator verified (664 tests pass; newest LOG entry). Branch `nrp-monitor-rewrite` pushed. No suspected rewrite bug so far; pending/unknown rows are coverage limits, not equivalence.
**In flight:** day loop, 96 shadow passes every 15 min, ends ~2026-11-19 12:00 local.
- Check: `kill -0 $(cat /private/tmp/claude-501/nrp-shadow/loop.pid) && tail -5 /private/tmp/claude-501/nrp-shadow/loop.log`
- Reports: gitignored `rewrite/shadow/runs/`; persisted results under `/private/tmp/claude-501/nrp-shadow/`.
- The loop runs code from this worktree: edits here change later passes. Note the time of any edit in LOG.
**Next:**
1. After the loop ends (or earlier for a partial read): from the worktree, `/Users/hunterschweiger/miniconda3/bin/python3 skills/nrp-monitor/rewrite/shadow/run.py --day-summary 2026-11-18T11:55:00`.
2. Check every unexplained row against installed monitor.log (read-only). Fix comparator gaps with a test; treat real decision differences as rewrite bugs.
3. Report to Hunter: counts, each unexplained row and its cause, and a recommendation on the R4 install/swap. Do not install.
4. At merge to main, regenerate code-map aggregates (_INDEX/_GRAPH/_FEATURES conflict).
**Gotchas:** state copy is sequential, not atomic; installed agents in flight at snapshot time are now matched. One pass takes ~60 s.
**Read first:** PLAN.md R4; newest LOG entry; shadow/AUDIT.md; latest runs/ report.

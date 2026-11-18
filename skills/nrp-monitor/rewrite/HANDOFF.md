# Handoff: nrp-monitor rewrite  (2026-11-18, main session)
**Plan and active steps:** plan `nrpmon-rewrite` (PLAN.md). R3a/R3b/R3c done on branch `nrp-monitor-rewrite`
(worktree ~/.t3/worktrees/mission_control/t3-5d6f3948-7a71276ff0751a9b, head fa07454). Stop: before install (R4 swap).
**Where we are (verified):** 604 tests pass on the branch (= main 662 − 58 cut tests; verified by main session).
Only assertion change outside cut tests: a new test that the judge is off by default. Code map for the package
committed at `.code-summaries/` (27 files). Size: 8,855 lines (imports 577, blank 1,040, code 6,790).
**Waiting on Hunter (asked 11-18, with recommendation):**
1. Condense before the R4 shadow? Five dedupe items in the branch's rewrite/LOG.md (sizing evidence; manifest
   resize/replace; CLI registration; agent prompt/run/report; locked JSON txns). Recommend: a Sol agent does
   1, 2, then 3, 5 (not 4) behind the 604 tests, then the shadow runs once on final code. Rough guess −500..1,000 lines.
2. Workflows stage type: recommend R6 after the swap.
3. Offered: a repo-wide code map (87 other files unmapped; freshness check lists them).
**Next:** on Hunter's answer, start the condense agent (codex gpt-6.1-sol) in the branch worktree, or go to R4
per the branch's rewrite/HANDOFF.md (read-only shadow with isolated state; no install).
**In flight:** nothing.
**Read first:** branch rewrite/HANDOFF.md and top LOG entry; PLAN.md cut register.

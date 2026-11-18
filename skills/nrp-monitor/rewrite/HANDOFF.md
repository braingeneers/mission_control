# Handoff: nrp-monitor rewrite  (2026-11-18, main session)
**Plan and active steps:** plan `nrpmon-rewrite` (PLAN.md; Hunter's post-R3 answers recorded). Branch `nrp-monitor-rewrite`
(worktree ~/.t3/worktrees/mission_control/t3-5d6f3948-7a71276ff0751a9b). Active: R4 shadow prep. Stop: before install (R4 swap). R6 = Workflows stage type.
**Done + verified this session:** condense items 1,2,3,5 (2b4d996..846566c, map bc458c0, LOG/HANDOFF 6071cce): new owners
stage_jobs.py (submit/restart/logs/resources), sizing.py (all evidence), cli_args.py, state.py locked-JSON helper. Main session
re-ran the suite: 604 passed (225.9s). Code 6,790 -> 6,800 (findability, not size, per Hunter). Repo code map merged to main (655966f).
NRP resource-use changes (a8bbd60, 1c7debc, bdb03a4) confirmed present in the rewrite.
**Shadow so far:** prep 55b96da (14 gated routes, 643 tests). Main session 25f821d: read-only S3 allowed, skipped kubectl -> rc 125
(650 passed). First-pass "unexplained" rows were checked against installed state: installed monitor saw the same failures and
resubmitted -> they match. Remaining artifacts: timing (shadow sees newer cluster events) and ladder cascade after skipped actions.
**In flight:** T3 delegate "nrp-monitor shadow comparator" (codex gpt-6.1-sol, branch worktree): decision-level matching with lagged
installed window + pending rows, find the 4 "filesystem write outside isolated state" routes, --day-summary mode, tests.
Check: `git -C <worktree> log --oneline 25f821d..HEAD`.
**Next:**
1. When it returns: review its diff and the filesystem-write finding, re-run the suite, read the last run.
2. Run the shadow every ~15 min for a day: detached nohup loop (96 iterations) of rewrite/shadow/run.py with reports in rewrite/shadow/runs/; then --day-summary.
3. Report the day's comparison to Hunter with a recommendation; stop before install.
4. At branch merge: regenerate .code-summaries aggregates (both branches have maps).
**Read first:** branch rewrite/HANDOFF.md + top LOG entry; PLAN.md R4 + cut register.
**Open questions for the user:** none now. Installation needs Hunter's explicit approval.

# Handoff: nrp-monitor R4 shadow (2026-11-18)
**Plan and active steps:** `nrpmon-rewrite`, PLAN.md R4. One isolated shadow pass completed; day comparison pending. Stop before install/swap. R5 later; R6 unapproved.
**Where:** branch `nrp-monitor-rewrite`, worktree `/Users/hunterschweiger/.t3/worktrees/mission_control/t3-5d6f3948-7a71276ff0751a9b`. No push, installation, live mutation or scheduling.
**Checked:** explicit `run --shadow` gates plus filesystem/subprocess/HTTP allowlists. Normal decision path runs only on an isolated copied state; see `shadow/AUDIT.md`. Installed monitor was read, never executed.
**Evidence:** `shadow/2026-11-18-single-pass.md`: 14 live tasks / 23 stage rows; 10 expected suppression differences, 3 unexplained, 4 unchanged with recent evidence, 6 unknown recent decisions. Private snapshot `/private/tmp/claude-501/nrp-shadow/pass-afbwh5g0`.
**Unexplained:** newly observed failed stages for 20260720 ws17–64, 20260720 ws65–128, and loop1 ws65–128. Same group-bound parsing ValueError; time drift is plausible but unproven. Agent suppression explains subsequent coordinator routing only.
**In flight:** none. Final suite: 643 passed, 7 existing warnings, 262.48s (`/tmp/r4-suite.txt`). No live shadow pass remains running.
**Next:**
1. Run the shadow over a day, then report to Hunter; stop before install. Main session chooses cadence; no scheduling authorized here.
2. Runner: `/Users/hunterschweiger/miniconda3/bin/python3 skills/nrp-monitor/rewrite/shadow/run.py` from this worktree. Each invocation refreshes an isolated copy, runs one pass, saves a timestamped report. Never run the installed monitor for comparison.
3. Investigate unexplained changes and incomplete coverage; compare fresh installed logs/task events, not only state totals. Obtain separate Hunter approval before any install/swap.
**Gotchas:** AWS HEAD observations deliberately suppressed; S3 unknown. Admission create probes, fallback Jobs, agents, notifications, postchecks and wakes skipped. Legacy check_pods reached a forbidden delete and stopped: incomplete coverage, zero deletes. Local downstream transitions after skipped agents are provisional. This is not proof of equivalence or installation acceptance.
**Read first:** PLAN.md R4/Cut register; newest LOG entry; shadow/AUDIT.md; shadow/2026-11-18-single-pass.md; scripts/nrp_monitor/shadow.py.
**Open questions:** none blocks repeating read-only comparisons; uncertainty remains in the three stage failures and global legacy enforcement coverage.

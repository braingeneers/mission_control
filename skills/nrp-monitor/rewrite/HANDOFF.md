# Handoff: nrp-monitor R4 shadow preparation (2026-11-18)
**Plan and active steps:** `nrpmon-rewrite` in PLAN.md; R3b/R3c and requested ownership consolidation complete. Next is R4 shadow comparison. Stop for Hunter before installing/swapping the package; R5 later, R6 unapproved.
**Where:** branch `nrp-monitor-rewrite`, worktree `/Users/hunterschweiger/.t3/worktrees/mission_control/t3-5d6f3948-7a71276ff0751a9b`. No push or install performed.
**Checked:** each consolidation item passed 604 tests; final 604 passed, 7 existing warnings (233.55s). Ruff F401/F821, eager-cycle scan and diff whitespace clean. Package code map current; unrelated repository map gaps remain. Commits, counts and exhaustive patch-target edits: newest LOG entry.
**Unknown:** live shadow decisions, installed-state compatibility over a real day, and installation. No live task operations performed.
**In flight:** none. Suite logs `/tmp/condense-{1,2,3,5}.txt`; map check `/tmp/condense-map-check.json`.
**Read first:** PLAN.md R4/Cut register; newest LOG entry; DESIGN.md §1; cli.py run_pass and task/pass_.py process_tasks.
**Owners:** sizing.py evidence/fallback; stage_jobs.py stage submission/replacement/diagnostics/resources; cli_args.py parser registration; state.json_txn locked single-file updates. Agent prompt/run/report consolidation was explicitly skipped.
**Next:**
1. Prepare the read-only shadow comparison with isolated state. Audit every dry-run route before invoking it; suppress notifications and agent launches. Do not run a normal monitor pass against production state. Obtain the installed monitor's comparable observations without modifying its installation/state.
2. Compare decisions over a day, recording differences, evidence and outcomes in LOG.md. Keep cut-feature differences tied to the Cut register.
3. Report the shadow result to Hunter and stop before installing/swapping anything. No installation approval is implied by completion of R3.
**Gotchas:** action guards intentionally use fresh single-Job reads, not pass snapshots. s3.incluster_job retains direct kubectl-create. RUNNER_EXEC/exec_* patch targets remain. Test-only monitor_imports routes moved functions; no production compatibility namespace. Multi-file wake claims retain outer locks.
**Check:** `cd skills/nrp-monitor/scripts && /Users/hunterschweiger/miniconda3/bin/python3 -m pytest tests -q -p no:cacheprovider > /tmp/r4-suite.txt 2>&1`.
**Open questions:** none blocks shadow preparation. R4 has not started.

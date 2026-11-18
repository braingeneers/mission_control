# Handoff: nrp-monitor R4 shadow validation (2026-11-18)
**Plan and active steps:** `nrpmon-rewrite` in PLAN.md; R3b/R3c complete. Next is R4 shadow comparison; stop for Hunter before installing/swapping the package. R5 follows later; R6 remains unapproved.
**Where:** branch `nrp-monitor-rewrite`, worktree `/Users/hunterschweiger/.t3/worktrees/mission_control/t3-5d6f3948-7a71276ff0751a9b`. Do not edit main or install/touch ~/.local during shadow preparation.
**Verified:** R3b's three checkpoints each passed 587 tests. P's 17 new cases passed; final suite 604 passed, 7 existing warnings (366.64s). See newest LOG entry for commits, measurements and test-inventory reconciliation.
**Unverified:** live shadow decisions, compatibility with installed state under a real day of observations, and installation. No live task operations were performed here.
**In flight:** none after final validation. Test outputs are `/tmp/r3-{suite,piece4-suite,condense-suite,P-suite}.txt`; suite command is below.
**Read first:** PLAN.md R4 and Cut register; latest LOG.md entry; DESIGN.md §1; scripts/nrp_monitor/cli.py `cmd_run_pass`/`run_pass` and task/pass_.py `process_tasks`.
**Next:**
1. Refresh/create the code map requested in PLAN.md for the final R3b/R3c package; this task did not refresh it.
2. Present the final size and five duplication opportunities from LOG.md to Hunter for the further-condensation decision (per main's handoff). Do not implement extra deduplication unasked.
3. Prepare the read-only shadow comparison with isolated state. Audit every dry-run route before invoking it; suppress notifications and agent launches. Do not run a normal monitor pass against production state. Obtain the installed monitor's comparable observations without modifying its installation/state.
4. Compare decisions over a day, recording differences, evidence and outcomes in LOG.md. Keep cut-feature differences tied to the Cut register.
5. Report the shadow result to Hunter and stop before installing/swapping anything. No installation approval is implied by completion of R3.
**Gotchas:** action guards intentionally use fresh single-Job reads; batched fake Pending JSON differs from its single-Job response. `s3.incluster_job` retains its directly invoked kubectl-create contract. Test-only monitor_imports routes patches; it is not a production compatibility namespace. See LOG for five unimplemented duplication opportunities.
**Checks:** `cd skills/nrp-monitor/scripts && /Users/hunterschweiger/miniconda3/bin/python3 -m pytest tests -q -p no:cacheprovider > /tmp/r4-suite.txt 2>&1` (about 4 minutes; background and read the output file).
**Open questions:** none blocks shadow preparation; Hunter's explicit approval is required for installation.

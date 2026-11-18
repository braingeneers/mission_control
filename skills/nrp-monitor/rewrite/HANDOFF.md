# Handoff: R3a package move complete; next is R3b

Work only on branch `nrp-monitor-rewrite` in
`/Users/hunterschweiger/.t3/worktrees/mission_control/t3-5d6f3948-7a71276ff0751a9b`.
Main checkout and installed monitor were not edited. No install, R3b, or patch P port occurred.

Implementation commits: `512a77f`, `6805600`, `9782a7b` (package move plus retained C2 copy repair).

## Read first
`PLAN.md` (approval and Cut register), `DESIGN.md` §1, newest `LOG.md` entry.
C1-C4 remain cut as registered. R3a mechanically extracted all 350 retained
functions/classes into `scripts/nrp_monitor/`; entry point resolves its real path.
`install.sh` copies the package and `nrp-task` continues through the entry point.

## Verification
587 passed, 7 warnings in 234.08s (0:03:54)
Use `/Users/hunterschweiger/miniconda3/bin/python3` (pytest available).
Baseline `88ef48f` from immutable archive: 293 passed, then one retained failure
in `test_plan_groups.py::test_success_copy_bounded_and_exact` (`-x` stopped).
C2 had removed bounded S3 completion-copy support and emptied its `may_touch`
scope. Both are restored exactly; night code authoring remains removed.
Stale C1 prepass patch and the wake-constant source helper were retargeted.
All retained assertion ASTs are unchanged; changed-assert diff grep is empty.
CLI help parses at all 36 command paths. Compile/undefined-name checks pass.
Eager import graph is acyclic. All modules are below 800 lines; counts in LOG.

## Import and patch rules
Cross-module globals use module references so defining-module patches take effect.
Deferred relative imports resolve unavoidable orchestration dependencies, with
comments at each import. There is no production compatibility/shared namespace.
`tests/monitor_imports.py` is a test-only import adapter: each former script load
gets a UUID-named package instance (even when the old loader name repeats), and attribute patches route to the defining
module. It retains assertion text and isolates state/environment between loaders.
Do not change it to reload the canonical package: deferred imports would then see
another fixture's modules. Existing fake-bin fixtures copy the adjacent package.

## Next work (not started)
R3b: state machine, ladder as data, unified cluster reads and runner interface per
DESIGN. Auxiliary files (`decisions`, `timeouts`, `tier0`, `task_agents`,
`task_commands`, `continuation`, `plan_wakes`, `plan_commands`, `setup`) split the
large old sections without redesign. Preserve retained assertions and C1-C4.
Code map is a separately planned post-R3a action; it has not been run here.
R3c ports patch P later. Do not install/swap before Hunter's R4 gate.

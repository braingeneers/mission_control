# Handoff: nrp-monitor R3a cuts complete, package pending (2026-11-18)
**Plan:** nrpmon-rewrite R3a authorized; stop before R4 install. Implementation sub-agent relay.
**Worktree:** /Users/hunterschweiger/.t3/worktrees/mission_control/t3-5d6f3948-7a71276ff0751a9b; branch nrp-monitor-rewrite. Never edit main checkout.
**Commits:** C1 ce234a2 + e54710f; C2 fc77d32; C3 1d34054 + docs 2c8dc77; C4 50d2068. Register updated in relay commit.
**Checked:** C3 targeted 56 passed; C4 targeted 86 passed; default-off new test 1 passed; retained exact-marker tests 14 passed. No package exists yet.
**In flight:**
- Corrected clean baseline: exec session 18705, /tmp/nrp-r3a-original-result.txt. Archived 0f38bd1 scripts plus sibling memory_peak.py; command python -m pytest /tmp/nrp-r3a-original/skills/nrp-monitor/scripts/tests -q.
- Current full suite: exec session 36773, /tmp/nrp-r3a-after-cuts-result.txt; cwd skills/nrp-monitor/scripts, python -m pytest tests -q.
- Interpreter: /Users/hunterschweiger/miniconda3/bin/python3 (default python lacks pytest).
**Next:**
1. Inspect/await the two in-flight outputs. Flattened previous baseline is invalid for helper tests: 642 passed/1 skipped/2 missing-helper failures. Corrected run should settle comparison.
2. Fix any retained regressions from full suite; preserve every retained assertion. Only cut-specific removals allowed and register all of them.
3. Mechanical move to scripts/nrp_monitor per DESIGN §1, explicit imports, no shared namespace. Keep bodies/names; <=~800 lines/module (record exceptions). No R3b redesign or patch P.
4. Thin nrp-monitor entry; install.sh copies package beside it; fake-bin copy fixtures must copy package. Never run install outside existing temporary-HOME tests.
5. Port internal tests only imports/patch targets. Prove retained assertions unchanged (C3 mixed tests have approved cut runner fixture/expectation changes).
6. Full suite, CLI parse checks, module counts, LOG; commit and push only nrp-monitor-rewrite once suite passes. Never install/touch live ~/.local/push main.
**Gotchas:** C4 config is state config.json ladder.triage_judge (not agents.json); task fixture opts in so optional judge assertions survive.
C1 retained ChainError, state_lock, iso/ago, regex/heartbeat helpers. C2 retained plan_gpu_cover (GPU approval).
C3 removed local runner tests (6); generic setup/config/failover now use agy; no retained assertions dropped.
Seven more C1 tests removed from ExactChains/IndexedChains in test_s3_exact; retained pure/task tests unchanged.
Some stale CLI help still says Gemini CLI / thinking and historical docs mention chains/night code; clean only cut-related current guidance.
**Read first:** PLAN.md (R3a/register), LOG.md newest entry, DESIGN.md §1-2.
**Open questions:** none. Branch not pushed because full suite is still pending; honor pass-before-push rule.

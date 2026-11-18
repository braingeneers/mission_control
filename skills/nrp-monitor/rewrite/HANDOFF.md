# Handoff: nrp-monitor R3a partial implementation (2026-11-18)
**Plan:** nrpmon-rewrite, R3a authorized; stop before R4 install. User requested implementation sub-agent relay.
**Branch:** nrp-monitor-rewrite from 0f38bd1; C1 ce234a2, C2 fc77d32. No push or install.
**Verified:** script compiles. No package exists yet. Targeted cuts check: 33 passed in 45.53 s; no full-suite result yet.
**In flight:** clean original baseline copied to /tmp/nrp-r3a-baseline, pytest output /tmp/nrp-r3a-baseline-result.txt (exec session 78641).
Completed targeted corrected cuts check: scripts/tests/test_plans.py test_origin.py test_red_alert.py, output /tmp/nrp-r3a-cuts-result.txt (session 11455).
Earlier runs against the changing source (sessions 18125, 9973) are invalid; do not report their counts as baseline.
Existing interpreter /Users/hunterschweiger/miniconda3/bin/python3 has pytest; default tool shell python3 does not.
**Next:**
1. Inspect both output files; await running checks, fix retained-behavior regressions before further cuts.
2. Review C2 sidecar s3 cp removal (coupled to may_touch) and stale docstrings/skill docs mentioning night code/chains; keep scope within approved cuts.
3. Apply C3 local gemini CLI removal (keep agy) and C4 off-by-default ladder.triage_judge; one commit per cut. Update register with each SHA in subsequent commit.
4. Mechanical module move per DESIGN section 1; no deeper redesign. Use explicit module imports and preserve state/CLI behavior.
5. Installer must copy package beside entry point; tests often copy just the script to fake bin, so inspect fixture packaging carefully.
6. Port internal-test import/patch targets only; full test suite, CLI parse checks, module counts, LOG update, commit and push only nrp-monitor-rewrite when passing.
**Tests:** full removed-test names in PLAN register. User explicitly permits only cut-feature test removal; preserve retained part of mixed tests.
Mixed test test_next_add_refuses_outside_may_touch_and_outside_run became test_next_add_refuses_outside_run; only cut may_touch assertion removed.
**Gotchas:** plan_gpu_cover was inside night-code section but is retained GPU approval logic; restored in C2.
ChainError, load_chain_file, state_lock, iso/ago, regexes and heartbeat helpers were in chain sections but serve retained features.
**Read first:** PLAN.md, LOG.md top entry, DESIGN.md sections 1-2. Script read section-by-section only.
**Open questions:** none; continue approved work. Never touch live ~/.local paths, install, push main or merge patch P.

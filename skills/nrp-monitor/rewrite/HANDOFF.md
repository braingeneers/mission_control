# Handoff: nrp-monitor modular rewrite  (2026-11-18, R2 session)
**Plan and active steps:** PLAN.md (nrpmon-rewrite). R1 and R2 done; **stopped for Hunter** on DESIGN.md §4
(5 decisions). R3 is not approved yet.
**Where we are:** CENSUS.md (verified counts) and DESIGN.md (layout, cut list C1-C5, t71 problems U1-U9) are written.
1c7debc red-alert probe verified live. Nothing deleted or changed in code or state.
**In flight:** nothing.
**Next:**
1. Record Hunter's answers verbatim in PLAN.md (decisions 1-5).
2. If decision 3 = A: patch the current script for U1 (working-set sizing, NRP violation -> resize/restart for
   resumable stages, else coordinator wake with numbers), U3 (`task resize`/`task restart`), U5 (zero-node check),
   with tests; install; tell the t71 chat (c38c20f5).
3. Then R3 module by module per DESIGN.md §1; apply approved cuts first (C5 is state-dir only).
**Gotchas:** never read the 8.9k-line script whole; grep `^# ----` sections or delegate. Tests live in
scripts/tests (run from scripts/). Push to main, `git pull --ff-only` before committing. Install = scripts/install.sh.
gpu-long never logs: check before relying on it for U1.
**Read first:** PLAN.md, DESIGN.md §2-4, LOG.md top entry.
**Open questions for Hunter:** DESIGN.md §4, each with a recommendation.

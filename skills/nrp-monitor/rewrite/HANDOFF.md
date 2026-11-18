# Handoff: nrp-monitor modular rewrite  (2026-11-18, spike-tokenizer-scaling session)
**Plan and active steps:** rewrite/PLAN.md (nrpmon-rewrite); start R1. Approved R1-R2; stop for Hunter
after R2 with the cut list. Nothing is deleted before he agrees.
**Where we are:** red-alert fix landed and installed (1c7debc, 645 tests pass). Not yet verified on a live
scheduled pass: check monitor.log for "probe"/"RED ALERT" lines and that no Traceback appeared.
**In flight:** nothing from this workstream. The installed monitor runs on its own (launchd plist).
**Next:**
1. Confirm the 1c7debc probe ran cleanly in `~/.local/state/nrp-monitor/monitor.log`.
2. R1 census: delegate to a Sonnet agent (log + registries + grep of section headers, `grep -n '^# ----'
   scripts/nrp-monitor`); write rewrite/CENSUS.md.
3. R2: design the package (behavior as tables / strategies, one Task state machine, one cluster-read layer,
   one runner interface) and the cut list; give Hunter each cut with evidence, what breaks if wrong, and a
   recommendation.
**Gotchas:** never read the 8.7k-line script whole in the main thread; grep sections or delegate.
Repo rules: push to main, `git pull --ff-only` before committing, no checkout/stash/reset.
Install is a copy via scripts/install.sh; INSTALLED records the commit.
**Read first:** PLAN.md, LOG.md top entry, scripts/nrp-monitor section headers (grep above),
references/operations.md.
**Open questions for Hunter:** none until the R2 cut list.

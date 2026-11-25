# Handoff: nrp-monitor rewrite, post-swap  (2026-11-18 14:15, main session)
**Plan and active steps:** nrpmon-rewrite, PLAN.md. R4 swap DONE. Next R5 spiky-job check; R6 unapproved.
**Where we are:** rewrite is the installed monitor (`~/.local/bin/nrp_monitor/INSTALLED`, commit 1ee4f63) and on main. Post-swap fixes done and verified (see the four newest LOG entries): memory judged on the stricter of RSS/working set; account summary counts starting pods apart; band action counts only our account, waits through ramp-up (≤15 min), keeps coordinator sizing (`coordinator_sized`); `task stage --done-s3`. Docs (SKILL.md, references/utilization.md, tasks.md, nrp-cluster SKILL.md) match. Other threads send monitor problems here.
**In flight:** nothing running. Watch passes: `tail -50 ~/.local/state/nrp-monitor/monitor.log`, `cat ~/.local/state/nrp-monitor/launchd.err` (empty at 14:02).
**Next:**
1. Fix regressions as reported; cut features are in PLAN.md "Cut register". Rollback: LOG "R4 swap" entry.
2. Watch the next passes: no safety stop on pods younger than ramp-up; ft-official-units-region `region` and ft-disease-sizegroups `u96`/`u384` (marked coordinator_sized by hand) get a wake, not an auto-restart, if they flag.
3. R5 spiky-job check (PLAN.md).
**Open for Hunter:** none blocking. Option B (ask NRP support for a portal token to read NRP's own verdicts) not requested; recommend only if our flags and NRP's Violations page disagree in practice.
**Read first:** PLAN.md; newest LOG entry; `.code-summaries/_INDEX.md` for module map.

# Handoff: nrp-monitor rewrite, post-swap  (2026-11-18 12:15, main session)
**Plan and active steps:** nrpmon-rewrite, PLAN.md. R4 swap DONE (Hunter approved, newest LOG entry). Next R5 spiky-job check; R6 unapproved.
**Where we are:** the rewrite is the installed monitor (`~/.local/state/nrp-monitor/INSTALLED`, commit 7e1f9b6) and merged on main. Verified: CLI smoke, first launchd pass clean. Not yet verified: a full day of live passes.
**In flight:** watch live passes for regressions: `tail -50 ~/.local/state/nrp-monitor/monitor.log`, `cat ~/.local/state/nrp-monitor/launchd.err`. Code-map refresh of 9 stale summaries (`summaries.py check`).
**Done since swap:** policy read under launchd, chat-scoped session notice, one-line node summary (newest LOG entry).
**Open for Hunter:** memory measure gap vs NRP (rss vs working set): rec. Option A, flag on the stricter of both; B = ask NRP for a portal token. Evidence in newest LOG entry.
**Next:**
1. Tell other threads: the monitor was swapped to the modular package, same commands; send monitor problems to this workstream.
2. Fix regressions as reported; restore cut features from PLAN.md "Cut register" if needed. Rollback steps: newest LOG entry.
3. Separate issue for Hunter: launchd cannot read the shared utilization policy (TCC on ~/Desktop symlink); monitor uses built-in numbers.
4. R5 spiky-job check.
**Read first:** PLAN.md; newest LOG entry; `.code-summaries/_INDEX.md` for module map.

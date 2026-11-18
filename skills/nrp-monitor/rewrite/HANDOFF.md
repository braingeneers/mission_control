# Handoff: nrp-monitor rewrite, post-swap  (2026-11-18 13:10, main session)
**Plan and active steps:** nrpmon-rewrite, PLAN.md. R4 swap DONE. Next R5 spiky-job check; R6 unapproved.
**Where we are:** rewrite is the installed monitor (`~/.local/bin/nrp_monitor/INSTALLED`, commit 875bccd) and on main. Post-swap fixes done and verified live: policy read under launchd, chat-scoped session notice, one-line node summary, memory judged on stricter of rss/working set (two newest LOG entries). Other threads were told to send monitor problems here.
**In flight:** nothing running. Watch passes: `tail -50 ~/.local/state/nrp-monitor/monitor.log`, `cat ~/.local/state/nrp-monitor/launchd.err` (empty at 13:05).
**Next:**
1. Fix regressions as reported; cut features are in PLAN.md "Cut register". Rollback: LOG "R4 swap" entry.
2. Watch the first passes after 875bccd for memory band actions on cache-heavy pods (expected: resize or one "spiky" wake, not a resize loop).
3. R5 spiky-job check (PLAN.md).
**Open for Hunter:** none blocking. Option B (ask NRP support for a portal token so we read NRP's own verdicts instead of modeling them) is not requested; recommend only if our flags and NRP's Violations page disagree in practice.
**Read first:** PLAN.md; newest LOG entry; `.code-summaries/_INDEX.md` for module map.

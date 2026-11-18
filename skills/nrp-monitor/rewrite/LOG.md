# Log: nrp-monitor rewrite (newest first)

## 2026-11-18 — P utilization patch on main
- Added a separate utilization-actions section: budget-free resize/restart and stale-wake cancellation;
  working-set-first sizing (cgroup fallback, OOM minimum); NRP LOW/HIGH actions bypass review/ramp-up.
- Resumable stages resize/restart from measured CPU/memory; otherwise wake once
  with numbers, spiky warning and deadline. Stop only registered task Jobs after 30 minutes or at
  three namespace violators (default four-pod block threshold); logs/S3 retained, coordinator + owner.
- Zero-node required selector/affinity guard caches node reads per pass, fails open on read errors,
  routes `unschedulable` directly to coordinator. Watch-only failures now go coordinator-first.
- Validation: `python3 -m pytest tests -q`: 662 passed (7 existing deprecation warnings).
- Added `tests/test_util_actions.py`; adjusted red-alert, robustness, sizing, wake, ladder, origin and util-waiver assertions for
  intentional changes. Config: `nrp_violation_grace_minutes` (default 30). R3 must port these hooks.

## 2026-11-18 — R1 census + R2 design (stopped for Hunter)
- 1c7debc verified live: red-alert probe ran 08:52, passed, no new Traceback, launchd.err empty.
- R1 `CENSUS.md`: ~1,300 lines unused in 7 days (chains 754, night code 399, gemini CLI ~70, gpu-long ~100).
  on_done is ON (`on_done.enabled`), 90 continue-agent runs. Tier 1 judge: 518 runs, 0 closes, 38 unparseable.
  557 warnings: launchd cannot read ~/.claude utilization policy. One stopped chain -> 86 kubectl errors.
- Tests: 11 black-box files (fake bins on PATH), 23 load the script and call ~155 internals / patch ~20 globals.
- gpu-long is NOT cut: it is NRP's 3 h GPU rule (utilization) but never logged; find out why in R3.
- t71 chat (c38c20f5) problem list U1-U9 folded into `DESIGN.md` §3; Hunter: utilization first, comparison second.
- R2 `DESIGN.md`: module layout, cut list C1-C5, 5 decisions for Hunter.

## 2026-11-18 — starting point
- Script is 8,722 lines, 376 functions, 28 commits since 2026-11-11; grew one incident rule at a time.
- Rough sections: agent runners ~1,000; failure ladder (Tier 0 rules, judge, fixer, deputy, coordinator
  wake) ~1,700; plans on_done + night code ~1,150; tasks/handoff/manifests/S3 ~1,000; chains ~800
  (overlaps tasks); digest, push, nrp-task, setup, validation, cluster reads (two sections) the rest.
- Suspected dead or duplicate: chains, night code (flag default OFF), duplicated cluster reads. Unverified.
- 1c7debc added account RED ALERT (dry-run admission probe every ~10 min, global submit hold, owner wakes,
  red_alert.json) and NRP-floor reviews that cannot end in "no change". Must survive the rewrite;
  tests/test_red_alert.py. Known gaps: owners matched only via task stage Jobs; re-alerts within 1 h keep
  the same id (no re-wake).

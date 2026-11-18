# Log: nrp-monitor rewrite (newest first)

## 2026-11-18 — R3a package move
- Commits: baseline `88ef48f` (includes registered C1-C4); package implementation `512a77f`, fixture targets `6805600`, fresh test-package identity `9782a7b`; documentation follows it on the same branch.
- AST splitter `/tmp/r3a_split.py` assigned original source nodes by DESIGN section and helper overrides; all 350 functions/classes accounted for. Bodies normalize identically except the sibling `nrp-util-check` path and the two retained C2 repairs below.
- Explicit module-reference imports preserve defining-module monkeypatch behavior. Cycle scan found mutual orchestration edges; commented local imports remove eager cycles. Compile + symtable undefined-name checks are clean; all 36 CLI help paths parse.
- Thin real-path entry point, adjacent package copy in installer, fake-bin package copy fixture. Test-only isolated package import adapter routes old test patches to defining modules; no production compatibility namespace.
- Baseline `88ef48f`: 293 passed, 1 failed (stopped at first failure, 134.67 s). Initial worktree baseline was invalidated by the entry-point edit and discarded; this comparison uses an immutable archive including sibling memory_peak.py. The retained failure was C2 accidentally removing bounded completion `s3 cp` and `may_touch` parsing. Restored their original scope/size guards; no night authoring restored. Plan-group regression check: 22 passed.
- Remaining fixture repairs: stale C1 `chain_names` prepass patch removed (its failed setup leaked a subprocess mock); `WAKE_MAX_TRIES` source-reading helper follows state.py. No assertions changed. Targeted repair verification: 19 passed. A subsequent full run reached 585 passed / 2 webhook fixture failures; UUID package identities repaired repeated loader-name reuse, with all 5 webhook tests passing.
- Final full suite: 587 passed, 7 warnings in 234.08s (0:03:54). Outputs `/tmp/r3a-full-88ef48f.txt`, `/tmp/r3a-final.txt`.
- Test changes: `test_agent_runners.py`, `test_followup_tiers.py`, `test_install.py`, `test_ladder.py`, `test_origin.py`, `test_plans.py`, `test_s3_exact.py`, `test_s3_incluster.py`, `test_tasks.py`, `test_v3_tier0.py`, `test_webhooks.py`; added import helper `monitor_imports.py`. Only import/loader/patch-routing and fixture/helper changes (including the constant-source path); no changed assertion lines (`git diff -U0 88ef48f ... | rg '^[+-][[:space:]]*(assert\b|self\.assert)'` empty), all retained assertion ASTs identical.
- `wc -l` per module (no >800-line exception):
  - `__init__.py`: 1
  - `agents.py`: 566
  - `cli.py`: 406
  - `cluster.py`: 332
  - `config.py`: 130
  - `continuation.py`: 194
  - `decisions.py`: 248
  - `ladder.py`: 485
  - `legacy.py`: 411
  - `notify.py`: 278
  - `nrp_task.py`: 332
  - `plan_commands.py`: 161
  - `plan_wakes.py`: 315
  - `plans.py`: 398
  - `red_alert.py`: 146
  - `s3.py`: 224
  - `setup.py`: 254
  - `sizing.py`: 135
  - `state.py`: 700
  - `task/__init__.py`: 1
  - `task/model.py`: 41
  - `task/pass_.py`: 483
  - `task/registry.py`: 693
  - `task_agents.py`: 151
  - `task_commands.py`: 354
  - `tier0.py`: 317
  - `timeouts.py`: 154
  - `util.py`: 336
  - `wake.py`: 775
- No live install/state changes, main push, R3b implementation or P port. R3b starts from HANDOFF.md; package code map remains a separately planned follow-up.

## 2026-11-18 — R3a cuts continued, mechanical move still pending
- C3 `1d34054`, docs/register `2c8dc77`: removed local Gemini CLI, policy/settings and setup selection; agy retained. Generic config/setup/failover tests use agy in place of removed runner; only local-runner tests and valid-thinking loop removed (full register). C2 stale code-authoring / sidecar-copy help corrected in the same script edit.
- C4 `50d2068`: task failure judge requires config.json `ladder.triage_judge: true`, default false. Existing task fixture explicitly opts in; robustness role test opts in. No existing assertions changed for C4. Added one end-to-end default-off test (passed).
- C1 follow-up `e54710f`: full-suite collection found test_s3_exact still imported deleted test_chains. Removed its two chain-only classes (7 tests); all names in register. Retained exact-marker tests passed (14).
- Checks: C3 targeted tiers/followups/robustness 56 passed; C4 tasks/ladder/robustness 86 passed (before new default-off test); new default-off 1 passed. diff --check clean.
- Original baseline /tmp/nrp-r3a-baseline finished 642 passed, 1 skipped, 2 failed in 427.71s. Both failures are missing nrp-cluster/references/memory_peak.py due to flattened temp-copy layout, not monitor regressions. Corrected immutable baseline archived from 0f38bd1, including sibling helper, running in /tmp/nrp-r3a-original (output below).
- No package move/import port/installer edit yet. No install/live state access, main changes, push or P port. Full suite must pass before branch push.

## 2026-11-18 — R3a partial implementation relay (not ready to install or push)
- Branch `nrp-monitor-rewrite`, based on `0f38bd1`; C1 `ce234a2`, C2 `fc77d32`.
- C1 removed chain execution/commands and cut-specific tests (full names in PLAN cut register); shared helpers retained.
- C2 removed overnight code authoring, ignored may_touch, removed authoring prompt instructions; shared plan_gpu_cover restored after targeted checks exposed its accidental removal.
- Hunter authorized removal/adaptation of cut-specific tests; verbatim clarification appended to PLAN.
- No package modules yet. C3/C4, mechanical modularization, import/patch-target port, installer packaging, final full validation and push remain.
- Baseline: default system Python has no pytest; existing Miniconda Python supports pytest. Initial runs overlapped editing and are invalid baselines. An isolated original scripts copy under /tmp/nrp-r3a-baseline is running the clean baseline, output /tmp/nrp-r3a-baseline-result.txt; result: 642 passed, 1 skipped, 2 failed solely because the copy omitted sibling nrp-cluster/references/memory_peak.py. Both failed helper tests rerun from the real repository passed (2 passed in 0.11 s); this is a composite baseline of 644 passed / 1 skipped, not a single clean full-suite pass.
- Targeted C1/C2 checks initially failed due to missing plan_gpu_cover; corrected rerun passed 33 tests in 45.53 s (test_plans, test_origin, test_red_alert); output /tmp/nrp-r3a-cuts-result.txt. Full-suite results remain pending.
- No install or live-state access; no push. Tests invoke installer only in their existing temporary-HOME fixtures.

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

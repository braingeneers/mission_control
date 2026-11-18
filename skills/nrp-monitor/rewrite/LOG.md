# Log: nrp-monitor rewrite (newest first)

## 2026-11-18 — memory judged on the stricter of working set and RSS (main session)
- Hunter (verbatim, on the rss/working-set gap): "ok we should error on the side of caution for this then" = Option A.
- 875bccd: nrp-util-check also reads container_memory_rss (10m mean); a pod is outside a memory band (and under the lab floor) if either measure is; the flag line adds `rss X.XGi N%`. util.py spiky check uses the lower measure so a cache-heavy pod is not resized to the same size repeatedly. Tests: test_memory_band_uses_the_stricter_of_working_set_and_rss, test_spiky_check_reads_the_lower_rss; suite 669 passed. Installed 13:05; live run OK.
- Live evidence: 12 of 135 braingeneers pods had RSS < 2/3 of working set (lowest 0.15). First live run: account 5 of 112 running pods outside NRP bands (block threshold 4); the monitor's band action handles them.

## 2026-11-18 — post-swap fixes (main session)
- 7944723: launchd now reads the utilization policy (install.sh copies it to the state dir; an unreadable file falls through). Verified: 0 policy warnings in the 12:47 pass (was every pass since 2026-11-10).
- NRP violations research (Sonnet, read-only): thresholds match NRP's policy page (GPU >40%, CPU 20-200%, RAM 20-150%, 1 CPU/2GB exempt; our local override already has cpu_band [0.2, 2.0]). NRP's per-pod verdicts come from https://portal.nrp.ai/rpc `user.GetUserInfo` (Violations page nrp.ai/userinfo), browser CILogon cookie only; no Thanos metric or k8s label carries them. NRP's namespace recording rules use container_memory_rss; we use working set (higher), so NRP may flag memory LOW where we don't (inference). Options to Hunter: A flag on the stricter of rss/working set (recommended); B ask NRP support for a portal token. Undecided.
- c440aae: session-start coordinator notice scoped to the current chat (T3CODE_THREAD_ID / session id vs origin link); unknown chat gets a count only. Request from Hunter via the t71 chat. Display only.
- f49fe30: quiet status shows excluded nodes as one count line (full list in `status` and digest). "Need the owner" stays global (Hunter agreed). Suite 667 passed.

## 2026-11-18 — R4 swap: rewrite installed and merged (main session)
- Hunter (verbatim, on the "nothing installed until you say so" line): "wdym installed? shouldnt this be the same now and we use the new version? if it breaks we just fix it". Then: "once you have it fixed so agents can use we will tell the other threads what was done and if there are problems to send your way for fixing". Day shadow loop stopped after pass 1 (no longer meaningful).
- Backup before swap: `~/.local/share/nrp-monitor-backup/bin-pre-rewrite-20261118T1201/` (old bin files + plist) and `state-pre-rewrite-20261118T1201.tgz` (state without logs). Rollback: bootout label, copy bin files back to ~/.local/bin, trash ~/.local/bin/nrp_monitor, restore plist, bootstrap.
- Swap 12:01: bootout, pass lock free, `install.sh --launchd` from branch 7e1f9b6. CLI smoke (help/task list/status/digest/tool) OK. First launchd pass 12:07: utilization observations, pod failure notices, triage/fix agents dispatched and returned; launchd.err empty.
- The `utilization-policy.json ... Operation not permitted` warning predates the swap (575 occurrences since 2026-11-10): launchd cannot read ~/.claude/skills (symlinked into ~/Desktop, TCC), so the monitor uses built-in numbers. Separate issue.
- Merged branch into main; code-map indexes unioned, 9 summaries marked stale for a Gemini refresh.

## 2026-11-18 — R4 comparator verified; in-flight agent match; day loop started (main session)
- Reviewed aab633d: shadow-only changes (decision journal, dir_fd-resolved write gate, compare.py). Full suite 664 passed. Live pass 11:52:21 (`runs/2026-11-18T115221.md`, private pass-7yig6zi0): matched 2 / unexplained 1 / pending 12 / unknown 10; zero filesystem blocks.
- The unexplained row (20260720 ws17-64): installed started a fix agent at 11:50:42 (monitor.log line 23592) whose submit landed 11:52:30; the state copy was taken while that agent ran, so the shadow repeated the same fix_agent decision and was compared to the later submit. Comparator gap, not a rewrite bug. judge() now matches a shadow agent decision to the same installed agent decision made before the snapshot when no other decision came between (test_agent_in_flight_at_snapshot_matches). 61 shadow tests pass.
- Day loop: `/private/tmp/claude-501/nrp-shadow/loop.sh`, PID in `loop.pid`, log `loop.log`; 96 passes x 15 min from ~11:58 local, ends ~2026-11-19 12:00.

## 2026-11-18 — R4 first-decision comparator and pending/day reports
- Compare first task/stage decisions, not terminal shadow states; task suppression cuts off later events as provisional. Read installed launchd interval (300s), allow two intervals after completion, persist/re-judge pending results under private tmp; missing evidence expires unknown. `--day-summary SINCE` aggregates persisted per-run verdicts, every unexplained row/evidence and route counts. Reports stay gitignored under shadow/runs/.
- Four old filesystem blocks are inferred isolated submit-temp cleanup false positives: relative job.json unlink resolved against cwd instead of dir_fd. Checked local reproduction recovered cleanup without changing the decision. Resolve directory FDs; external writes remain blocked with route/path-kind/caller labels and private targets, and count as suppression. No new redirect or production source writes; details in shadow/AUDIT.md.
- Final pass 11:47:31–11:48:35 local, exit 0: matched 2 / unexplained 0 / pending 15 / unknown 12; zero filesystem blocks/global errors (`shadow/runs/2026-11-18T114731.md`, private pass-_8g7_fbs). Re-judged at 11:51:43: matched 7 / unexplained 0 / pending 10 / unknown 12. No suspected rewrite bug identified; pending/unknown are coverage limits, not equivalence. Day-summary checked; later installed evidence resolved pending rows. Four earlier-development unexplained rows retained: ft-disease u128 lacked task scope in the old journal (now fixed); three ws17–64 wait/failure rows reflect a later failed attempt-3 observation (installed 11:50:41, line 23591). Their snapshots remained running; the final shadow observed that failure and matched it. Comparison gaps, no suspected rewrite bug.
- Validation: 664 passed, 7 existing warnings, 242.71s (`/tmp/r4-suite.txt`, required scripts-directory pytest command); focused boundary/comparator cases 60 passed. Main next: run about every 15 minutes for a day, summarize/report to Hunter, stop before install. No push, install, scheduler or installed monitor execution.

## 2026-11-18 — R4 isolated shadow, one pass (nrp-monitor-rewrite)
- Added explicit `run --shadow`: 14 semantic gates (agent dispatch/backend/run + stored aliases; push/Slack/banner; wakes/webhooks/handoff writes; postcheck; admission probe; S3 Job fallback), plus kubectl/process, HTTP and filesystem allowlists. Kubectl permits only get/describe/logs/top; other verbs record and raise, including server dry-run creates. Audited reachability and limitations: `shadow/AUDIT.md`. Normal decision path writes only an isolated copy; no installation, scheduling, push or live mutation.
- Tests: 643 passed, 7 existing warnings, 262.48s (`/tmp/r4-suite.txt`; required miniconda pytest command); 39 shadow boundary cases use no real cluster/network. Earlier intermediate suite: 639 passed/7 existing warnings. Ruff F401/F821 and diff whitespace clean; runner help and compilation checked. Retained test assertions unchanged.
- Exactly one live shadow pass, 11:22:21–11:23:05 local, exit zero, private snapshot `/private/tmp/claude-501/nrp-shadow/pass-afbwh5g0`. Installed monitor was not executed: comparison reads its copied monitor.log and task events for the preceding 30-minute window. Snapshot copy is sequential, not atomic.
- `shadow/2026-11-18-single-pass.md`: 14 live tasks / 23 stage rows; 10 expected shadow-suppression differences, 3 unexplained, 4 unchanged with recent evidence, 6 unknown recent decisions. Counts are stage rows; task-scoped attempted actions repeat across their stages. No cut-driven difference asserted. Suppressed: 12 agent dispatches, 24 AWS subprocesses, one fallback Job, one delete, one push, one webhook-processing call.
- Unexplained: 20260720 ws17–64, 20260720 ws65–128 and loop1 ws65–128 stages newly failed with group-bound parsing ValueError. Newer live observations plausibly explain stage failure (inferred, not proven); skipped agents explain subsequent coordinator routing only. Deliberately kept these unexplained instead of counting all agent-associated changes as expected. Agent results/postchecks, admission and S3 are unknown; legacy check_pods stopped at the forbidden delete boundary, so zero deletes and incomplete coverage. No equality claim from exit zero.
- `shadow/run.py` refreshes a fresh private state copy, relocates state references, runs one gated pass and saves a timestamped sanitized report per invocation; no loops/scheduler. `scripts/nrp_monitor/shadow.py` owns the gates. Final post-pass changes preserve agent return contracts and strengthen comparison classification/tests; no second shadow pass performed. HANDOFF.md overwritten: run the shadow over a day, then report to Hunter; stop before install.

## 2026-11-18 — ownership consolidation before R4 (nrp-monitor-rewrite)
- Item 1 `2b4d996`: sizing owns Thanos memory/CPU peaks, memory-low evidence, single-container saved-peak fallback and repeated CPU request calculation. OOM recovery and utilization sizing retain their distinct policies. Full suite: 604 passed, 7 existing warnings, 256.57s (`/tmp/condense-1.txt`).
- Item 2 `2c1f4d0`: stage_jobs owns do_submit, utilization_restart, save_task_logs, resource_values/resource_template and propagate_resources. Shared delete_stage_job saves diagnostics before replacement/safety-stop deletion; callers retain errors, guards and state transitions. Full suite: 604 passed, 7 warnings, 269.18s (`/tmp/condense-2.txt`).
- Item 3 `752e259`: cli_args owns monitor/scoped-tool argparse construction, shared origin-edit/resource option registration and handler bindings; cli.main dispatches the selected handler. Scoped positional dispatch and authorization stay in nrp_task; monitor and scoped restart retain their different accepted options. Full suite: 604 passed, 7 warnings, 255.56s (`/tmp/condense-3.txt`).
- Item 5 `846566c`: state.json_txn owns locked load/modify/write for task_txn, plan_txn and notification claim/rearm. Task completion/terminal hooks, literal-False vetoes, plan callbacks that do not veto, defaults, atomic file formats and permissions stay unchanged. Task wake/outbox updates inherit this through task_txn. Multi-file group/fallback wake locks remain: they coordinate several records, not duplicated single-file transactions. Full suite: 604 passed, 7 warnings, 233.55s (`/tmp/condense-5.txt`).
- Test edits, exhaustive: tests/monitor_imports.py owner targets only. Item 1: thanos_peak_mem tier0 -> sizing; memory_low_evidence util -> sizing. Item 2: save_task_logs and do_submit task.pass_ -> stage_jobs; resource_values, resource_template and propagate_resources sizing -> stage_jobs; utilization_restart util -> stage_jobs. Items 3/5: none. No assertions changed. An initial misplaced repository-root pytest invocation produced 35 passed/1 unrelated terminal-input test failure; the corrected package run passed (its output above excludes the stray trailing root-test output).
- Skips: item 4 (agent prompt/run/report) explicitly excluded; agents.py, task_agents.py and continuation.py untouched. No requested item otherwise skipped. Distinct asynchronous cleanup/best-effort GPU deletion and multi-file wake transactions were not forced into replacement/single-file policies. Fresh single-Job action guards, direct s3.incluster_job kubectl-create and RUNNER_EXEC/exec_* targets retained.
- Code map `bc458c0`: refreshed 16 changed/new files plus three selected consumers following summarize-codebase; generated static consumer links also updated. Freshness check `/tmp/condense-map-check.json`: zero stale/missing/deleted package files; 87 existing unrelated repository gaps remain outside scope. Annotation work: `/tmp/condense-code-map`.
- Package line counts, same mutually exclusive method as previous entry (all scripts/nrp_monitor/**/*.py; AST import/docstring spans, whole-line comment, blank, remaining code): fa07454 before 8,855 total / 577 imports / 310 docstring / 138 comment / 1,040 blank / 6,790 code; after 8,922 / 580 / 326 / 138 / 1,078 / 6,800. Explicit ownership/helpers add 67 total lines; no line-saving claim. Measurement helper `/tmp/condense-measure.py`.
- Final checks: Ruff F401/F821 clean, eager import graph has no cycles, git diff --check clean. Each item committed only after its full package suite passed. No push, install, live state/task operation or R4 run. Next is the existing R4 shadow preparation and day comparison; installation remains a separate Hunter stop.

## 2026-11-18 — R3b complete and R3c P port (nrp-monitor-rewrite)
- R3b commits: `de922b0` pass snapshots + fresh action guards (587 passed, 235.34s); `db5bb69` BACKENDS/Result runner interface (587 passed, 235.07s); `5d4debc` unused-import cleanup (587 passed, 275.44s). R3c commit: `f21d572`; final full-suite result: 604 passed, 7 existing warnings (366.64s).
- Piece-3 failure was the fake cluster's inconsistent Pending representation: batched JSON reports `active=1`, while single-Job jsonpath reports no active count. Kept fresh authoritative `cluster.job_state` for action/waiver guards; pass-wide scans use `jobs_in` and per-Job pod snapshots. Nested-pass reuse, mutation invalidation and freshness outside a pass were checked separately. No test assertions changed in R3b.
- Piece 4 applied `r3b/piece4-agents-backends.py`: claude/codex/agy backend rows, one executor, tuple-compatible `Result` from dispatch. Preserved RUNNER_EXEC/exec_* patch targets and fallback ordering. The legacy direct subprocess create in `s3.incluster_job` remains (its fake contract pins it).
- Condensation removed 378 unused imports (including redundant local imports). Standard-library monkeypatch targets now belong to the test-only import adapter rather than unused production imports. Removed detached scratch worktree `/private/tmp/claude-501/p1` with `git worktree remove`.
- R3c ports `bdb03a4`: working-set-first sizing with cgroup fallback/OOM floor; bounded NRP actions and per-container sizing; budget-free restart via `transition(..., "release")`; zero-node checks in sizing; CLI/tool hooks; watch-only coordinator routing via the existing guard table. P's 17 new cases passed separately. Ported P's intentional test changes verbatim; only the adapter's defining-module targets are additional test edits. No additional assertion changes or test cuts.
- Main audit: `git fetch origin`, remote main confirmed `3473081`; `git log 0f38bd1..origin/main -- skills/nrp-monitor` contains P plus `85fb5fc`, `8a71990`, `3473081` (handoffs only). Main history is merged; its obsolete handoffs are superseded by the R4 handoff. P references are retained.
- Test inventory: AST count including parameterization is main 662 vs rewrite 604, a net 58 approved cut cases. There are 60 missing named definitions (all in the Cut register), offset by the retained mixed C2 test's rename and the explicit C4 optional-judge test. The only assertion differences against main outside P are the already approved C3 runner adaptations in test_tiers.py. Audit output: `/tmp/r3-P-assertions.txt`.
- Package line counts (all `scripts/nrp_monitor/**/*.py`, mutually exclusive categories: AST import/docstring spans, then whole-line comments, blank, remaining code): supplied starting worktree 8,998 total / 927 imports / 305 docstring / 136 comment / 1,020 blank / 6,610 code; committed `7df136a` independently measures 8,986 / 949 / 303 / 134 / 1,008 / 6,592. After piece 4: 8,977 / 891 / 307 / 138 / 1,033 / 6,608; after cleanup: 8,636 / 550 / 307 / 138 / 1,033 / 6,608; final P port: 8,855 / 577 / 310 / 138 / 1,040 / 6,790. The starting supplied count includes uncommitted piece-3 work; the two baselines are deliberately distinguished. Measurement outputs: `/tmp/r3-{piece4,condense,final}-measure.json`.
- Final checks: all four new P functions match main after AST normalization of module references and the restart transition; Ruff F401/F821 clean; no eager import cycles; `git diff --check` clean. Full suite logs: `/tmp/r3-suite.txt`, `/tmp/r3-piece4-suite.txt`, `/tmp/r3-condense-suite.txt`, `/tmp/r3-P-suite.txt` (standard miniconda Python, pytest `-q -p no:cacheprovider`).
- Five largest remaining duplication opportunities (observed, not implemented), ranked by repeated responsibility: (1) memory/CPU evidence and sizing fallback across util, tier0 and sizing; (2) manifest resource edits, diagnostics, deletion and replacement across do_submit, utilization_restart and resource propagation; (3) argparse registration/dispatch across cli, nrp_task and task_commands; (4) agent prompt/run/report handling across task_agents, continuation and legacy followups; (5) locked JSON load/modify/write patterns across task, plan and notification/wake state.
- R4 shadow behavior remains unverified. No installation, service operation or live task mutation was performed; the installed monitor remains outside this workstream. Stop for Hunter before installation, as PLAN.md requires.

## 2026-11-18 — R3b pieces 1-2 (relay; pieces 3-4 pending)
- `316f168` task state machine; `b8bcff9` failure ladder as data. Each verified alone in a clean scratch worktree: 587 passed (piece 1 236 s, piece 2 263 s).
- Package lines 9021 (4e1a038) -> 8986 (b8bcff9). handle_failure 112 -> 17 lines; its guards/tiers are a 172-line LADDER section.
- No test files changed. Piece 3 (cluster snapshot) is uncommitted with 1 failing test; piece 4 (agent BACKENDS) is a drafted script. See HANDOFF.md.

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

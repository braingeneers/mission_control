# Plan: nrp-monitor modular rewrite (id: nrpmon-rewrite)

**Central question:** can nrp-monitor keep every behavior people rely on while becoming small, modular
code that one agent can hold in context?

**Hunter's decisions (verbatim, 2026-11-18):**
- "I definitely want it to be robust but that is so much context that I am sure we can have the same
  functionality but modular and condensed"
- "ideally when possible make it modularized where this feels like a behemoth basically a bunch of if,
  else statements basically (not actually but as an analogy)"
- Approved the order: red-alert fix first (done, 1c7debc), then this cleanup, then the spiky-job check.

**Approval:** R1-R2 done 2026-11-18 (`CENSUS.md`, `DESIGN.md`). Hunter approved the DESIGN.md §4 answers below and
"start on the refactor branch": R3 approved on branch `nrp-monitor-rewrite`; utilization patch (P) approved on main.
**Stop for Hunter before the swap** (R4 install of the new package) and before R6.

**Hunter's answers to DESIGN.md §4 (verbatim, 2026-11-18):**
- Design: "great and we should implement the code map skill for this repo so agents can find things in the modules easier as well"
- 1 cuts: "ok makes sense but lets keep a list of things we cut so that if we run into a problem with the monitor we can start adding things back in if needed"
- 2 tests: "lets go with your rec" (option B: only import/patch-target lines move)
- 3 utilization: "sounds good. if you wnat to have a subagent work on the patch while we start on the refactor branch and switch over later so we can work in parallel that could make sense."
- 4 watch-only: "yes that makes sense. I am often asleep or doing something else so the coordinator should deal with it. if there is a problem that absolutely needs me and is a problem with resources we should never leave jobs hanging that could get us banned"
- 5 Workflows stage: "not really sure what this meansn" (explained in chat)

**Hunter's answers after R3 (verbatim, 2026-11-18):**
- Condense: "I mean if we run tests to make sure it is working then we can shrink and if problems come up we can fix them. I think part of the size being a problem was that it was one giant behemoth, so it being more modular will allow agents to find and fix things a lot more quickly via the code map, which you should have set up now. I will leave it to your judgement of more importantly than overall size is making it easier for agents to find and fix things while being robust."
- Workflows stage type: R6, after the swap (picked the recommended option).
- Repo-wide code map: "Yes, in background".
- My choice under that delegation: condense items 1, 2, 3, 5 (one owner module per responsibility), skip 4; then R4 shadow on the final code.

**My choices (not Hunter's):** violation grace = 30 min (config key) before the monitor stops a violating Job itself;
it also stops at once when the namespace reaches `account_block_after_violating_pods` - 1 violating pods. Coding
children run on codex gpt-6.1-sol (Hunter's Sol-for-coding preference). **Stop for Hunter after R2** (cut list); no deletion before he agrees.

## Steps
- **R1 Usage census.** From `~/.local/state/nrp-monitor/monitor.log` (last 7+ days), task/chain
  registries and state files: which sections actually ran (chains, night code, on_done, gemini runner,
  each ladder tier, setup). Output: `rewrite/CENSUS.md`, one row per section (lines, calls seen, last use).
- **R2 Design + cut list.** Module layout and the list of what to cut/archive, each with evidence and what
  breaks if wrong. Done when Hunter approves it.
  Design goals: behavior as data, not branches. Ladder tiers, failure classes and rules as tables /
  small strategy objects with one dispatch loop; one `Task` state machine with explicit transitions;
  one cluster-read layer (today split across two sections); one agent-runner interface for
  Claude/Codex/Gemini. Python package beside the script (e.g. `nrp_monitor/`), thin CLI entry point.
- **R3 Rewrite** module by module behind the existing tests (645 pass at 1c7debc); tests are the
  contract. Same CLI, same state file formats (or a one-time migration), same install.sh.
- **P Utilization patch (main, parallel to R3)**: U1 working-set sizing + violation actions (resize/restart
  resumable, else coordinator, stop after grace), U3 `task resize`/`task restart`, U5 zero-node check, U9 watch-only
  to coordinator. Own section in the script + `tests/test_util_actions.py`; R3 ports it.
- **R3a** cuts C1-C4, package scaffold, mechanical move, tests ported (option B). **R3b** state machine, ladder as
  data, one cluster layer, one runner (Opus-level design work). **R3c** port patch P from main.
- **Code map**: after R3a, run `summarize-codebase` on `scripts/nrp_monitor/` (Gemini bulk delegate), refresh after R3b/c.
- **R4 Shadow run** next to the installed script (read-only / dry) for a day; diff decisions; then swap.
- **R5 Spiky-job check** at profile time (peak vs mean memory) in the new sizing module.
- **R6 (proposed, not approved) Workflows stage type** (t71 U7): poll Workflows runs as a task stage.

## Cut register (restore from here if the monitor misses something)
Restore: `git show edd3af7:skills/nrp-monitor/scripts/nrp-monitor` has every cut section intact (line ranges from
`CENSUS.md`). Add a row when a cut lands, with the commit that removed it.

| Cut | What it did | Lines at edd3af7 | Removed in | Restore note |
|---|---|---|---|---|
| C1 chains | model-free multi-step Job pipelines (`chain add/validate/...`, `process_chains`) | 1605-1886, 2160-2432, 8079-8277 + tests/test_chains.py | ce234a2 | state archived to `S/backup/chains-20261118/`. Additional C1 removals (`e54710f`): test_s3_exact.py::IndexedChains::test_chain_partial_indexed_job_waits_without_deleting; test_s3_exact.py::ExactChains::test_DONE_absent_with_DONE_dot_1_present_does_not_complete_and_keeps_the_job; test_s3_exact.py::ExactChains::test_DONE_dot_1_is_not_satisfied_by_DONE_dot_10; test_s3_exact.py::ExactChains::test_complete_marker_completes_and_deletes_the_job; test_s3_exact.py::ExactChains::test_access_denied_and_network_and_garbage_never_count_as_success; test_s3_exact.py::ExactChains::test_persistent_access_error_stops_after_five_passes_and_keeps_the_job; test_s3_exact.py::ExactChains::test_chain_add_refuses_prefix_style_done_s3. Removed tests: test_chains.py::test_dag_success (C1); test_chains.py::test_failure_stops_no_retry_then_resume (C1); test_chains.py::test_resume_skip (C1); test_chains.py::test_missing_s3_output_stops_and_keeps_job (C1); test_chains.py::test_s3_tool_error_is_retried_not_fatal (C1); test_chains.py::test_manual_gate_then_resume (C1); test_chains.py::test_crash_in_submitting_adopt_and_fail (C1); test_chains.py::test_submit_command_failure (C1); test_chains.py::test_job_cap (C1); test_chains.py::test_default_cap_is_the_shared_400_not_40 (C1); test_chains.py::test_cap_comes_from_the_shared_policy (C1); test_chains.py::test_local_override_lowers_the_cap (C1); test_chains.py::test_local_override_cannot_raise_the_cap (C1); test_chains.py::test_env_can_lower_the_cap_further (C1); test_chains.py::test_lock_held_means_noop (C1); test_chains.py::test_simultaneous_passes_submit_once (C1); test_chains.py::test_wait_codes_and_stall (C1); test_chains.py::test_wait_is_woken_by_run (C1); test_chains.py::test_deadline_overrun (C1); test_chains.py::test_adopt_existing_running_and_done_steps (C1); test_chains.py::test_on_finish_agent_once (C1); test_chains.py::test_kubectl_down_changes_nothing (C1); test_chains.py::test_heartbeat_and_status (C1); test_chains.py::test_show_list (C1); test_chains.py::test_cwd_under_desktop_refused (C1); test_chains.py::test_validation_problems (C1); test_chains.py::test_duplicate_name_and_job_refused (C1); test_chains.py::test_spec_copied_into_state (C1); test_chains.py::test_dry_run_strips_apply_and_never_applies (C1); test_chains.py::test_resume_size_refused_and_copied (C1); test_chains.py::test_existing_job_check_notify_only (C1); test_chains.py::test_existing_pod_path_dry_run (C1); test_chains.py::test_strike_one_oversized_then_strike_two_delete (C1); test_chains.py::test_account_alarm_needs_two_high_passes (C1); test_chains.py::test_strike_two_waits_for_next_pass (C1); test_chains.py::test_strike_resets_when_not_flagged (C1); test_chains.py::test_strike_two_kept_is_loud (C1); test_chains.py::test_resize_note_reaches_registered_resume (C1); test_chains.py::test_followup_gets_read_only_s3 (C1); test_chains.py::test_s3_read_helper_refuses_writes (C1); test_chains.py::test_add_during_pass_not_lost (C1); test_origin.py::test_chain_origin_add_show_backfill_and_stop_alert (C1) |
| C2 night code | continue agent writes code overnight in a plan's `may_touch` paths | 6959-7357 | fc77d32 | `may_touch` no longer authorizes night code. Its existing bounded S3 completion-copy scope is retained (R3a package move repaired the accidental removal). Removed tests: test_plans.py::test_night_code_end_to_end (C2); test_plans.py::test_night_code_gates (C2); test_plans.py::test_next_add_refuses_manifest_without_shipped_sha_and_wrong_name (C2); test_plans.py::test_no_code_repo_or_no_scope_means_no_code (C2). Mixed test `test_plans.py::test_next_add_refuses_outside_may_touch_and_outside_run` retains the closed-run gate as `test_next_add_refuses_outside_run` |
| C3 local gemini CLI | `exec_gemini` runner + gemini policy/settings | ~918-1028 | 1d34054 | Gemini still runs via `agy`. Removed C3 tests: test_tiers.py::GeminiRunner::test_argv_is_headless_json_default_approval_with_an_admin_policy_and_the_alias; test_tiers.py::GeminiRunner::test_policy_denies_everything_then_allows_only_the_allowlist_and_never_edits; test_tiers.py::GeminiRunner::test_thinking_budget_and_no_thinking; test_tiers.py::GeminiRunner::test_json_mode_wraps_the_answer_like_the_other_runners; test_tiers.py::GeminiRunner::test_only_the_triage_tier_may_run_on_gemini; test_tiers.py::GeminiRunner::test_limit_and_auth_are_reported_as_such_but_a_bad_answer_is_not. Mixed setup/config/failover tests retain their generic coverage using agy instead of the removed local CLI; removed valid-thinking-setting loop (C3). |
| C4 Tier 1 judge default | read-only triage before the fixer; 518 runs / 0 closes | 4962-5196 | 50d2068 | set `ladder.triage_judge: true` in state config.json. Existing ladder-test fixtures explicitly enable the optional judge; no assertions removed |
| C5 state-dir clutter | old script copies, plist.migrated, forecast-test-fix, templates.bak, agents.json.bak | n/a | 2026-11-18 (trash, main session) | in macOS Trash until emptied; git has every script version |

## R3a test-cut rule (main session's answer to the R3a agent, 2026-11-18; follows from Hunter's cut approval, not his words)

"Remove cut-specific tests; preserve all retained-behavior assertions. Only tests whose subject is a cut feature (chains, local gemini CLI runner, night code, or the judge running by default) may go; if a test mixes cut and retained behavior, keep and adapt the retained part. List every removed test (file::name and which cut) in your final report and in the Cut register's restore note in rewrite/PLAN.md, so they can be restored with the feature."

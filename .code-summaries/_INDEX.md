# Code summaries

Generated: 2026-11-18 | commit: 846566c0e307e65457d43b9f8f51c7174453472b | mode: path

29 file summaries (29 full, 0 brief); 2 package markers. Scope: all project directories except known holes.

Use `_FEATURES.md` for behavior, `_GRAPH.md` for import consumers. Check freshness with the helper before relying on summaries.
`brief` summaries (figure/scratch scripts) have a reviewed overview plus AST facts only; read source for details.

## Directory tree
```text
skills/
  nrp-monitor/
    scripts/
      nrp_monitor/
        task/
```

## skills/nrp-monitor/scripts/nrp_monitor
- [agents.py](skills/nrp-monitor/scripts/nrp_monitor/agents.py.md) — Manages headless sub-agent execution, CLI runner dispatch (Claude Code, Codex, Antigravity/Gemini), quota fallback, sandboxing, and allowlists across triage, repair, and task tiers. Imported by legacy.py, task_agents.py, notify.py, and setup.py; not directly run as CLI. Symbols: AgentCmd, BACKENDS, RUNNER_EXEC, Result, _answer, agent_cfg, agent_cmd, agents_available, agy_command, agy_parse, agy_workspace, auth_allowed, auth_hit, available_runners, backend_name, block_runner, check_backend, claude_argv, clean_env, codex_auth, … (+28).
- [cli.py](skills/nrp-monitor/scripts/nrp_monitor/cli.py.md) — Monitor entry point and handlers for the pass, legacy Job registration, status and logs. main builds the parser from cli_args and dispatches its selected handler; no parser definitions live here. Symbols: cmd_add, cmd_list, cmd_log, cmd_run, cmd_run_pass, cmd_status, main, run_pass, save_merged, snapshot_code.
- [cli_args.py](skills/nrp-monitor/scripts/nrp_monitor/cli_args.py.md) — Owns argparse registration for nrp-monitor and the scoped nrp-task option parsers. monitor_parser binds handlers with set_defaults; origin_edit_args and resource_args share repeated options. Tool command authorization and positional dispatch remain in nrp_task. Symbols: monitor_parser, origin_edit_args, resource_args, tool_parser.
- [cluster.py](skills/nrp-monitor/scripts/nrp_monitor/cluster.py.md) — Kubernetes cluster query interface, kubectl subprocess wrapper, node health tracker, and namespace-wide pod utilization inspector. Imported by cli, ladder, legacy, red_alert, and s3; not run directly as a CLI. Symbols: MUTATING, SNAPSHOT, _cached, apply_manifest, bad_node_lines, bad_nodes, block_episode, block_should_reapply, block_wake_text, classify_job, fetch_jobs, job_complete, job_pods, job_state, jobs_in, kubectl, my_pods, namespace_offenders, offender_text, pass_snapshot, … (+4).
- [config.py](skills/nrp-monitor/scripts/nrp_monitor/config.py.md) — Configuration loader and environment extractor for NRP monitor policies, GPU floors, concurrent job limits, utilization waivers, and AWS environment settings. Imported across nrp_monitor modules; not run as a CLI. Symbols: _skip_limit, aws_env, gpu_floor, max_jobs, skip_limit_text, step_env, util_policy, util_waiver_hours, util_waiver_max.
- [continuation.py](skills/nrp-monitor/scripts/nrp_monitor/continuation.py.md) — Orchestrates automated multi-step plan continuations when a plan task finishes, generating continue-agent prompts, evaluating outputs against acceptance criteria, and updating plan state. Imported by plan_wakes and cli; not run directly as a CLI. Symbols: close_continuation, continue_prompt, continue_task, person_resolution_context.
- [decisions.py](skills/nrp-monitor/scripts/nrp_monitor/decisions.py.md) — Manages deterministic failure fingerprinting, coordinator/deputy decision recording and replay, and LLM token/cost tracking ledger. Imported by ladder, task_agents, notify, and cli; exposes CLI subcommands decide, wake-review, and costs. Symbols: DECISION_APPLY, _decide_escalate, _decide_resubmit, _decide_skip_reuse, apply_decision, cmd_costs, cmd_decide, cmd_wake_review, cost_event, cost_rows, decisions, failure_context, fingerprint, postcheck_failure, record_decision, scaled_retry_cap.
- [ladder.py](skills/nrp-monitor/scripts/nrp_monitor/ladder.py.md) — Implements the tiered task failure escalation ladder (Tier 0 script rules, Tier 1 triage judge, Tier 2 fixer agent, Tier 2.5 deputy, Tier 3 coordinator chat, owner escalation) and stage observation loop. Imported by cli, legacy, task_pass; not run as a CLI. Symbols: Decision, LADDER, STOP, act, agents_wait, check_coordinator_waits, class_budget, class_retries, close_failure, coordinator_summary, deadline_rule, deputy_prompt, dry_run, escalate, fixer, gpu_expired, guard, handle_failure, observe_task, postcheck_guard, … (+14).
- [legacy.py](skills/nrp-monitor/scripts/nrp_monitor/legacy.py.md) — Legacy job and pod utilization monitoring loop, handling strike-based pod resizing/deletion, 3-hour GPU policy enforcement, account alarms, and multi-attempt job follow-up agents. Imported by cli; not run as a CLI directly. Symbols: _gpu_low, acct_alarm, check_jobs, check_pods, followup_solved, gpu_long_actions, gpu_long_pass, record_resize, tiered_job_followup.
- [notify.py](skills/nrp-monitor/scripts/nrp_monitor/notify.py.md) — Routes silent digest events and one-time owner pushes through Slack, Claude push and banner fallback. Push claims and rearming use state.json_txn; JSON reading and atomic writing retain their existing formats and patch targets. Renders current task/plan state into digest text. Symbols: banner, claude_push, cmd_digest, coordinating, daily_digest, digest, jwt_days_left, needs_owner, notify, push, push_clear, read_json, ref_label, render_digest, slack_dm, write_json.
- [nrp_task.py](skills/nrp-monitor/scripts/nrp_monitor/nrp_task.py.md) — Scoped nrp-task command handler for task agents: validates task identity and role before inspect, reship, commit, submit, delete, plan and report actions. Argparse options come from cli_args; submit/replacement and saved diagnostics delegate to stage_jobs. Existing positional command dispatch stays… Symbols: cmd_tool, reship_dirs.
- [plan_commands.py](skills/nrp-monitor/scripts/nrp_monitor/plan_commands.py.md) — CLI subcommands for managing multi-step execution plans (nrp-monitor plan ...): sync, list, show, close, needs-owner, and resume. Run via CLI nrp-monitor plan <subcommand>. Symbols: cmd_plan_close, cmd_plan_list, cmd_plan_needs_owner, cmd_plan_resume, cmd_plan_show, cmd_plan_sync, plan_line, plan_names.
- [plan_wakes.py](skills/nrp-monitor/scripts/nrp_monitor/plan_wakes.py.md) — Manages group wake coalescing, plan completion wake policies, terminal step wake generation, and idle plan fallback check-ins. Imported by cli, continuation, ladder, state; not run as a CLI directly. Symbols: FALLBACK_SINCE, completion_policy, continuation_covers, group_members, group_ready, process_continuations, process_group_wakes, process_plan_fallbacks, skip_closed_continuation, step_done_summary, step_mates, step_siblings, task_group, terminal_wake.
- [plans.py](skills/nrp-monitor/scripts/nrp_monitor/plans.py.md) — Parses and validates approved plan run blocks, snapshots plan text/templates, tracks ledger and step bounds, and gates continuation registration. plan_txn delegates locked load/modify/write to state.json_txn while retaining defaults and its historical callback return behavior. Symbols: approved_pos, check_on_done, ledger_add, next_steps, on_done_enabled, parse_run_block, pev, plan_dir, plan_gpu_cover, plan_header, plan_section, plan_set, plan_state, plan_sync, plan_txn, resolve_plan_path, split_list, step_pos, tool_next_add.
- [red_alert.py](skills/nrp-monitor/scripts/nrp_monitor/red_alert.py.md) — Account-wide RED ALERT monitor that probes NRP admission webhooks via server dry-run jobs and holds all task submissions across namespaces whenever NRP refuses new pods due to low utilization or quota. Imported by cli, cluster; not run directly as a CLI. Symbols: process_red_alert, red_alert, red_alert_enter, red_alert_notify, red_alert_text, red_probe.
- [s3.py](skills/nrp-monitor/scripts/nrp_monitor/s3.py.md) — S3 object existence verifier, prepass batch checker, and in-cluster Ceph fallback runner, ensuring exact key matching without prefix false positives. Imported by ladder, cli, nrp_task; not run as a CLI directly. Symbols: incluster_job, s3_check_job_manifest, s3_check_many, s3_exists, s3_incluster, s3_incluster_on, s3_prepass, s3_split, save_logs.
- [setup.py](skills/nrp-monitor/scripts/nrp_monitor/setup.py.md) — Interactive and non-interactive setup wizard and diagnostics tool for configuring LLM agent runners (Claude Code, Codex, Antigravity) across execution tiers in agents.json. Run via CLI nrp-monitor setup or nrp-monitor agents. Symbols: backend_label, cmd_agents, cmd_setup, installed_runners, parse_backend_list, parse_backend_spec, setup_ask, setup_config, suggest_tiers, write_agents_cfg.
- [sizing.py](skills/nrp-monitor/scripts/nrp_monitor/sizing.py.md) — Owns memory/CPU evidence and sizing primitives: Thanos working-set and CPU-rate peaks, saved cgroup peak extraction and single-container legacy fallback, memory-low evidence with OOM floors, quantity parsing and CPU request sizing. Also checks whether required node restrictions match any schedulabl… Symbols: UTIL_NODE_CACHE, container_memory_peak, cpu_quantity, cpu_request, mem_bytes, mem_text, memory_low_evidence, saved_memory_peak, thanos_peak_cpu, thanos_peak_mem, true_memory_peak, zero_node_reason.
- [stage_jobs.py](skills/nrp-monitor/scripts/nrp_monitor/stage_jobs.py.md) — Owns stage Job submission and replacement, resource snapshots and manifest propagation, saved diagnostics and diagnostics-before-delete. do_submit enforces retry, manifest, GPU, admission and fresh Job-state guards. utilization_restart edits resource requests/limits and queues budget-free replaceme… Symbols: delete_stage_job, do_submit, propagate_resources, resource_template, resource_values, save_task_logs, utilization_restart.
- [state.py](skills/nrp-monitor/scripts/nrp_monitor/state.py.md) — Owns state paths, constants, task persistence and the shared json_txn locked load/modify/write helper. task_txn wraps it with completed-stage preservation and terminal wake hooks; plans.plan_txn and notification claims use the same helper while retaining their own defaults and writers. Symbols: ACCT, AGENTS_CFG, AGE_RE, AGY_GATE, APPROVED, AUTH_ANY, AUTH_BLOCK_S, AUTH_BUDGET, AUTH_TIMEOUT, AUTH_TURNS, BLOCK_ESCALATE_S, BLOCK_RE, BLOCK_RECHECK_S, CHAINS, CLASSES, CLASS_DEFAULT, CLONE_MAX_FILE, CLONE_SUFFIXES, CODE_PYTHON, CODE_SKIP, … (+178).
- [task_agents.py](skills/nrp-monitor/scripts/nrp_monitor/task_agents.py.md) — Prompt builder and execution harness for task-level sub-agents (Tier 1 triage judge, Tier 2 fixer, Tier 2.5 deputy, continuation agent), enforcing tool allowlists, manifest validation checkpoints, and handoff logging. Imported by ladder, continuation; not run as a CLI directly. Symbols: run_task_agent, task_prompt.
- [task_commands.py](skills/nrp-monitor/scripts/nrp_monitor/task_commands.py.md) — Implements CLI command handlers for querying, controlling, and updating NRP tasks (task list, watch, code, stage, show, resume, needs-owner, handoff, cancel, origin, and util restart). Invoked via nrp-monitor subcommands by human operators or agent coordinators. Symbols: cmd_origin, cmd_task_cancel, cmd_task_code, cmd_task_handoff, cmd_task_list, cmd_task_needs_owner, cmd_task_resume, cmd_task_show, cmd_task_stage, cmd_task_watch, cmd_util_restart.
- [tier0.py](skills/nrp-monitor/scripts/nrp_monitor/tier0.py.md) — Implements Tier 0 deterministic heuristic automated fixes (node exclusion, memory OOM bumping, lost pod resubmission) and queue monitoring for NRP jobs without invoking LLM agents. Symbols: RULES, _oom_matches, _report_long_pending, exclude_node, node_fault_of, queue_ceiling_seconds, report_long_pending, tier0_fix, tier0_lost, tier0_node, tier0_oom, vanished_nodes.
- [timeouts.py](skills/nrp-monitor/scripts/nrp_monitor/timeouts.py.md) — Manages active deadline extensions, queue time crediting, and Tier 0 timeout recovery for running NRP jobs. Checks if log activity is progressing and resubmits resumable stages with doubled deadlines upon expiration. Symbols: deadline_watch, log_signature, patch_deadline, pod_waiting_error, stage_resumable, tier0_timeout.
- [util.py](skills/nrp-monitor/scripts/nrp_monitor/util.py.md) — Routes utilization observations, lab-only waivers, reviews and bounded NRP band actions. Evidence and CPU sizing delegate to sizing; replacement and diagnostics-before-delete delegate to stage_jobs. Fresh job_state guards for waiver acceptance remain here. Symbols: active_waiver, check_orphans, flag_rule, process_util_event, task_pod_flag, util_nrp_review, util_ok_extract, util_waive, util_waiver_check, utilization_band_action, waiver_active, waiver_stage.
- [wake.py](skills/nrp-monitor/scripts/nrp_monitor/wake.py.md) — Implements wake delivery, coordinator session resume, webhook notifications, chat origin tracking, and structured handoff file management (`handoff.md`) for tasks and plans. Symbols: NoWebhookRedirect, WAKE_EXEC, WakeError, add_origin_args, claude_session_open, detect_session, handoff_append, handoff_attach, handoff_body, handoff_chars, handoff_clean, handoff_escalation_missing, handoff_extract, handoff_join, handoff_load, handoff_path, handoff_prompt, handoff_record, handoff_set, handoff_sha, … (+24).

## skills/nrp-monitor/scripts/nrp_monitor/task
- [model.py](skills/nrp-monitor/scripts/nrp_monitor/task/model.py.md) — Defines task lifecycle state transition rules and machine (`transition`, `can`, `TRANSITIONS`), valid status sets (`LIVE`, `HELD`, `TERMINAL`), and resource resizing heuristics. Symbols: HELD, IllegalTransition, LIVE, TERMINAL, TRANSITIONS, _MOVES, can, resize_advice, transition.
- [pass_.py](skills/nrp-monitor/scripts/nrp_monitor/task/pass_.py.md) — Orchestrates each task pass: stage dependencies and S3 gates, failure classification, completion and postcheck handling, held completion recovery and repeated exception escalation. Submissions and diagnostics delegate to stage_jobs; snapshots are used for observation while action guards stay fresh. Symbols: advance_task, classify, note_waiting, pod_started, process_task, process_tasks, recover_held_completion, run_postcheck, s3_gate.
- [registry.py](skills/nrp-monitor/scripts/nrp_monitor/task/registry.py.md) — Validates, initializes, and registers multi-stage NRP tasks (`cmd_task_add`, `validate_task`, `clone_code`). Enforces manifest formatting, container resource declarations, git branch isolation, S3 bucket and key specifications, GPU permissions, and durable manifest checkpoints. Symbols: agent_manifest_checkpoint, aws_cmd, clone_code, cmd_task_add, code_dir_problem, code_dirs_check, git, gpu_expired, load_chain_file, manifest_check, manifest_doc, manifest_error, manifest_gpu, manifest_mem, manifest_structure, manifest_write, protected_dirs, pv3_spec_uri, s3_bucket_ok, task_add_raw, … (+3).

## Package markers and re-exports (no per-file summary)
- `skills/nrp-monitor/scripts/nrp_monitor/__init__.py` — Package marker.
- `skills/nrp-monitor/scripts/nrp_monitor/task/__init__.py` — Package marker.

## Known holes
- Skipped directory names anywhere in the tree: `__pycache__`, `build`, `dist`, `generated`, `internal_tests`, `node_modules`, `site-packages`, `test`, `testing`, `tests`, `third_party`, `vendor`, `vendored`; dot-directories; repo-root files.
- Notebooks, data, weights, images, shell/SLURM/YAML files, and other non-source assets are not summarized.
- `data-lifecycle/src/generate_puts_deletes_test.py` — test or placeholder.
- `data-lifecycle/tests/` — excluded directory.
- `docker-maintenance/test_maintenance.py` — test or placeholder.
- `skills/nrp-monitor/scripts/tests/` — excluded directory.
- `tests/` — excluded directory.

## Missing or stale summaries
- `data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py` — refresh before relying on navigation.
- `data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py` — refresh before relying on navigation.
- `data-lifecycle/src/badkeys.py` — refresh before relying on navigation.
- `data-lifecycle/src/generate_cleanup_report.py` — refresh before relying on navigation.
- `data-lifecycle/src/generate_puts_deletes.py` — refresh before relying on navigation.
- `data-lifecycle/src/glacier_cost_analysis_plot.py` — refresh before relying on navigation.
- `data-lifecycle/src/lifecycle_constants.py` — refresh before relying on navigation.
- `data-lifecycle/src/lifecycle_controls.py` — refresh before relying on navigation.
- `data-lifecycle/src/stage4_keys.py` — refresh before relying on navigation.
- `data-lifecycle/src/stage4_process_puts_deletes.py` — refresh before relying on navigation.
- `data-lifecycle/src/stage4_upload_poc.py` — refresh before relying on navigation.
- `docker-maintenance/maintenance.py` — refresh before relying on navigation.
- `experiment-dash/assets/style.css` — refresh before relying on navigation.
- `experiment-dash/dashboard_helpers.py` — refresh before relying on navigation.
- `experiment-dash/experiment-plotly-app.py` — refresh before relying on navigation.
- `job-h5repack/get_task.py` — refresh before relying on navigation.
- `job-h5repack/init.py` — refresh before relying on navigation.
- `job-h5repack/update_metadata.py` — refresh before relying on navigation.
- `logging-s3-aggregator/log_aggregator.py` — refresh before relying on navigation.
- `logging-s3/log.py` — refresh before relying on navigation.
- `nginx-reverse-proxy/static/index.html` — refresh before relying on navigation.
- `oauth2-proxy/error.html` — refresh before relying on navigation.
- `plotly-dash-picroscope-control-console/Experiment_Metadata_SQL.py` — refresh before relying on navigation.
- `plotly-dash-picroscope-control-console/app.py` — refresh before relying on navigation.
- `plotly-dash-picroscope-control-console/app_elements/experiment_panel.py` — refresh before relying on navigation.
- `plotly-dash-picroscope-control-console/app_elements/imaging_panel.py` — refresh before relying on navigation.
- `plotly-dash-picroscope-control-console/app_elements/livestream_panel.py` — refresh before relying on navigation.
- `plotly-dash-picroscope-control-console/assets/resizing_script.js` — refresh before relying on navigation.
- `plotly-dash-picroscope-control-console/assets/styles.css` — refresh before relying on navigation.
- `plotly-dash-picroscope-control-console/callbacks.py` — refresh before relying on navigation.
- `service-accounts/app/token_service.py` — refresh before relying on navigation.
- `shadows_vue/babel.config.js` — refresh before relying on navigation.
- `shadows_vue/public/index.html` — refresh before relying on navigation.
- `shadows_vue/src/assets/css/styles.css` — refresh before relying on navigation.
- `shadows_vue/src/auth/auth0-plugin.js` — refresh before relying on navigation.
- `shadows_vue/src/main.js` — refresh before relying on navigation.
- `shadows_vue/src/router/index.js` — refresh before relying on navigation.
- `shadows_vue/vue.config.js` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/composer.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/dumper.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/error.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/events.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/loader.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/nodes.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/parser.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/reader.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/representer.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/resolver.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/serializer.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/_vendor/yaml/tokens.py` — refresh before relying on navigation.
- `skills/braingeneers-one/scripts/suite.py` — refresh before relying on navigation.
- `skills/mission-control-services-management/scripts/authenticate.py` — refresh before relying on navigation.
- `skills/nrp-cluster/references/memory_peak.py` — refresh before relying on navigation.
- `skills/nrp-monitor/rewrite/r3b/graph.py` — refresh before relying on navigation.
- `skills/nrp-monitor/rewrite/r3b/names.py` — refresh before relying on navigation.
- `skills/nrp-monitor/rewrite/r3b/piece4-agents-backends.py` — refresh before relying on navigation.
- `skills/nrp-monitor/rewrite/r3b/toplevel.py` — refresh before relying on navigation.
- `slack-bridge/slack_bridge.py` — refresh before relying on navigation.
- `smartplug-dash/smartplug-dashboard.py` — refresh before relying on navigation.
- `strapi-shadows-db/config/admin.js` — refresh before relying on navigation.
- `strapi-shadows-db/config/api.js` — refresh before relying on navigation.
- `strapi-shadows-db/config/database.js` — refresh before relying on navigation.
- `strapi-shadows-db/config/middlewares.js` — refresh before relying on navigation.
- `strapi-shadows-db/config/plugins.js` — refresh before relying on navigation.
- `strapi-shadows-db/config/server.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/admin/app.example.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/admin/webpack.config.example.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/api/experiment/controllers/experiment.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/api/experiment/routes/experiment.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/api/experiment/services/experiment.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/api/interaction-thing/controllers/interaction-thing.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/api/interaction-thing/routes/interaction-thing.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/api/interaction-thing/services/interaction-thing.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/api/plate/controllers/plate.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/api/plate/routes/plate.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/api/plate/services/plate.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/api/sample/controllers/sample.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/api/sample/routes/sample.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/api/sample/services/sample.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/api/well/controllers/well.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/api/well/routes/well.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/api/well/services/well.js` — refresh before relying on navigation.
- `strapi-shadows-db/src/index.js` — refresh before relying on navigation.

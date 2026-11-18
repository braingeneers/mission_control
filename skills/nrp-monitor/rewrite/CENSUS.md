# nrp-monitor usage census (2026-11-18, window 2026-11-11 .. 2026-11-18 08:54)

Read-only census; nothing run except grep/stat/pytest --collect-only (645 collected, `scripts/tests/`, 35 files).

**Shorthand.** `S`=`~/.local/state/nrp-monitor`. `L7`=`awk '$1>="2026-11-11"' S/monitor.log` (15,242 lines). `D:kind`=`S/digest.log`
JSON rows (4,317 total since 11-05) with `kind` and `t>=2026-11-11`. `C:kind`=`S/costs.jsonl` rows (2,144; the file only starts
2026-11-12 15:00, so it covers ~6.7 days). Counts are over the window unless said. Script = `scripts/nrp-monitor` (8,916 lines;
lines 1-305 are preamble/constants). The script has **29** section headers (`grep -n '^# ----'`), not 24. Tests = `scripts/tests/test_*.py`.

## Totals

- Tasks registered 11-11..11-18: **274** `D:added` rows, 241 distinct names; 241 task dirs born >= 11-11 (`stat -f %B tasks/*`; 603 dirs total).
  Per day 11-11..11-18: 13, 41, 42, 22, 19, 11, **121**, 5 (11-17 was a plan-replay burst).
- Task statuses now (`tasks/*/task.json`): done 367, cancelled 226, retrying 5, running 3, WITH_COORDINATOR 1, NEEDS_OWNER 1.
- Passes: launchd `StartInterval=300` (`~/Library/LaunchAgents/edu.ucsc.hunterschweiger.nrp-monitor.plist`), last pass 141 s (`S/heartbeat`).
  No per-pass log line exists. Lower bound = distinct 5-min buckets with any L7 line per day: 159, 157, 179, 195, 136, 267, 262, (96 so far)
  of 288 max, so **~150-270 passes/day**, i.e. about one pass per 5 min around the clock. 8 `daily digest written` lines.
- Log volume in L7 by line type (`awk '{print $2}'`): `task` 10,897; `digest` 2,860; `WARNING:` 557; `notify:` 226; `plan` 180; `check_pods` 142; `chains:` 86; `PUSH` 81.
- 1,496 headless agent starts (`L7 'agent start'`): fix 656, triage 612, deputy 101, continue 90, followup 37.

## Per-section table

Verdict key: USED = daily/continuous; RARE = seen but a handful of times; UNSEEN = zero in window (all-time check noted); CANNOT TELL = no log signal.

| Section | Lines (n) | Evidence in window (pattern) | Last seen | Verdict | Tests |
|---|---|---|---|---|---|
| origin (306-505) | 306-505 (200) | 600 of 603 `tasks/*/task.json` carry `"origin"` (`grep -l '"origin"'`); L7 `origin` 81 | 11-17T23:47 (add time) | USED | test_origin, test_origin_queue |
| notifications (506) | 506-521 (16) | L7 `notify:` 226 | 11-18T08:44 | USED | test_followup_tiers |
| headless agents (522) | 522-529 (8) | L7 `agent start` 1,496 / `agent done` 1,489 | 11-18T08:53 | USED | test_agent_runners |
| agent runners | 530-907 (378) | C:triage runner `agy` 518; C:fixer `codex/gpt-6.1-sol` 536; C:deputy `claude/sonnet` 101; C:continue `codex/gpt-6.1-sol` 76; coordinator wakes `t3-cli` 166, `claude` 25, `codex` 2 | 11-18T08:53 | USED (see Q3) | test_agent_runners (27 fns) |
| gemini runner | 908-1202 (295) | `agy` triage 518 (below); `exec_gemini` (local `gemini` CLI) never selected: `S/agents.json` lists `agy` not `gemini`; L7 `gemini` 0; L7 `failover` 0, `D:failover` 0. Lines ~1087-1202 are `dispatch_agent`/`run_agent`/prompt builders used by every tier | 11-18T08:53 (agy) | USED for agy+dispatch; UNSEEN for `exec_gemini`/gemini_policy/settings (963-1028) | test_tiers (exec_gemini x2), test_followups (exec_agy) |
| cluster reads | 1203-1240 (38) | `kubectl` (25 refs), `job_state` (9 refs), `my_pods` (**1 call**) | every pass | USED | indirect |
| run (check_pods, gpu-long, check_jobs, followups) | 1241-1604 (364) | check_jobs/followups: L7 `followup agent start` 37, `D:result` 37; pod-check agent: L7 `pod-check start` 3 (88 all-time); `gpu-long` 0 (monitor.log all-time 0); `util-check` 58 (all are `check_pods error: nrp-util-check`, tool failing 11-12 (5) and 11-13 (52) only) | followup 11-17T20:30; pod-check 11-14T12:04; util-check 11-13T08:55 | USED (check_jobs/followup); RARE (pod-check); UNSEEN (gpu_long: ~100 lines, 2 test files) | test_gpu_long, test_gpu_long_e2e |
| chains | 1605-1702 (98) | see Q1: no chain registered; `chains:` lines are only kubectl errors (86) | 11-16T22:10 (error) | UNSEEN (feature) | test_chains (41) |
| validation (chain validation) | 1703-1886 (184) | defs: protected_dirs, under_protected, validate_chain, load_chain_file, dry_run_steps; only reachable via `chain add/validate`; L7 `chain add` 0, L7 `validate` hits are unrelated agent text | never | UNSEEN | test_chains (no direct validate_chain test) |
| cluster / S3 reads | 1887-2159 (273) | L7 `s3 in-cluster check:` 8; `s3 in-cluster Job .* ran` 5; `s3 external check failed` 6 (fell back in-cluster); marker checks run per pass via `s3_exists` (12 refs), `save_logs` (4 refs) | 11-18T05:38 | USED (s3_exists/save_logs); RARE (in-cluster fallback) | test_s3_incluster (18), test_s3_exact (21) |
| chain transitions | 2160-2432 (273) | L7 `chain .* step` 0; `process_chains` runs each pass over 1 `stopped` chain (heartbeat `chains=1`, `OBSERVED` at line 1612) | never transitioned | UNSEEN (loop runs, no transitions) | test_chains |
| digest and push | 2433-2553 (121) | L7 `PUSH` 81, `slack dm` 81, `claude push` 81, `osascript` 0 | 11-18T08:08 | USED (osascript path UNSEEN) | test_agent_runners |
| tasks | 2554-2631 (78) | L7 `^task ` 10,897 lines | 11-18T08:54 | USED | test_tasks (37) |
| handoff (+ wake delivery) | 2632-3262 (631) | L7 `handoff` 468; `D:handoff-owner` 54; `D:no-handoff` 43; `D:wake-ignored` 12; `wake delivery failed` 101 (82 claude "session open ... deferred", 11 codex rc, 7 codex "active writer"); `S/webhooks/` 3 entries, newest 11-07 (T3 webhook path superseded by `t3-cli` wakes) | 11-18T08:45 | USED (T3-webhook `S/webhooks` files: UNSEEN since 11-07) | test_handoff (24), test_wake (33), test_terminal_wakes, test_webhooks |
| manifests, S3, code | 3263-3576 (314) | per-task `tasks/*/manifests/`; `task add` of 241 tasks runs manifest/code checks; `task.src` dirs | 11-18T07:27 | USED | test_manifest_safety, test_existing_markers |
| task add / validate | 3577-3866 (290) | `D:added` 274; `task validate` as a command: no log signal; legacy `add` (8618): L7 `add .* resume=` 1 | 11-18T07:27 | USED (add); CANNOT TELL (validate cmd) | test_tasks |
| task pass | 3867-3970 (104) | `save_task_logs` -> `tasks/*/logs/*-a*.txt`; heartbeat `pass-ok` (~150-270/day) | 11-18T08:54 | USED | test_tasks |
| failure decisions, cost evidence | 3971-4427 (457) | C total 2,144 rows; `D:failure-ignored` 73; `D:util-review` 60; `D:block` 19 ("submit refused by NRP"); C:decision 16; `cmd_costs` | 11-18T08:54 | USED | test_escalation_costs (23) |
| account RED ALERT | 4428-4840 (413) | `S/red_alert.json` probed `braingeneers` at 11-18T08:52:35 (1795020755); L7 `RED ALERT` 0, `red-alert` 0 (code installed 11-18T07:59, commit 1c7debc, so <1 h of live data) | probe 11-18T08:52 | CANNOT TELL (probe running, no alert ever fired) | test_red_alert (6) |
| Tier 0 timeouts | 4841-4961 (121) | `D:deadline-extended` 31, `D:deadline-resubmit` 2, `Tier 0 resubmit refused` 0; `could not extend activeDeadlineSeconds` 21 (NRP webhook denial) | extend 11-18T00:52; resubmit 11-14T09:38 | USED (extend); RARE (resubmit) | test_v3_tier0 (29), test_ladder |
| Tier 1 judge | 4962-5196 (235) | L7 `triage agent start` 612; C:triage 518; `Tier 1 triage: ESCALATE: no verdict line in the triage answer` 38; `D:triage-closed` 0; C `triage_resolution` 0 | 11-18T08:53 | USED (but never closes an event, see Q4) | test_tiers (29) |
| Tier 0 rules | 5197-6212 (1016) | L7 `by tier0` rule outcomes: oom ~32, node-fault ~39 (known node fault on 14 hosts), lost 6; `tier0 .* not applied` 6; C:rule 60, C:decision 16; `D:retry` 118; rule `gpu` has no log hits. Lines also hold util-waiver (`util waiver refused`) and pending report code | 11-18T08:54 | USED (oom/node/lost); UNSEEN (`gpu` rule); `D:util-waived` 0 | test_v3_tier0, test_ladder, test_util_waiver (28) |
| plans: on_done | 6213-6958 (746) | see Q2: `continue agent start` 90, C:continue_agent 76, `D:plan-continued` 1, `D:plan-resume` 3, `D:plan-wait` 14, `D:plan-fallback` 19, `D:plan-start` 212 (211 "by session", 1 "by continuation") | 11-18T08:06 | USED | test_plans, test_plan_groups, test_plan_fallbacks, test_plan_needs_owner |
| plans: night code | 6959-7357 (399) | `D:plan-code` 0 (all-time 0 in digest.log and monitor.log); L7 `night` 0; no `plans/*/work/code-*` dir (find -name 'code-*'); 26/26 plan headers do declare `may_touch` | never | UNSEEN | test_plans only (nothing tests `tool_code`/`code_need`) |
| digest | 7358-7460 (103) | L7 `daily digest written` 8; `S/digests/` 14 files 11-05..11-18 | 11-18T08:08 | USED | none |
| task commands | 7461-7782 (322) | L7 `task show` 142; `resumed by a person` 57 (`task resume`); `task needs-owner` -> `D:handoff-owner` 54; `cmd_task_code` (7490): no signal | 11-18T07:27 | USED (show/resume/handoff); CANNOT TELL (task code, stage, watch, list) | indirect |
| nrp-task (fix agent tool) | 7783-8078 (296) | every fix/triage/deputy/continue agent (1,496) calls it; `D:resolved` 11, `D:merge` 38, `D:result` 37 | 11-18T08:53 | USED | test_ladder etc. |
| chain commands | 8079-8277 (199) | L7 `chain add` 0; `S/chain_src` newest 11-05 | never | UNSEEN | test_chains |
| setup (+ CLI main) | 8278-8916 (639) | Real setup is 8278-8516 (~240 lines); 8517-8916 is `cmd_status/run/add/list/log` and `main` (argparse). `S/agents.json` written 11-11 12:46 with `agents.json.bak` (12:01) and `.bak-20261111T1250` (setup/agents cmd run at least twice, 11-11) | 11-11T12:46 | RARE (setup); USED (main/run/status) | test_tiers, test_escalation_costs (cmd_setup/suggest_tiers) |

## Answers

**Q1 Chains.** None registered or transitioned since 11-11: L7 `chain add`=0, `chain .* step`=0, `D` has no chain kind. `S/chains/` has 13 chains,
every `chain.json` mtime **11-11 12:18** (12 `finished`, 1 `stopped`: `t51-bee21985-phase` = done,failed,7 pending); `S/chain_src/` 8 json files, newest 11-05 09:47.
All `chain_src` and chains pre-date the 11-11 v3 move to tasks. The only live effect: that one `stopped` chain is in `OBSERVED`
(`grep -n '^OBSERVED'`, line 1612), so each pass calls `kubectl get jobs` for it (heartbeat `chains=1`) and wrote 86 `chains: kubectl get jobs ... failed` lines.
Sections chains + validation + chain transitions + chain commands = 98+184+273+199 = **754 lines** with zero use.

**Q2 on_done and night code.** `S/on_done.enabled` exists (0 bytes, 11-06 13:05), so on_done is **ON**; the code comment "default OFF" (line 6213, `ON_DONE_FLAG` 6222)
only describes the absence of the file. on_done runs for real: `continue agent start` 90 (by plan: t71-donor-set 27, t71-hybrid-pilot 21, ft-ladder 13 in "continue agent for task" lines),
C:continue_agent 76 (all `codex/gpt-6.1-sol`), one actual continuation `D:plan-continued` fig2-rel-protein P1 -> P2 on 11-17T16:11, 3 `plan-resume`, 14 `plan-wait`, 19 `plan-fallback`.
`D:plan-start` 212 is almost all "(by session)" (a person's session registering a step), not auto-continuation. `S/plans/` = 26 plans, each with plan.md/header.json/state.json/work/files.
**Night code: no run ever**: `D:plan-code` 0, `grep -c plan-code monitor.log digest.log` = 0/0, no `code-*` clones under `plans/*/work`.

**Q3 Gemini.** Yes: tier 1 triage ran on Gemini through the **`agy` CLI, model `gemini-3.8-flash-low`**, 518 times in C (and 612 `triage agent start` lines in L7; the L7 window is longer than C),
plus 1 `followup` Tier-1 row. The local `gemini` CLI runner (`exec_gemini`, lines 918-1028) was never used. Backend per tier, from C (`runner`/`model`), 11-12..11-18:

| Tier | Backend ran | Count |
|---|---|---|
| judge (Tier 1 triage) | agy / gemini-3.8-flash-low (no claude-haiku fallback row; `failover` 0) | 518 |
| fixer (Tier 2) | codex / gpt-6.1-sol (+1 codex, model null) | 536 |
| continue agent | codex / gpt-6.1-sol | 76 |
| followup | codex / gpt-6.1-sol 22, codex 2, agy 1 | 25 |
| deputy | claude / sonnet | 101 (32 resolved, 66 escalated, 3 stopped) |
| coordinator wake | not an agent runner: `coordinator_wake` 225 rows; results delivered via t3-cli 166, claude 25, codex 2 | 225 |
| pod agent | codex | 3 |

**Q4 Ladder counts** (C unless noted, 11-12..11-18; per day triage 3/49/64/81/33/181/107, fixer 12/56/70/82/35/196/86):
Tier 0 rules: `rule` 60 + `decision` 16 (L7: oom ~32, node ~39, lost ~6); Tier 0 timeouts: `D:deadline-extended` 31, `D:deadline-resubmit` 2;
Tier 1 judge 518 rows (612 L7 starts), **0 `triage_resolution`**, 38 "no verdict line" parse failures; fixer 536 rows, 18 `resolved` + 4 `fixer_resolution` (outcome `escalated` is the default label for any non-resolved run, `run_agent` line 1130-1132);
deputy 101 rows, 1 `deputy_resolution`; coordinator wake 225 (kind: escalation 106, done 82, plan-fallback 19, failure 17, util_nrp 1), `wake_review` 229, `coordinator_resolution` 57, `wake_avoided` 13;
owner push: `owner_dm` 67 (L7 `PUSH` 81, 1 per `slack dm`). 123 of 2,144 rows have a non-null `cost_usd`.
Triage rows (518) and fixer rows (518 `escalated`) match 1:1, so the judge hands every case to the fixer; `D:util-review` 60 are the only "judge recommends fixer review" outcomes (watch-only tasks, Job left running), not closes.

**Q5 Duplicate cluster reads.** Section 1203-1240 (38 lines): `kubectl`, `my_pods` (pods by `nrp.ai/username` annotation, 1 caller), `job_state` (one `kubectl get job NAME` per call, 9 refs).
Section 1887-2159: `aws_env, step_env, job_complete, classify_job, fetch_jobs, parse_ts, s3_split, s3_incluster_on, s3_check_job_manifest, incluster_job, s3_incluster, s3_check_many, s3_prepass, s3_exists, save_logs`.
Overlap: `job_state` (1215) and `classify_job`+`fetch_jobs` (1915-1937) both classify a Job as ok/FAILED/running/pending and both call `job_complete`; `job_state` is single-job jsonpath, `fetch_jobs` is the batched JSON version
(`fetch_jobs` 5 refs, `job_state` 9 refs, both live). Only `kubectl` is shared plumbing. Everything else in 1887-2159 is S3 (marker exists, in-cluster fallback, log save), not cluster reads.

**Q6 setup, validation.** setup: weak evidence (agents.json + 2 baks on 11-11, nothing since; no log line). Chain validation: none (Q1). `task validate`: CANNOT TELL (no log line). `S/tests/test_chains.py` (11-04) is a stale copy, not the repo tests.

**Q7 Backup / archive candidates in S** (name | size | mtime):
- `nrp-monitor.pre-batchB.bak` 415 KB 11-12 15:14; `nrp-monitor.pre-main-7b1385b.bak` 429 KB 11-12 15:34; `nrp-monitor.pre-sizing-robustness.bak` 388 KB 11-12 14:04; `nrp-monitor.pre-watchdog-escalation.bak` 395 KB 11-12 14:55
- `nrp-watchdog.bak-20261104` 60 KB; `-20261105` 63 KB; `-20261105b` 70 KB; `-20261105c` 145 KB; `-20261106-pre-after_s3` 161 KB; `-20261106-pre-ondone` 163 KB; `-20261106-pre-s3exact` 206 KB; `-20261106-repo-stale-pre-s3exact` 161 KB (mtimes 11-04..11-06)
- `edu.ucsc.hschweig.nrp-watchdog.plist.migrated` 1 KB 11-09 15:12; `edu.ucsc.hunterschweiger.nrp-watchdog.plist.migrated` 1 KB 11-11 11:47
- `agents.json.bak` 324 B 11-11 12:01; `agents.json.bak-20261111T1250` 324 B 11-11 12:46
- `templates.bak-20261106-pre-ondone/` 20 KB, 4 files, 11-06 11:58; `templates/*.bak` (8) and `.bak-20261104/.bak-20261105` (2) inside `templates/`
- `forecast-cleanup-20261113/` 1.1 MB, 103 files, 11-13 10:11; `forecast-test-fix/` **32 MB**, 18 files, 11-13 13:35; `forecast/` 9 MB
- `backup/` 1 MB: `20261109-pre-deploy`, `pre-v3-20261111T1108`, `state-20261104-164315`, `nrp-watchdog.2026-11-04.orig`
- Not backups but large/stale: `work/` **1.0 GB** (6 entries, newest 11-17 15:01), `tasks/` 66 MB (603 dirs), `plans/` 20 MB, `resume/` 30 files newest 11-13, `resize.log` 392 KB (last 11-17 15:03), `approved/` 6 dirs newest 11-11, `S/tests/` stale copy.

## Surprises

1. 557 `WARNING: ~/.claude/skills/nrp-cluster/references/utilization-policy.json is not a valid utilization policy ([Errno 1] Operation not permitted)` since 11-11 (L7 `WARNING`): launchd cannot read `~/.claude`; the `utilization-policy.local.json` in S is the working fallback.
2. `nrp-util-check` failed 57 times (5 on 11-12, 52 on 11-13, none since) (L7 `check_pods error: ... nrp-util-check`).
3. Tier 1 judge never closes an event on its own in the window and fails to emit a verdict line 38 times; the tier is effectively a pass-through to the fixer.
4. `D:plan-start` 212 and `wake delivery failed` 101 (82 are the intentional "claude session open, deferred" case) distort naive counts of automation.
5. 754 chain-related lines + ~100 gpu-long lines + 399 night-code lines + ~70 gemini-CLI lines = roughly 1,300 script lines (15%) with no use in the window.

# nrp-monitor rewrite: design and cut list (R2, 2026-11-18)

Plan: `PLAN.md` (nrpmon-rewrite). Evidence: `CENSUS.md` (7-day usage, every number has its grep). Extra input:
the t71 coordinator chat's problem list (c38c20f5, 11-18), items U1-U9 below. Hunter 11-18: "the important part
first is to make sure we are utilizing resources properly and then comparison second."

## 1. Shape

Today: one 8,916-line script, 387 functions, 29 sections. Status changes happen at ~30 scattered
`t["status"] = ...` sites, and the ladder is one 100-line `handle_failure` of nested ifs. Cluster reads are
split across two sections (`job_state` at 1215 duplicates `classify_job`+`fetch_jobs` at 1915).

Target: a package `scripts/nrp_monitor/` plus a thin `scripts/nrp-monitor` entry point (~40 lines). Same CLI, same
state files (task.json, digest.log, costs.jsonl, agents.json, plans/), same launchd plist. install.sh copies the package
next to `~/.local/bin/nrp-monitor`. Estimate: about 5,500 lines after cuts and consolidation, no module over ~600.
This is an estimate, not measured.

| Module | Holds (today's section) | Main change |
|---|---|---|
| `state.py` | paths, JSON io, locks, `task_txn`, log, digest rows | none, only gathered |
| `config.py` | config.json, agents.json, utilization policy | install copies the policy into the state dir. Fixes the 557 "Operation not permitted" warnings (launchd cannot read `~/.claude`). |
| `cluster.py` | both cluster-read sections, pods, nodes, Thanos | **One read layer**: one batched `fetch_jobs` per pass, cached in a `PassSnapshot`. `job_state` is dropped. Pods that are Terminating are ignored while a live pod exists (U6). Ownership comes from a label set at submit, never the name prefix (U4). Adds node counts per affinity (U5). |
| `s3.py` | markers, in-cluster fallback, `save_logs` | none |
| `task/model.py` | status sets, transitions | **One state machine**: a `TRANSITIONS` table {status: {event: next}} and a single `transition(t, event, why)` that checks the move, writes the event and queues wakes. Stale queued wakes are cancelled when the task moves past them (U3 side effect). |
| `task/registry.py` | task add/validate, manifests, code snapshot | Submit labels the Job with its task. Pre-submit checks run here (U2, U5). |
| `task/pass_.py` | task pass, `advance_task`, `process_tasks` | One summary line per task per pass: submitted / waiting: reason / running (U8). |
| `ladder.py` | failure decisions, Tier 0 rules + timeouts, judge, fixer, deputy, coordinator | **Behavior as data.** `CLASSES` table: class → budget, Tier 0 rules, resumable policy. Guards are a list (same signature twice, retry cap, class budget, systemic, GPU expired), each returning a reason or None. Tiers are a list of small strategies, each `try(ctx) -> Decision \| None`, run by one loop. Tier 0 rules (oom, node, lost, timeout) are entries `{name, matches, apply}`. |
| `sizing.py` | `true_memory_peak`, `saved_memory_peak`, `thanos_peak_mem`, `propagate_resources` | **One sizing function** (R5 and U1). Requests come from the measured Thanos working-set peak and mean, not cgroup `memory.peak` (which includes page cache). Detects spiky jobs (peak/mean). Checks the NRP band. A pre-submit check compares against earlier runs of the same module (U2). |
| `util.py` | util events, waivers, NRP review, gpu-long | An **NRP violation is an action, not a note** (U1). A resumable stage is resized to the measured peak × 1.5 and restarted. A non-resumable one wakes the coordinator with the computed numbers. "No change" is not allowed while in violation. |
| `red_alert.py` | account RED ALERT | as is (1c7debc) |
| `agents.py` | agent runners, agy runner, dispatch, prompts | **One runner interface** `run(prompt, tier) -> Result`. Backends (claude, codex, agy) are rows in a `BACKENDS` dict holding the command builder and output parser. Fallback order comes from agents.json. |
| `wake.py` | origin, handoff, wake delivery | none, only gathered |
| `plans.py` | on_done continuation | night code removed (C2) |
| `notify.py` | digest, push, Slack, osascript fallback | none |
| `cli.py`, `nrp_task.py` | task commands, setup, main; the fixer's tool | Commands as a table. Adds `task resize NAME --cpu --mem` / `task restart NAME` (U3). |
| `legacy.py` | jobs.json `run`/`add`, check_jobs, followups | kept (37 followups this week) |

## 2. Cut list (needs Hunter's yes; nothing is deleted before that)

| # | Cut | Evidence (CENSUS.md) | What breaks if wrong | Recommendation |
|---|---|---|---|---|
| C1 | Chains: 4 sections, 754 lines, test_chains (41 tests) | None registered or stepped since 11-11; all 13 chains date from 11-11 12:18. One stopped chain still causes a `kubectl get jobs` each pass: 86 error lines. | A chain JSON could no longer run. Tasks with stages already cover multi-step pipelines. | **Cut**; move `S/chains`, `S/chain_src` into `S/backup/` |
| C2 | Night code: 399 lines | Never ran, ever (`plan-code` 0 in both logs, no `code-*` clones) | The `may_touch` key in plan headers (26/26 declare it) becomes ignored. WATCHDOG_ON_DONE.md and plan-run need one line each. | **Cut** |
| C3 | Local `gemini` CLI runner (`exec_gemini`, gemini policy/settings, ~70 lines) | Never selected; Gemini runs through `agy` (518 judge runs) | Setup on a machine with `gemini` but no `agy` | **Cut**; agy stays |
| C4 | Tier 1 judge in the default ladder | 518 runs, **0** closed an event, 38 gave no parseable verdict. It is a pass-through to the fixer and adds one agent run per failure. | A benign failure goes to the fixer (codex), which can also close it (18 resolved this week). | **Remove from the default ladder**; keep it as an optional strategy (one table row, off) |
| C5 | State-dir clutter | 12 old script copies (`nrp-monitor.pre-*.bak`, `nrp-watchdog.bak-*`, 2.6 MB), 2 `*.plist.migrated`, `templates.bak-*`, `agents.json.bak*`, `forecast-test-fix` (32 MB), `forecast-cleanup-20261113`, stale `S/tests/` | None: git has the history, and `S/backup/pre-v3-*` is kept | **Trash** them. Leave `work/` (1 GB) until each dir's owner is checked; `codex-home-*` is live. |

**Not cut, though rare:** gpu-long (0 log lines ever, but it is NRP's 3 h GPU-average rule, so it falls under
utilization; R3 must find out why it never logs, possibly because `nrp-util-check` failed on 11-12 and 11-13); Tier 0
resubmit (2 uses); the osascript fallback; the pod-check agent; legacy jobs.json; setup. The T3-HTTP webhook backend
(`S/webhooks` unused since 11-07) is decided in R3: `queue_task_webhook` is the live wake queue despite its name.

## 3. Problems from the t71 chat (U1-U9) and where each lands

| # | Problem (evidence in c38c20f5) | Fix | Module |
|---|---|---|---|
| U1 | Pods at 15-20% of requested memory for about 20 h, including an NRP violation, and every review ended in "no change". Sizing used cgroup peak 7.58 GiB; the Thanos working set was 6.09 GiB. | Size from the working set; spiky detection; on a violation, resize and restart if resumable, otherwise wake the coordinator with numbers | sizing, util |
| U2 | GPU stage requested 18 CPU / 42 Gi and used 1.7-1.9 cores; a 3090 job sat pending 89 min on "Insufficient cpu" | Pre-submit check against earlier runs of the module, CPU and memory | sizing, registry |
| U3 | A running task cannot be resized. The workaround (delete the Job) notified the owner, sent stale wakes and used retry budget. | `task resize` / `task restart`: a transition with no failure, no owner notice, no budget use | cli, task/model |
| U4 | The shared `pv3-gate-hschweig-*` prefix led another chat's monitor to claim t71 pods | Task label at submit; ownership from the registry and the label | cluster, registry |
| U5 | The A10 stage required region us-west, which has 0 A10 nodes, and sat 11 h | Count matching nodes at submit; zero fails at once with the reason | cluster, registry |
| U6 | A Terminating zombie pod (11 h) supplied the failure text; failed Jobs outside any task were never reported | Prefer live pods; list unowned failed Jobs in the digest (report only, no deletes) | cluster, notify |
| U7 | Workflows (Nextflow) runs are invisible; a stalled driver was caught only by a separate watcher | A new stage type `workflows`: poll `/api/runs/{id}`, success = S3 markers, stall rule | proposed R6 |
| U8 | `run` prints nothing, so it is unclear why a stage was not submitted | One line per task per pass | task/pass_ |
| U9 | Watch-only failures always reach the owner, including the coordinator's own deletes | Watch-only failures wake the coordinator first; the owner hears only if the chat says so | ladder |

## 4. Decisions for Hunter

1. **Approve the cut list (C1-C5).** It removes about 1,300 lines of code nobody used this week, plus 41 chain
   tests, and stops 86 kubectl error lines. If a cut is wrong, the code is back with one `git revert`.
   Recommend: yes to all five.
2. **How the tests carry over.** 11 test files run the script as a black box (fake kubectl/aws on PATH); they stay
   unchanged and are the contract. 23 files load the script and call about 155 internal functions directly,
   patching about 20 globals. Option A keeps them byte-identical by putting every name back into one shared namespace,
   which rebuilds the behemoth. Option B moves only their import and patch-target lines to the new modules, with
   assertions unchanged; I would show a diff proving only those lines moved. **Recommend B.**
3. **Utilization first: patch now, or wait for the rewrite?** The rewrite (R3+R4) takes days. U1, U3 and U5 are what
   put the account at risk today (NRP blocks the account past 4 violating pods). Option A: a small patch to the
   current script now. It covers the working-set source, violation → resize/restart for resumable stages, the
   `task resize` command and the zero-node check. The rewrite then carries these over behind their tests. Option B:
   build `sizing`/`util` first in R3 and swap early. **Recommend A**: the protection is live in about a day, and
   the tests written for it become part of the rewrite's contract.
4. **Watch-only rule (U9).** Today every watch-only failure reaches Hunter. Proposed: the coordinator hears first, and
   Hunter only if it says so. That is the rule every other task already follows. **Recommend yes.**
5. **Workflows stage type (U7).** New scope, not part of this plan. **Recommend** adding it as R6, after the swap
   (R4), so it is built once on the new runner and stage interfaces.

# Shadow boundary audit

`run --shadow` is the single explicit switch. It refuses installed state and runs
normal decisions against a copy below `/private/tmp/claude-501/nrp-shadow/`.
`--dry-run` alone is insufficient: it bypasses decisions and had unguarded routes.

Audited pass graph: cli.run_pass → s3_prepass, red_alert, legacy.check_pods /
check_jobs, task.pass_.process_tasks, plan_wakes.process_continuations,
wake.process_task_webhooks, util.check_orphans, notify.daily_digest.
Task edges include ladder, tier0, timeouts, stage_jobs, task_agents, continuation,
registry manifest edits and wake/handoff hooks. Local state/log writes are allowed
only inside the snapshot; external code, handoffs and manifests cannot be written.

| Boundary | Gate |
|---|---|
| cluster.kubectl; direct s3.incluster_job create; apply_manifest; delete_stage_job; tier0/timeouts/util replacement | kubectl allowlist get/describe/logs/top only; every other verb (including server dry-run create) is recorded and returns rc 125 without running, so the rest of the pass is still compared |
| s3.incluster_job | semantic skip, unknown result, no create/wait/delete |
| red_alert.red_probe | semantic skip, error/unknown admission, never assumes accepted |
| agents.dispatch_agent/run_agent/exec_backend; RUNNER_EXEC and exec aliases | semantic skip before scratch homes and executable lookup |
| notify.push/slack_dm/claude_push/banner | semantic skip; silent digest remains isolated |
| wake.wake_session/wake_t3/WAKE_EXEC/process_task_webhooks/handoff_write | semantic skip; no chat resume, webhook POST or external handoff edit |
| task.pass_.run_postcheck | arbitrary command skipped, unknown postcheck |
| all other subprocess.run, raw Popen / process primitives | only read-only kubectl and `aws [--endpoint-url X] [--profile X] s3api head-object` / `s3 ls` permitted; other subprocess.run records rc125; raw forbidden calls raise |
| nrp-util-check helper | reviewed repository source executed in-process under the same gates; its GPU kubectl exec fallback raises |
| urllib (including redirects and webhook opener) | GET to exact configured Thanos origin/path only; all other URLs/methods raise |
| Python filesystem writes/rename/remove/mkdir/chmod/utime/link | audit hook requires resolved paths inside isolated state; symlinks omitted from copy; temp files redirected there |

S3 reads (head-object, ls; exact aws_cmd shape) run for real so success markers are observed;
every other aws operation or flag shape records rc 125. (Main session change after the first pass.)
Raw argv, prompts, credentials
and URLs are never included in shadow-action records. This is a boundary for the
audited monitor, not a sandbox for hostile Python or malicious kubectl plugins.
No agents run; no child shell or cloud helper can escape these gates.

Tests cover every semantic row, stored executor aliases, every prohibited kubectl
verb, allowed reads through a fake cluster, shell/S3/agent subprocess rejection,
raw Popen rejection, webhook rejection, external write rejection and installed-state
refusal. The runner refreshes state each invocation and executes exactly one pass;
no cron, launchd, loop or scheduler is provided or installed.

Decision comparison (2026-11-18): ordered observations and suppressed actions share
`shadow-actions.jsonl` (private evidence). Semantic wrappers retain task/stage
context for submit/replacement/agents; the exact `ladder.observe_task` successful
Job deletion call records mark_done before its suppressed delete. First decisions
per stage before the first suppressed task action are comparable; everything
later is provisional. Utilization measurements alone are not review decisions;
agent entry records the review/fix category. Old-Job cleanup within do_submit is
part of submit; an explicit utilization replacement is restart. Untouched siblings after suppression are unknown, never
credited with the task's action. No-action rows need explicit installed evidence;
missing evidence stays pending through two installed intervals after pass end,
then becomes unknown. Installed launchd StartInterval was checked at 300 seconds.
Each invocation re-judges pending persisted results and rewrites their reports;
`--day-summary SINCE` aggregates those results without duplicating resolutions.
Results/pending state live only below `/private/tmp/claude-501/nrp-shadow/`;
per-run/day reports live in gitignored `runs/`. Pre-comparator Markdown reports
have no persisted decision data and are intentionally excluded from aggregation.

Filesystem finding (inferred attribution; checked local reproduction): all four
original records immediately followed kubectl apply, consistent with do_submit's
TemporaryDirectory cleanup: `stage_jobs.py:do_submit` -> TemporaryDirectory.__exit__
-> shutil.rmtree -> os.unlink('job.json', dir_fd=<isolated nrp-submit directory>).
The actual target is `<isolated pass>/nrp-submit-*/job.json`, not a task source
manifest. The old gate resolved job.json against cwd, falsely reporting an
external write. A local reproduction retained at
`/private/tmp/claude-501/nrp-shadow/cleanup-proof-1bk0q03s/proof.txt` confirms one
false block and successful tempfile recovery; it did not change the decision.
Original random directory suffixes were not recorded and are unrecoverable.
No new redirection is needed: these files already belong to isolated state.
The gate now resolves directory descriptors (F_GETPATH on macOS; /proc/self/fd
on Linux). Tests check isolated cleanup and rejection of an actual external
relative unlink. Remaining external writes stay blocked and record operation,
path kind and code caller, with the exact target retained only in private JSONL.
The comparator treats such a block as suppression, never a stage failure.

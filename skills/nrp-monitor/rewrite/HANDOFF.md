# Handoff: R3b pieces 1-2 committed; pieces 3-4 remain (relay at ~220k context)

Work only on branch `nrp-monitor-rewrite` in
`/Users/hunterschweiger/.t3/worktrees/mission_control/t3-5d6f3948-7a71276ff0751a9b`. Never edit main, install, or touch ~/.local.
Read first: `PLAN.md`, `DESIGN.md` §1, the newest `LOG.md` entry, and the original R3b brief (four pieces; tests are the contract; option B:
internal tests change only import lines/monkeypatch targets, never assertions).

## Done (each verified alone, full suite 587 passed)
- `316f168` piece 1: `task/model.py` TRANSITIONS + `transition(t, event, why, **fields)` + `can()`; every task status write uses it
  (only `state.task_load`'s NEEDS_HUNTER rename remains, a data migration). `release` drops queued escalation wakes.
- `b8bcff9` piece 2: `ladder.handle_failure` is a 17-line loop over `LADDER` (guards via `@guard(action)`, strategies return `Decision`);
  `state.CLASSES` + `failure_class()` replace CLASS_BUDGET/SYSTEMIC_CLASSES/TRIAGE_CLASSES_ALWAYS; `tier0.RULES` {name, matches, apply};
  `decisions.DECISION_APPLY`. ladder/tier0/timeouts/decisions top-import leaf modules (no cycles: `rewrite/r3b/graph.py nrp_monitor`).

## Piece 3: uncommitted in the worktree (also saved as `rewrite/r3b/piece3-cluster-snapshot.patch`)
`cluster.SNAPSHOT` + `pass_snapshot()` (opened in `cli.cmd_run_pass` and `pass_.process_tasks`), `jobs_in(ns)` (cached `fetch_jobs`),
`job_state` is now a lookup into `jobs_in` (name kept, so tests patching it need no change; the jsonpath read is gone), `job_pods`
cached per pass, `kubectl()` drops a namespace from the snapshot on mutating verbs. `process_tasks` split into `process_task`;
`s3_prepass` and `check_orphans` use `jobs_in`.
Suite with pieces 2+3: 586 passed, 1 failed: `tests/test_util_waiver.py::Refused::test_refused_when_the_job_is_not_running`
(output `/private/tmp/claude-501/r3b-p3.txt`). First step: run that test alone, read it. Likely cause: `util.py:107` calls `job_state`,
which now goes through `fetch_jobs` (`get jobs -o json`) instead of `get job NAME -o jsonpath`; that test's fake kubectl may answer
only the jsonpath form, or a snapshot from an earlier call is stale. Fix in production code if possible; otherwise adapt only the
test's patch target and list it. Then run the full suite in the background (`cd skills/nrp-monitor/scripts &&
/Users/hunterschweiger/miniconda3/bin/python3 -m pytest tests -q -p no:cacheprovider > FILE 2>&1`), and commit when it is 587.
Known leftover: `s3.incluster_job` still calls `subprocess.run(["kubectl", ... "create", "-f", "-"], input=...)` directly;
test_s3_incluster's fake pins that call with an assertion, so it stays.

## Piece 4: drafted, not applied: `rewrite/r3b/piece4-agents-backends.py`
Run `python3 rewrite/r3b/piece4-agents-backends.py scripts/nrp_monitor/agents.py` after piece 3 is committed, then add
`import functools` to the agents.py header and hoist with `python3 rewrite/r3b/toplevel.py scripts/nrp_monitor/agents.py state,notify`;
check with `rewrite/r3b/names.py`. It adds `_answer` (shared limit/auth JSON parsing), a `BACKENDS` table (refuse, home, command,
output, parse) for claude/codex/agy, one `exec_backend`, `RUNNER_EXEC` as partials (tests patch it), aliases `exec_claude/exec_codex/exec_agy`
(tests call them), and `Result` namedtuple returned by `dispatch_agent` (kept as the one interface; tests patch it by name).
Fallback order is unchanged (`tier_backends` from agents.json). wake.py untouched.

## Then
Full suite green, commit, LOG.md entry at top (commits, line counts, tests, test files touched: none so far), HANDOFF for R3c
(port patch P from main: section `# ---- utilization actions (patch P, 2026-11-18) ----` and `tests/test_util_actions.py`, once it lands),
push. Optional final commit: drop unused stdlib imports in modules other than state.py (state keeps them: the test adapter falls back
to state for stdlib names). Line counts: 9021 at 4e1a038; 8986 at b8bcff9; handle_failure 112 -> 17 lines (+172-line ladder section
that replaces it and its inline guards). Scratch worktree `/private/tmp/claude-501/p1` (detached at b8bcff9) can be removed with
`git worktree remove`.

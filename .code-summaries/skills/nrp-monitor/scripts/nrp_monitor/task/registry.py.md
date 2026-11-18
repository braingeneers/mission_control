# registry.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.task.registry`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Validates, initializes, and registers multi-stage NRP tasks (`cmd_task_add`, `validate_task`, `clone_code`). Enforces manifest formatting, container resource declarations, git branch isolation, S3 bucket and key specifications, GPU permissions, and durable manifest checkpoints.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cluster` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.decisions` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.plans` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.sizing` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_agents` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_commands` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.tier0` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.timeouts` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
- **Uses:** `cluster` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `config` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `plans` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `s3` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `tier0` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Invoked by CLI parser in `nrp_monitor.cli` for `task add` commands.
- **Shared data:** Uses `nrp_monitor.plans` to link task completion to plan steps, `nrp_monitor.wake` for handoff attachment and origin validation, and `nrp_monitor.s3` for bucket/key existence verification.

## Dependencies
- `yaml` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
### `protected_dirs()`
> Returns list of protected OS user directory paths (~/Desktop, ~/Documents, ~/Downloads) where direct daemon execution is discouraged.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:20 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:11`
### `under_protected(path)`
> Checks if a given filesystem path resolves inside any protected user directory.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:15`
### `load_chain_file(path)`
> Loads and parses YAML or JSON task/chain definition files up to 1 MB.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:534 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:26`
### `manifest_structure(doc)`
> Validates structural schema of a Kubernetes Job document (spec, template, containers, resources) before inspection.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:104 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:137 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:672 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:88 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:46`
### `manifest_error(path, error)`
> Formats human-readable error string with line and column numbers for invalid manifests.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:106 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:139 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:72`
### `agent_manifest_checkpoint(n)`
> Creates durable backup mapping of task manifest contents to detect and recover from corrupted agent edits.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:642 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:78`
### `validate_agent_manifests(n, originals=None)`
> Validates all manifests in a task directory against originals, restoring valid copies or quarantining invalid files as .rejected.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:94`
### `manifest_check(path, ns, job)`
> Enforces NRP house rules on a Job manifest (single Job, matching names/namespaces, backoffLimit 0, activeDeadlineSeconds, restartPolicy Never, no long sleeps).
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:439 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:123`
### `manifest_gpu(path)`
> Parses container resources to count GPU requests/limits in a manifest.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:191 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:504 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:506 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:168`
### `gpu_expired(s)`
> Checks if a stage's GPU request exceeds the owner's daily GPU approval date (`gpu_ok_until`).
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:187`
### `pv3_spec_uri(path)`
> Extracts S3 spec URI from `--spec` command-line argument of predictor_v3 Jobs.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:204`
### `manifest_mem(t, s)`
> Extracts memory request or limit string from first container of a manifest.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:220`
### `aws_cmd(c=None)`
> Constructs AWS CLI command array configured with custom endpoint and profile.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:241 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:230`
### `s3_bucket_ok(bucket)`
> Verifies reachability and accessibility of an S3 bucket via AWS CLI.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:517 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:238`
### `git(*args, cwd=None, inp=None)`
> Runs git command in target working directory with configured identity and timeouts.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:260 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:268 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:285 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:289 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:290 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:294 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:296 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:299 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:300 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:303 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:315 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:316 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:249`
### `clone_code(name, code, warn)`
> Clones repository into cache directory, checks out dedicated monitor branch, and commits tracked uncommitted changes.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:613 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:254`
### `code_dir_problem(x, what)`
> None, or why `x` cannot be a code dir: relative = inside the task's repo (no `..`), absolute / `~` = another git checkout.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:346 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:354 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:330`
### `code_dirs_check(code)`
> Validates packaging directories declared in code configuration against repository structure.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:400 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:342`
### `validate_task(raw, warn, plan_gpu=None)`
> Validates entire task specification including goals, approvals, stage dependencies, S3 keys, and manifests.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:568 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:363`
### `cmd_task_add(a)`
> Registers a new task, validates its stages and manifests, creates task directory, initializes git clone, and writes task state.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:530`
### `task_add_raw(raw, src_file, by='session', parent=None)`
> Register a task. by = "session" (a person or chat: `task add`) or "continuation" (the plan agent, via `nrp-task next-add`).
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:539 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:542`
### `manifest_doc(path)`
> Loads and parses YAML or JSON manifest file into Python dictionary.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:104 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:444 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:88 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:662`
### `manifest_write(path, doc)`
> Validates structure and writes Job document to disk as YAML or JSON.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/task/registry.py:671`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env `NRP_MONITOR_REQUIRE_CONTINUATION`: if set, refuses tasks registered without `on_done`, `followup`, or `digest_only`. |
| Env `NRP_MONITOR_REQUIRE_HANDOFF`: if set, refuses tasks registered with missing or thin handoff files. |
| Env `NRP_MONITOR_S3_ENDPOINT`: endpoint URL for S3 checks (defaults to `_m_state.DEFAULT_S3`). |
| `_m_config.util_policy()['smoke_max_jobs']` (default 3): maximum parallelism/completions for smoke/profile stages. |
| File path: task definition YAML/JSON file supplied to `cmd_task_add`. |

## Data Shapes
- Task definition mapping: `{"name": str, "goal": str, "approved": str, "stages": list, "mode": str, "notes": str, "code": dict, "handoff": str, "origin": dict, "on_done": dict, "followup": str, "digest_only": str, ...}`.
- Manifest document: parsed dict from Kubernetes Job YAML/JSON spec.
- Code clone spec: `{"repo": str, "branch": str, "base": str, "clone": str, "subdir": str, "pkg_dir": str, "extra_pkg_dirs": list}`.

## Notes
- Prevents tasks from registering if any active task already owns any of the declared Job names.
- Clones git repositories into `~/.cache/nrp-tasks/<task>/repo` on a new `monitor/<task>` branch, applying uncommitted changes from the source directory.
- Generates durable `agent-manifests.json` checkpoints to validate or revert agent-induced manifest corruption.

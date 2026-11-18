# agents.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.agents`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Manages headless sub-agent execution, CLI runner dispatch (Claude Code, Codex, Antigravity/Gemini), quota fallback, sandboxing, and allowlists across triage, repair, and task tiers. Imported by legacy.py, task_agents.py, notify.py, and setup.py; not directly run as CLI.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.config` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.continuation` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.legacy` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.notify` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.nrp_task` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.setup` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.shadow` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_agents` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.wake` — import consumer hint; not a proven runtime call.
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `legacy` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `wake` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imports state, notify, decisions, legacy.
- **Shared data:** Spawns external CLI processes: claude, codex, and agy.
- **Shared data:** Invoked by legacy.py for legacy job follow-up and pod checks, and task_agents.py for task repair, triage, and deputy agents.

## Dependencies
None

## Classes
### AgentCmd(list)
> The Claude form of an agent command (a list) plus the spec every runner builds its own command from.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:150`
**Kind:** class. **Instantiated by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:170 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None

## Functions
### `clean_env()`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:222 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:426 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:19`
### `default_agent_cfg()`
> Returns base dictionary of default models, limits, and ladder steps across tiers.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:109 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:113 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:60 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:26`
### `check_backend(tier, i, b)`
> Validates and normalizes a single runner/model tier backend configuration entry.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:97 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:40`
### `parse_agent_cfg(raw)`
> Validates and merges user agents.json config with system defaults.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:111 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:58`
### `load_agent_cfg()`
> Loads agents.json from state dir or falls back safely to default config.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:117 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:106`
### `agent_cfg()`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:126 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:135 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:230 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:243 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:116`
### `tier_settings(tier, runner)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:147 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:156 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:437 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:445 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:125`
### `tier_backends(tier)`
> Resolves ordered backend candidate list for a given tier.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:427 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:132`
### `spec_model(spec, runner)`
> The model a runner uses for this spec: the backend dispatch chose, else the tier's `models` entry.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:157 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:327 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:144`
### `claude_argv(spec)`
> Builds command-line argument list for invoking headless Claude Code.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:170 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:360 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:155`
### `agent_cmd(tier, allowed, json_out=False, deny=())`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:168`
### `_answer(rc, out)`
> (rc, text) of a finished agent: a JSON answer (claude/agy --output-format json) gives its result or error, and its error flag.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:190 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:198 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:175`
### `limit_hit(rc, out, err)`
> True when a finished agent process answered with a usage limit instead of doing the work.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:188`
### `auth_hit(rc, out, err)`
> True when a finished agent process failed because the CLI is not signed in / its credentials are invalid (not a bad answer).
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:196`
### `reset_time(text)`
> Epoch seconds of 'resets 2pm (America/Los_Angeles)' (next occurrence, plus a minute), or None.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:261 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:203`
### `runner_ready(name)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:230 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:247 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:413 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:430 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:221`
### `runner_blocked(name)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:230 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:413 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:433 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:225`
### `available_runners()`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:234 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:270 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:271 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:229`
### `agents_available()`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:233`
### `is_unavailable(text)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:237`
### `unavailable_text()`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:273 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:452 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:241`
### `block_runner(runner, out, err, kind='limit')`
> Temporarily marks a runner unavailable in runners.json until quota reset or auth cooldown.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:439 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:251`
### `codex_rules(allowed)`
> Claude `Bash(prefix:*)` allowlist entries as Codex execpolicy rules: a matching command runs outside the sandbox (network, kubectl); everything else stays sandboxed.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:321 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:277`
### `codex_writable(allowed)`
> Directories the Claude allowlist lets the agent edit (Edit/Write rules), minus anything inside .git.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:325 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:294`
### `agy_workspace(home, allowed)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:341 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:304`
### `codex_auth()`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:320 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:362 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:314`
### `codex_command(spec, prompt, cwd, home, env)`
> Prepares sandboxed exec command, environment, and rules file for Codex runner.
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:318`
### `codex_parse(spec, r, text)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:331`
### `agy_command(spec, prompt, cwd, home, env)`
> Configures temporary workspace and pre-tool hooks for Antigravity Gemini CLI runner.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:340`
### `agy_parse(spec, r, text)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:346`
### `scratch_home(prefix)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:389 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:371`
### `exec_backend(runner, spec, prompt, cwd, timeout, env)`
> (status, out, err, rc) of one backend run. status: ok \| timeout \| limit \| auth (the last two set the runner aside) \| error.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:383`
### `backend_name(b)`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:414 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:415 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:407`
### `note_failover(spec, backends, i, why, on_failover)`
> One line per failover (log, digest, and the task's events through `on_failover`): which backend was unavailable, why, who takes over.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:431 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:435 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/agents.py:440 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:411`
### `dispatch_agent(spec, prompt, cwd, timeout=None, env=None, on_failover=None)`
> Primary entrypoint for executing agents with automatic runner failover upon limit/auth failure.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/agents.py:459 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:422`
### `run_agent(cmd, prompt, cwd, timeout=None)`
> Runs an agent command for legacy follow-up/pod check, records cost events, and extracts verdict.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:455`
### `kube_read_allow(k)`
> Read-only kubectl patterns for headless follow-up agents. Both flag orders work: `kubectl -n NS get job X` and `kubectl get job X -n NS` (agents write the second; a literal `kubectl -n NS get` prefix denied it, 2026-11-05). Only job/pod/event reads and logs/describe are allowed, never secrets.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:482`
### `auth_allowed(k, job, ns, adir)`
> Task-level approval (owner decision 2026-11-05): the task was approved when it was registered with --authorize, so the follow-up agent may debug and resubmit it without asking: apply Job files, create a ConfigMap, delete THIS task's finished Jobs, edit the task's own files under approved/<task>/, and register the replacement (the script enforces the attempt cap and the same-failure rule there). It cannot touch secrets, other namespaces or other …
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:492`
### `pod_allowed(pod, owner_job)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:506`
### `pod_prompt(pod, flag_line, owner_job, strike=1)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:516`
### `job_prompt(job, rec, status, resume_text)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/agents.py:524`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env NRP_MONITOR_CODEX_AUTH: optional custom path to Codex auth JSON (defaults to ~/.codex/auth.json). |
| File <state>/agents.json: configures runners list, per-tier models, turn limits, USD budgets, timeouts, and fallback tiers. |
| File <state>/runners.json: stores runner rate-limiting / quota state and unblock timestamps. |

## Data Shapes
- agents.json schema: {'runners': [str], 'models': {tier: {runner: model}}, 'limits': {tier: {'turns': int, 'budget': float, 'timeout': int}}, 'followup_ladder': [str], 'tiers': {tier: [{'runner': str, 'model': str?}]}}.
- Result namedtuple: Result(runner, status, out, err, rc) where status is in ('ok', 'timeout', 'unavailable', 'limit', 'auth').
- Runner state schema: {runner_name: {'until': float, 'since': float, 'why': str, 'kind': 'limit'|'auth'}}.

## Notes
- Global state: mutates <state>/runners.json to block runners hitting limits or authentication failures.
- Sandboxing: Generates Codex execpolicy rules from Claude tool allowlists (codex_rules), and injects Antigravity pre-tool hooks (agy_workspace).
- Restricted runners: agy (Gemini CLI) is restricted strictly to read-only tiers (triage).
- Sanitizes execution environment via clean_env() before spawning any agent process.

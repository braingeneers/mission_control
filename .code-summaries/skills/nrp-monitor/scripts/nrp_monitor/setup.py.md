# setup.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/setup.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.setup`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Interactive and non-interactive setup wizard and diagnostics tool for configuring LLM agent runners (Claude Code, Codex, Antigravity) across execution tiers in agents.json. Run via CLI nrp-monitor setup or nrp-monitor agents.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli_args` — import consumer hint; not a proven runtime call.
- **Uses:** `agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Imports agents, notify, state.
- **Shared data:** Reads PATH and tests binary existence via shutil.which.

## Dependencies
None

## Classes
None

## Functions
### `installed_runners()`
> Detects which supported runner CLIs are present on system PATH.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/setup.py:95 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/setup.py:13`
### `suggest_tiers(have)`
> Proposes default backend ordering for triage and fixer tiers based on available CLIs.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/setup.py:120 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/setup.py:17`
### `parse_backend_spec(tier, text, i=0)`
> Parses and validates a runner:model string into backend dictionary.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/setup.py:47 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/setup.py:35`
### `parse_backend_list(tier, text)`
> Parses comma-separated list of runner specifications.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/setup.py:125 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/setup.py:142 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/setup.py:162 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/setup.py:46`
### `backend_label(b)`
> Formats human-readable display string for runner backend.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/setup.py:137 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/setup.py:50`
### `setup_config(old, tiers)`
> Merges new tier backend specifications into existing configuration structure.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/setup.py:165 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/setup.py:54`
### `write_agents_cfg(new_text)`
> Atomically replace agents.json with `new_text`, keeping the old file as agents.json.bak. Returns the backup path or None.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/setup.py:185 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/setup.py:71`
### `setup_ask(prompt, default='')`
> unclear — see source
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/setup.py:106 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/setup.py:140 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/setup.py:182 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/setup.py:85`
### `cmd_setup(a)`
> Interactive/non-interactive CLI wizard configuring agents.json with diff preview.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/setup.py:93`
### `cmd_agents(a)`
> CLI command displaying active runner configurations, running tests, or unblocking rate limits.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/setup.py:190`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| CLI flags for setup: --non-interactive, --subscriptions, --triage, --deputy, --fixer, --dry-run. |
| CLI flags for agents: show, test [runner], unblock <runner>. |
| File <state>/agents.json: target configuration file generated and written by setup. |

## Data Shapes
- Runner backend specification: {runner: str, model: str?}.
- Tier configuration dictionary: {tier_name: [{runner: str, model: str?}]}.
- Unified diff string showing proposed changes to agents.json.

## Notes
- Displays unified diff of changes before prompting user to write agents.json.
- Automatically backs up previous agents.json to timestamped .bak file upon write.
- Provides test command that sends a tiny probe prompt through each configured runner to verify API credentials and functionality.
- Suggests Gemini flash for read-only triage (lowest thinking), Sonnet for fixers, and configures failover ordering.

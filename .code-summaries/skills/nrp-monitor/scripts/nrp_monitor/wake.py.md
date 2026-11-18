# wake.py

**Path:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py`
**Module:** `skills.nrp-monitor.scripts.nrp_monitor.wake`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Implements wake delivery, coordinator session resume, webhook notifications, chat origin tracking, and structured handoff file management (`handoff.md`) for tasks and plans.

## Connections
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.agents` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cli_args` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.cluster` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.continuation` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.ladder` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.legacy` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.notify` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.plan_wakes` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.plans` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.red_alert` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.pass_` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task.registry` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_agents` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.task_commands` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.nrp-monitor.scripts.nrp_monitor.util` — import consumer hint; not a proven runtime call.
- **Uses:** `agents` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `decisions` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `ladder` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `notify` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Uses:** `state` from `skills.nrp-monitor.scripts.nrp_monitor` — imports (static evidence).
- **Shared data:** Used across the monitor (`task_commands`, `pass_`, `ladder`, `registry`) for origin management, handoff updates, and chat notifications.
- **Shared data:** Invokes external CLIs (`claude`, `codex`, `t3`) via subprocess.

## Dependencies
None

## Classes
### NoWebhookRedirect(urllib.request.HTTPRedirectHandler)
> unclear — see source
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:509`
**Kind:** class. **Instantiated by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:712 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
#### `redirect_request(self, req, fp, code, msg, headers, newurl)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:510`
### WakeError(Exception)
> unclear — see source
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:548`
**Kind:** class. **Instantiated by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:637 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:646 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:648 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:652 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:654 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:661 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:675 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:680 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:687 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:698 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:700 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None

## Functions
### `norm_origin(raw, source='registered')`
> Validates and sanitizes chat origin dictionary against allowed fields, harnesses, and regex schemas.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:19`
### `detect_session(harness)`
> Detects current assistant session ID from environment variables based on harness type.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:76 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:54`
### `origin_overlay(raw_origin, a)`
> Overlays CLI `--origin-*` flags on top of task raw origin configuration.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:66`
### `add_origin_args(p)`
> Adds command-line argument definitions for chat origin configuration.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:82`
### `require_origin_note(o, kind, name, always=False)`
> Prints warning or exits with error if origin information is missing on task registration.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:94`
### `origin_plain(o, fallback='')`
> Formats a single-line human-readable summary of chat origin.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:106`
### `origin_tag(o)`
> Produces short bracketed origin tag for alert headers.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:191 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:116`
### `origin_slack(o, fallback='')`
> Formats chat origin text and links for Slack notifications.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:178 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:121`
### `lookup_origin(ref)`
> Looks up origin metadata and human description for a task, chain, or legacy job reference.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:177 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:191 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:138`
### `owner_of_job(st, job)`
> Determines which task or job registration owns a given Kubernetes Job.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:156`
### `slack_text(body, refs)`
> Assembles full Slack direct message text with origin attribution and escaped body.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:167`
### `short_tag(refs)`
> Generates concise origin prefix tag for desktop banners and push notifications.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:186`
### `handoff_split(text)`
> Splits handoff markdown text by level-2 headings while ignoring code blocks.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:264 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:285 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:303 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:304 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:357 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:363 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:379 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:420 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:426 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:194`
### `handoff_join(secs)`
> Reassembles handoff sections into formatted markdown text.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:278 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:375 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:378 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:207`
### `handoff_body(secs, head)`
> Retrieves body content for a specific heading from split handoff sections.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:233 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:268 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:274 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:285 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:304 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:371 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:377 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:423 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:426 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:433 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:219`
### `handoff_set(secs, head, body)`
> Updates or inserts a heading section body in split handoff sections.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:371 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:377 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:223`
### `handoff_sha(secs)`
> Calculates SHA-256 hash of stripped Registrar section body.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:303 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:360 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:366 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:379 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:424 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:232`
### `handoff_chars(body)`
> Counts characters in text excluding comments and whitespace.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:276 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:304 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:237`
### `handoff_path(hp, src_file)`
> Resolves absolute filesystem path for handoff markdown file.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:255 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:242`
### `handoff_load(hp, src_file)`
> Validates and parses handoff file, ensuring presence of Registrar and checking character length.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:247`
### `handoff_escalation_missing(text)`
> Checks whether handoff Registrar defines failure escalation procedures.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:281`
### `handoff_write(path, text)`
> Writes text to file atomically with restricted permissions (0600).
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:301 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:302 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:382 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:384 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:289`
### `handoff_attach(t, text, thin, source)`
> Initializes `handoff.md` and `handoff.orig.md` in task directory and stores registrar metadata.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:296`
### `handoff_clean(s, limit)`
> Sanitizes agent output text, escaping headings and fences to prevent document corruption.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:343 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:402 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:307`
### `handoff_extract(text)`
> Extracts `HANDOFF_ENTRY:` and `FOR_OWNER:` blocks from agent response text.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:395 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:323`
### `handoff_append(t, header, adds)`
> Appends text entry to designated handoff section while ensuring Registrar SHA-256 remains intact.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:408 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:346`
### `handoff_record(n, kind, full, rec, ctx)`
> Appends agent run results to handoff log sections and pushes owner questions to digest.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:387`
### `handoff_prompt(t)`
> Formats condensed handoff context for injection into LLM agent prompts.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:413`
### `wake_target(t)`
> Determines wake dispatch destination (T3 CLI, Claude Code, Codex, or T3 webhook relay).
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:474 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:715 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:448`
### `queue_task_webhook(t, kind, **extra)`
> Enqueues wake event into task `webhook_outbox` atomically.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:470`
### `webhook_config(n)`
> Validates and parses task-specific webhook configuration file.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:743 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:484`
### `wake_failed(n, event, why)`
> Handles failed wake attempts, tracking retries and falling back to NEEDS_OWNER on persistent failures.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:758 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:514`
### `wake_tools(target)`
> Defines tool permissions and path access allowed during non-interactive session resumes.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:610 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:552`
### `wake_text(t, event, harness='claude')`
> Constructs prompt text sent to woken coordinator chat or T3 thread.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:731 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:737 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:566`
### `wake_argv(target)`
> Generates command-line arguments for launching non-interactive assistant session resume.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:644 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:607`
### `claude_session_open(session)`
> Checks if Claude Code session process is actively running or recently updated.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:636 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:614`
### `wake_session(target, text, timeout=None)`
> Resumes Claude or Codex session headlessly with wake prompt via subprocess.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:630`
### `wake_test_mode()`
> Checks whether execution is occurring in test mode.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:679 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:665`
### `wake_binary(harness)`
> Resolves executable path for target agent harness.
> **Called by:** skills/nrp-monitor/scripts/nrp_monitor/wake.py:639 (named-call hint); skills/nrp-monitor/scripts/nrp_monitor/wake.py:693 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:671`
### `wake_t3(target, text)`
> Sends wake message to T3 thread via `t3 thread send` CLI command.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:691`
### `process_task_webhooks(a, st)`
> Processes and delivers queued task wake events from outbox via webhooks or CLI resumes.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/scripts/nrp_monitor/wake.py:706`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env `NRP_MONITOR_REQUIRE_ORIGIN`: if set, refuses registrations lacking origin chat metadata. |
| Env `NRP_MONITOR_REQUIRE_HANDOFF`: if set, refuses registration if handoff is missing or thin. |
| Env `NRP_MONITOR_NO_WAKE`: disables wake delivery subprocesses/webhooks when set. |
| Env `NRP_MONITOR_TESTING`: activates test wake mode. |
| Env `NRP_MONITOR_<HARNESS>_BIN`: override path for harness binaries (`CLAUDE`, `CODEX`, `T3`). |
| Env `CLAUDE_CODE_CHILD_SESSION`: detects child sessions to warn about incorrect origin capture. |
| File path `_m_state.STATE / 'webhooks' / task_name`: configuration file specifying destination webhook URL and workstream. |

## Data Shapes
- Origin dictionary: `{"title": str, "link": str, "assistant": str, "collaborator": str, "harness": str, "session": str, "cwd": str, "evidence": str, "recorded": str, "source": str}`.
- Wake event dictionary: `{"task": str, "event_type": str, "event_id": str, "generation": str, "summary": str}`.
- Handoff sections: list of `(heading, body)` tuples split across markdown headers (`## Registrar`, `## Fix log`, `## Continuation`, `## For the owner`).

## Notes
- Handoff file enforces an immutable `## Registrar` section validated via SHA-256 hash. Any unauthorized tampering is restored from `handoff.orig.md`.
- Supports non-interactive session resumption via `claude --resume` or `codex exec resume`, and thread posting via `t3 thread send`.
- Guards against resuming active Claude Code sessions to avoid terminal forks.

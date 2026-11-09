# Install (ask the user first)

Installing creates a background job (launchd on macOS) that runs every 5 minutes, copies programs into `~/.local/bin`,
and writes under `~/.local/state/nrp-watchdog`. The router skill's rule applies: installing instructions authorizes none
of this. Explain it and get the user's OK.

## Requirements

Python 3.8+ (standard library only), `kubectl` with access to the `braingeneers` namespace, the AWS CLI configured for the
lab S3, and, for the background repair agents, at least one agent CLI: `claude` or `codex` (see below). Slack DMs need the lab notification-service token
(`~/.ssh/braingeneers_jwt_token.json`; never print it).

## Which assistants it works with

Two different things use an assistant. The **session** is the assistant you type to: it follows this skill, writes
`TASK.json` and runs `nrp-watchdog task add`. That needs only a shell, so any assistant that loads skills can do it
(Codex, Claude Code, GitHub Copilot, Gemini CLI, Cursor). The **background agents** are started by the scheduler, not by
a chat, and today there are two runners: `claude` and `codex` (agents.md). Neither depends on which assistant started
the task, so a Cursor or Gemini session can register work that Claude or Codex repairs overnight.

| Assistant | Loads the skill from | Registers tasks | Reminder hook |
|---|---|---|---|
| Codex | `~/.codex/skills` (`agents/openai.yaml` supplies its card) | yes, explicitly | none: follow Procedure step 6 |
| Claude Code | `~/.claude/skills` | yes; optional auto-arm hook reminds the session | optional SessionStart / auto-arm hooks |
| GitHub Copilot | `~/.copilot/skills` | yes, explicitly | none |
| Gemini CLI | `~/.gemini/skills` | yes, explicitly | none |
| Cursor | `~/.cursor/skills` | yes, explicitly | none |

Verified by the author: Claude Code and Codex (sessions and background runners). Copilot, Gemini CLI and Cursor sessions
are expected to work because registration is a plain command, but have not been run. A Copilot, Gemini or Cursor
*background runner* does not exist yet; it would need the same allowlist and sandbox as the two above, so it is not
included unverified.

## Steps

1. `sh "<SKILL>/scripts/install.sh"` installs the programs and templates and writes the scheduler definition without
   loading it. `NRP_WATCHDOG_LABEL=...` overrides the launchd label (default `edu.ucsc.<user>.nrp-watchdog`).
2. Create `~/.local/state/nrp-watchdog/config.json`:
   `{"nrp_user_annotation": "http://cilogon.org/serverE/users/NNNN", "slack_user_id": "U...", "owner_label": "yourname", "owner_name": "Your Name"}`.
   `nrp_user_annotation` is the `nrp.ai/username` annotation on your pods (`kubectl -n braingeneers get pod POD -o
   jsonpath='{.metadata.annotations}'`); without it pod checks are off. Without `slack_user_id` the DM is skipped. Each key
   can instead be an environment variable: `NRP_WATCHDOG_USER_ANNOTATION`, `NRP_WATCHDOG_SLACK_USER`,
   `NRP_WATCHDOG_OWNER_LABEL`, `NRP_WATCHDOG_OWNER_NAME`. `owner_name` is how DMs and agent prompts refer to you (default: the
   label). `code_python` is optional: the interpreter that runs `nrp-task code-test` (it needs pytest) and `reship`; by default the one that runs the script, which under launchd may be a system Python without pytest.
3. `sh "<SKILL>/scripts/install.sh" --launchd` loads the scheduler. Verify: `nrp-watchdog status` (heartbeat within 10
   minutes) and `nrp-watchdog agents test`.
4. Optional: local rules. Copy `scripts/templates/utilization-policy.local.json.example` to
   `~/.local/state/nrp-watchdog/utilization-policy.local.json` and edit it (utilization.md, "Optional: local rules"). Without it
   only the shared numbers apply (GPU floor 40%, 400 concurrent jobs). The 5% single-item skip limit in the fix agent's prompt is
   the optional `skip_limit_fraction` setting in `config.json` (or `NRP_WATCHDOG_SKIP_LIMIT_FRACTION`).
5. Optional: `agents.json` (agents.md). Optional, Claude Code only: a SessionStart hook that runs
   `nrp-watchdog status --quiet` so a session starts with a warning if the scheduler has stalled.

`launchd` cannot read `~/Desktop` or `~/Documents`, so the programs are copied, never symlinked, and code for follow-up
agents is cloned into `~/.cache/nrp-tasks`.

Tests (standard library, fake `kubectl`, `aws`, `claude` and `codex` programs, no cluster or network):
`python3 -m pytest "<SKILL>/scripts/tests"` (about two minutes). Run them from a copy if you do not want bytecode written
into the installed skill.

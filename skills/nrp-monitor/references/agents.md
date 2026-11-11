# Agents and fallback

Optional file `<state>/agents.json` (`~/.local/state/nrp-monitor/agents.json`). Without it: Claude only, with the
built-in models and limits. An invalid file is ignored with a digest fault; it never stops the scheduler.

## Choosing the backend per tier: `nrp-monitor setup`

Tier 1 (triage) and Tier 2 (fixer) each run on an ordered list of **backends** (`runner`, `model`, optional `thinking`). Tier 3 is always the
task's coordinator chat; there is no separate Opus tier. `install.sh` runs `nrp-monitor setup` once when `agents.json` is missing and a
terminal is attached (otherwise it prints how to run it). Setup asks which subscriptions you have (Claude Code, Codex, Gemini CLI, T3),
detects the installed CLIs, suggests Tier 1 = Gemini Flash with the lowest thinking (when Gemini CLI is available, else Haiku / Codex) and
Tier 2 = Sonnet (Codex after it as the failover when you have both), shows a diff against the current file, asks to write, keeps the old
file as `agents.json.bak` and replaces it atomically. Non-interactive: `nrp-monitor setup --non-interactive [--subscriptions claude,gemini]
[--triage gemini:gemini-3.8-flash:lowest,claude:haiku] [--fixer claude:sonnet] [--dry-run]` (`RUNNER[:MODEL[:THINKING]]`, comma list = order).

```json
{
  "tiers": {"triage": [{"runner": "gemini", "model": "gemini-3.8-flash", "thinking": "lowest"}, {"runner": "claude", "model": "haiku"}],
            "task":   [{"runner": "claude", "model": "sonnet"}]}
}
```

- **Failover** uses the next entry only when the one before is unavailable: a usage/rate limit (the runner is set aside until its reset
  time), not signed in (set aside one hour), or the CLI missing. A bad answer, a timeout or an ordinary error is never a reason: the answer is
  used as it is. Every failover is a line in the task's events (and the digest, kind `failover`): which backend, why, who took over.
  With no backend left the work waits and one DM says so, as before.
- **Old config** (`runners` + `models`) still loads and means the same ordered list per tier. `tiers` wins for the tiers it names.
- `thinking` (Gemini only): `lowest`, `low`, `medium`, `high`, or a token budget (integer). `lowest` is sent as thinkingLevel MINIMAL.

```json
{
  "runners": ["claude", "codex"],
  "models": {"triage": {"claude": "haiku", "codex": "gpt-6.1-sol"}, "repair": {"claude": "sonnet", "codex": "gpt-6.1-sol"}},
  "limits": {"task": {"turns": 60, "budget": 6.0, "timeout": 2700}},
  "followup_ladder": ["triage", "repair", "repair"]
}
```

- `runners`: in order of preference (without `tiers`; with `tiers` and no `runners`, the runners the tiers name). When one answers with a usage limit (for example "You've hit your weekly limit,
  resets 2pm"), it is set aside until its reset time and the next one takes over. With no runner left, agent work waits
  and one DM says so.
- Tiers: `pod` (utilization strike 2), `triage` (read-only: legacy job follow-ups and Tier 1 of the task ladder), `repair`, `repair_auth`
  (an authorized resubmit), `task` (Tier 2 fix and continue agents). Tier 3 of the task ladder is the task's coordinator chat and has no
  model entry (operations.md). `models` sets a model per runner; `limits` sets turns and dollars (Claude only) and a time
  limit in seconds.
- `followup_ladder`: what a finished job's follow-up tries, in order, each `triage` or `repair`, before a person.
- Commands: `nrp-monitor setup`, `nrp-monitor agents` (state and each tier's backends), `agents test [RUNNER]` (one tiny prompt through each runner),
  `agents unblock RUNNER`.

## The Gemini runner (read-only tier only)

`gemini` (the local Gemini CLI) is available for the `triage` tier only; a config naming it for any other tier is refused. It runs
`gemini -p ... --approval-mode default --skip-trust -o json --admin-policy FILE -m ALIAS` with the prompt on stdin. The same allowlist as
the Claude runner is enforced through Gemini CLI's policy engine: a per-run admin policy denies every tool, then allows only the listed
`nrp-task show|logs|describe|util|s3` command prefixes and reads under the task's folder (no `../`); edit and write rules are never
translated, so a Gemini agent cannot change a file, and in headless mode anything not allowed is denied. Thinking depth comes from a per-run
system settings file (`GEMINI_CLI_SYSTEM_SETTINGS_PATH`) that defines a model alias with a `thinkingConfig`; `~/.gemini` is not touched.
The Gemini CLI has no dollar or turn cap here, only the tier's time limit. Sign in with the CLI's own login (`gemini`, Google account);
`GEMINI_API_KEY` is not passed through (the agent environment is scrubbed), so an API-key user keeps the key in `~/.gemini/.env`.
Not exercised against the live model (known-issues.md): run `nrp-monitor agents test gemini` after setup.

## Claude and Codex are not equally restricted

Both start with the same allowlist. Claude denies everything not listed and limits reads to listed paths. Codex runs with
approvals off in a workspace-write sandbox (no network, writes only to the agent's own directories, `/tmp` excluded), plus
rules generated from the allowlist: a listed command may use the network, any other command stays in the sandbox. A Codex
agent can still read any file the user can, including tokens, and has no dollar or turn cap. Decide whether that is
acceptable before listing `codex`.

When the user has already specified per-tier backends/models, the agent applies them directly with
`nrp-monitor setup --non-interactive --triage ... --fixer ...`; do not ask the user to run setup.
Current live choice: Gemini Flash with lowest thinking then Haiku for triage; Codex gpt-6.1-sol then Claude Sonnet for the fixer:
```sh
nrp-monitor setup --non-interactive --triage gemini:gemini-3.8-flash:lowest,claude:haiku --fixer codex:gpt-6.1-sol,claude:sonnet
```

# Agents and fallback

Optional file `<state>/agents.json` (`~/.local/state/nrp-watchdog/agents.json`). Without it: Claude only, with the
built-in models and limits. An invalid file is ignored with a digest fault; it never stops the scheduler.

```json
{
  "runners": ["claude", "codex"],
  "models": {"triage": {"claude": "haiku", "codex": "gpt-6.1-sol"}, "repair": {"claude": "sonnet", "codex": "gpt-6.1-sol"}},
  "limits": {"task": {"turns": 60, "budget": 6.0, "timeout": 2700}},
  "followup_ladder": ["triage", "repair", "repair"]
}
```

- `runners`: in order of preference. When one answers with a usage limit (for example "You've hit your weekly limit,
  resets 2pm"), it is set aside until its reset time and the next one takes over. With no runner left, agent work waits
  and one DM says so.
- Tiers: `pod` (utilization strike 2), `triage` (read-only), `repair`, `repair_auth` (an authorized resubmit), `task`
  (fix and continue agents). `models` sets a model per runner; `limits` sets turns and dollars (Claude only) and a time
  limit in seconds.
- `followup_ladder`: what a finished job's follow-up tries, in order, each `triage` or `repair`, before a person.
- Commands: `nrp-watchdog agents` (state), `agents test [RUNNER]` (one tiny prompt through each runner),
  `agents unblock RUNNER`.

## Claude and Codex are not equally restricted

Both start with the same allowlist. Claude denies everything not listed and limits reads to listed paths. Codex runs with
approvals off in a workspace-write sandbox (no network, writes only to the agent's own directories, `/tmp` excluded), plus
rules generated from the allowlist: a listed command may use the network, any other command stays in the sandbox. A Codex
agent can still read any file the user can, including tokens, and has no dollar or turn cap. Decide whether that is
acceptable before listing `codex`.

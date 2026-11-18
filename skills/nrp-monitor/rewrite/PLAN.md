# Plan: nrp-monitor modular rewrite (id: nrpmon-rewrite)

**Central question:** can nrp-monitor keep every behavior people rely on while becoming small, modular
code that one agent can hold in context?

**Hunter's decisions (verbatim, 2026-11-18):**
- "I definitely want it to be robust but that is so much context that I am sure we can have the same
  functionality but modular and condensed"
- "ideally when possible make it modularized where this feels like a behemoth basically a bunch of if,
  else statements basically (not actually but as an analogy)"
- Approved the order: red-alert fix first (done, 1c7debc), then this cleanup, then the spiky-job check.

**Approval:** steps R1-R2 approved; both done 2026-11-18 (`CENSUS.md`, `DESIGN.md`), waiting on Hunter's answers to DESIGN.md §4. **Stop for Hunter after R2** (cut list); no deletion before he agrees.

## Steps
- **R1 Usage census.** From `~/.local/state/nrp-monitor/monitor.log` (last 7+ days), task/chain
  registries and state files: which sections actually ran (chains, night code, on_done, gemini runner,
  each ladder tier, setup). Output: `rewrite/CENSUS.md`, one row per section (lines, calls seen, last use).
- **R2 Design + cut list.** Module layout and the list of what to cut/archive, each with evidence and what
  breaks if wrong. Done when Hunter approves it.
  Design goals: behavior as data, not branches. Ladder tiers, failure classes and rules as tables /
  small strategy objects with one dispatch loop; one `Task` state machine with explicit transitions;
  one cluster-read layer (today split across two sections); one agent-runner interface for
  Claude/Codex/Gemini. Python package beside the script (e.g. `nrp_monitor/`), thin CLI entry point.
- **R3 Rewrite** module by module behind the existing tests (645 pass at 1c7debc); tests are the
  contract. Same CLI, same state file formats (or a one-time migration), same install.sh.
- **R4 Shadow run** next to the installed script (read-only / dry) for a day; diff decisions; then swap.
- **R5 Spiky-job check** at profile time (peak vs mean memory) in the new sizing module.
- **R6 (proposed, not approved) Workflows stage type** (t71 U7): poll Workflows runs as a task stage.

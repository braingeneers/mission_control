# Plan: nrp-monitor modular rewrite (id: nrpmon-rewrite)

**Central question:** can nrp-monitor keep every behavior people rely on while becoming small, modular
code that one agent can hold in context?

**Hunter's decisions (verbatim, 2026-11-18):**
- "I definitely want it to be robust but that is so much context that I am sure we can have the same
  functionality but modular and condensed"
- "ideally when possible make it modularized where this feels like a behemoth basically a bunch of if,
  else statements basically (not actually but as an analogy)"
- Approved the order: red-alert fix first (done, 1c7debc), then this cleanup, then the spiky-job check.

**Approval:** R1-R2 done 2026-11-18 (`CENSUS.md`, `DESIGN.md`). Hunter approved the DESIGN.md §4 answers below and
"start on the refactor branch": R3 approved on branch `nrp-monitor-rewrite`; utilization patch (P) approved on main.
**Stop for Hunter before the swap** (R4 install of the new package) and before R6.

**Hunter's answers to DESIGN.md §4 (verbatim, 2026-11-18):**
- Design: "great and we should implement the code map skill for this repo so agents can find things in the modules easier as well"
- 1 cuts: "ok makes sense but lets keep a list of things we cut so that if we run into a problem with the monitor we can start adding things back in if needed"
- 2 tests: "lets go with your rec" (option B: only import/patch-target lines move)
- 3 utilization: "sounds good. if you wnat to have a subagent work on the patch while we start on the refactor branch and switch over later so we can work in parallel that could make sense."
- 4 watch-only: "yes that makes sense. I am often asleep or doing something else so the coordinator should deal with it. if there is a problem that absolutely needs me and is a problem with resources we should never leave jobs hanging that could get us banned"
- 5 Workflows stage: "not really sure what this meansn" (explained in chat; still open)

**My choices (not Hunter's):** violation grace = 30 min (config key) before the monitor stops a violating Job itself;
it also stops at once when the namespace reaches `account_block_after_violating_pods` - 1 violating pods. Coding
children run on codex gpt-6.1-sol (Hunter's Sol-for-coding preference). **Stop for Hunter after R2** (cut list); no deletion before he agrees.

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
- **P Utilization patch (main, parallel to R3)**: U1 working-set sizing + violation actions (resize/restart
  resumable, else coordinator, stop after grace), U3 `task resize`/`task restart`, U5 zero-node check, U9 watch-only
  to coordinator. Own section in the script + `tests/test_util_actions.py`; R3 ports it.
- **R3a** cuts C1-C4, package scaffold, mechanical move, tests ported (option B). **R3b** state machine, ladder as
  data, one cluster layer, one runner (Opus-level design work). **R3c** port patch P from main.
- **Code map**: after R3a, run `summarize-codebase` on `scripts/nrp_monitor/` (Gemini bulk delegate), refresh after R3b/c.
- **R4 Shadow run** next to the installed script (read-only / dry) for a day; diff decisions; then swap.
- **R5 Spiky-job check** at profile time (peak vs mean memory) in the new sizing module.
- **R6 (proposed, not approved) Workflows stage type** (t71 U7): poll Workflows runs as a task stage.

## Cut register (restore from here if the monitor misses something)
Restore: `git show edd3af7:skills/nrp-monitor/scripts/nrp-monitor` has every cut section intact (line ranges from
`CENSUS.md`). Add a row when a cut lands, with the commit that removed it.

| Cut | What it did | Lines at edd3af7 | Removed in | Restore note |
|---|---|---|---|---|
| C1 chains | model-free multi-step Job pipelines (`chain add/validate/...`, `process_chains`) | 1605-1886, 2160-2432, 8079-8277 + tests/test_chains.py | (R3a) | state archived to `S/backup/chains-20261118/` |
| C2 night code | continue agent writes code overnight in a plan's `may_touch` paths | 6959-7357 | (R3a) | `may_touch` in plan headers is ignored after the cut |
| C3 local gemini CLI | `exec_gemini` runner + gemini policy/settings | ~918-1028 | (R3a) | Gemini still runs via `agy` |
| C4 Tier 1 judge default | read-only triage before the fixer; 518 runs / 0 closes | 4962-5196 | (R3a, kept as an off switch) | turn the strategy back on in config |
| C5 state-dir clutter | old script copies, plist.migrated, forecast-test-fix, templates.bak, agents.json.bak | n/a | 2026-11-18 (trash, main session) | in macOS Trash until emptied; git has every script version |

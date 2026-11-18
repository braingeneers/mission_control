# piece4-agents-backends.py

**Path:** `skills/nrp-monitor/rewrite/r3b/piece4-agents-backends.py`
**Module:** `skills.nrp-monitor.rewrite.r3b.piece4-agents-backends`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
One-off AST/regex refactoring transformation script for agents.py. Replaces separate exec_claude, exec_codex, and exec_agy functions with a unified BACKENDS table dispatch, scratch_home context manager, shared _answer parsing for limit/auth detection, and the Result namedtuple return structure. Run directly via CLI taking the target agents.py path as sys.argv[1].

## Connections
- **Shared data:** Applied to skills/nrp-monitor/scripts/nrp_monitor/agents.py.

## Dependencies
None

## Classes
None

## Functions
### `cut(start, end)`
> Helper function to slice out a section of string s between start and end delimiters and return the start index.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/rewrite/r3b/piece4-agents-backends.py:3`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| CLI argument `sys.argv[1]`: path to agents.py to transform in place. |

## Data Shapes
- Input: agents.py source text read from disk.
- Output: rewritten agents.py source code written back to sys.argv[1].

## Notes
- Modifies agents.py in place using string slicing, substring searching (s.index), and regex substitution.
- Extracts shared limit_hit and auth_hit error detection routines for agent subprocess output.

# toplevel.py

**Path:** `skills/nrp-monitor/rewrite/r3b/toplevel.py`
**Module:** `skills.nrp-monitor.rewrite.r3b.toplevel`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Code transform utility that hoists leaf package imports from function-local scopes to top-level imports and prunes unused standard library imports. Takes a Python file path and comma-separated leaf module names via CLI arguments (sys.argv[1], sys.argv[2]). Run as a CLI script during module reorganization.

## Connections
- **Shared data:** Used during the modularization of nrp-monitor to reorganize local circular imports.

## Dependencies
None

## Classes
None

## Functions
### `sub(m)`
> Regex substitution callback that extracts matched leaf import names and aliases into found dict while removing the inline local import.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/rewrite/r3b/toplevel.py:7`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| CLI argument `sys.argv[1]`: target Python file path. |
| CLI argument `sys.argv[2]`: comma-separated leaf module names to hoist. |

## Data Shapes
- Rewrites target file in place; prints `<path> hoisted [sorted leaf names]`.

## Notes
- Matches local break-cycle comments (`# Local import breaks orchestration cycle...`).
- Inserts hoisted imports immediately after existing top-level stdlib import statements.

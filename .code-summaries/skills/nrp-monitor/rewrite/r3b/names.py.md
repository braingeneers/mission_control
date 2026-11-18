# names.py

**Path:** `skills/nrp-monitor/rewrite/r3b/names.py`
**Module:** `skills.nrp-monitor.rewrite.r3b.names`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Static symbol auditor for Python files during refactoring. Accepts one or more Python file paths as CLI arguments (sys.argv[1:]), parses each AST, and collects defined, imported, stored, and loaded identifier names to report undefined name references and unused top-level imports. Run standalone from the command line.

## Connections
- **Shared data:** Audits rewritten scripts in skills/nrp-monitor before committing refactors.

## Dependencies
None

## Classes
None

## Functions
None

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| CLI arguments `sys.argv[1:]`: list of Python file paths to audit. |

## Data Shapes
- Prints `<file> UNDEFINED: [names...] UNUSED-TOP: [names...]` for any file with missing definitions or unused top-level imports.

## Notes
- Seeds global names `g` from `dir(builtins)`.
- Detects attribute-based references when flagging unused imports to prevent false positives on module namespace usage.

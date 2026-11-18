# graph.py

**Path:** `skills/nrp-monitor/rewrite/r3b/graph.py`
**Module:** `skills.nrp-monitor.rewrite.r3b.graph`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Static import dependency graph extractor and cycle detector for Python packages in the rewrite. Scans a root directory given as CLI argument (sys.argv[1]), parses AST for relative ImportFrom statements, resolves module edges, and runs depth-first cycle detection (cyc). Run directly as a CLI script during refactoring/packaging checks.

## Connections
- **Shared data:** Operates on Python source files across skills/nrp-monitor/scripts/nrp_monitor or rewrite trees.

## Dependencies
None

## Classes
None

## Functions
### `cyc(n, stack, seen)`
> Recursive depth-first search cycle detector walking the module dependency edge graph; prints cycle traces when a back-edge is found in stack.
> **Called by:** skills/nrp-monitor/rewrite/r3b/graph.py:17 (named-call hint); skills/nrp-monitor/rewrite/r3b/graph.py:18 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/nrp-monitor/rewrite/r3b/graph.py:13`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| CLI argument `sys.argv[1]`: path to repository or package root directory to inspect for cycles. |

## Data Shapes
- Edges dictionary mapping module string name to a set of imported target module strings (`edges: dict[str, set[str]]`).
- Prints boolean cycle existence (`cycles: True|False`) and dictionary of sorted dependency lists to stdout.

## Notes
- Treats relative imports (node.level > 0), with special-casing for `task.` subpackages.
- Uses recursive DFS with `seen` set and `stack` list to print any detected cycle path.

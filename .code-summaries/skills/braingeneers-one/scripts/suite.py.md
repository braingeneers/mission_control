# suite.py

**Path:** `skills/braingeneers-one/scripts/suite.py`
**Module:** `skills.braingeneers-one.scripts.suite`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Catalog maintenance and verification script for Braingeneers skills, tracking GitHub tree SHAs, fingerprints, and frontmatter metadata without running lab operations.

## Connections
- **Shared data:** Loads vendored PyYAML from `_vendor/yaml/__init__.py`.
- **Shared data:** Interacts with git subprocesses to compute tree hashes and blob SHAs.

## Dependencies
None

## Classes
### Failure(Exception)
> Exception indicating catalog verification or sync failure.
**Source:** `skills/braingeneers-one/scripts/suite.py:37`
**Kind:** class. **Instantiated by:** skills/braingeneers-one/scripts/suite.py:105 (named-call hint); skills/braingeneers-one/scripts/suite.py:114 (named-call hint); skills/braingeneers-one/scripts/suite.py:127 (named-call hint); skills/braingeneers-one/scripts/suite.py:142 (named-call hint); skills/braingeneers-one/scripts/suite.py:150 (named-call hint); skills/braingeneers-one/scripts/suite.py:160 (named-call hint); skills/braingeneers-one/scripts/suite.py:164 (named-call hint); skills/braingeneers-one/scripts/suite.py:167 (named-call hint); skills/braingeneers-one/scripts/suite.py:173 (named-call hint); skills/braingeneers-one/scripts/suite.py:175 (named-call hint); skills/braingeneers-one/scripts/suite.py:184 (named-call hint); skills/braingeneers-one/scripts/suite.py:197 (named-call hint); skills/braingeneers-one/scripts/suite.py:262 (named-call hint); skills/braingeneers-one/scripts/suite.py:268 (named-call hint); skills/braingeneers-one/scripts/suite.py:276 (named-call hint); skills/braingeneers-one/scripts/suite.py:328 (named-call hint); skills/braingeneers-one/scripts/suite.py:45 (named-call hint); skills/braingeneers-one/scripts/suite.py:48 (named-call hint); skills/braingeneers-one/scripts/suite.py:56 (named-call hint); skills/braingeneers-one/scripts/suite.py:62 (named-call hint); skills/braingeneers-one/scripts/suite.py:65 (named-call hint); skills/braingeneers-one/scripts/suite.py:81 (named-call hint); skills/braingeneers-one/scripts/suite.py:85 (named-call hint); skills/braingeneers-one/scripts/suite.py:89 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None
### Suite()
> Class managing skill catalog loading, validation, and metadata synchronization.
**Source:** `skills/braingeneers-one/scripts/suite.py:119`
**Kind:** class. **Instantiated by:** skills/braingeneers-one/scripts/suite.py:321 (named-call hint)
**Constructor:** `__init__(self, root, state_dir, catalog=None)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `catalog` | inferred at runtime | `load_catalog() if catalog is None else catalog` |
| `root` | inferred at runtime | `Path(root).absolute()` |
| `state` | inferred at runtime | `json.loads(self.state_file.read_text()) if self.state_file.exists() else {}` |
| `state_dir` | inferred at runtime | `Path(state_dir).absolute()` |
| `state_file` | inferred at runtime | `self.state_dir / 'state.json'` |
| `trees` | inferred at runtime | `{}` |
**Methods:**
#### `save(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** write call (static hint).
**Source:** `skills/braingeneers-one/scripts/suite.py:132`
#### `metadata(self, item, directory)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/suite.py:138`
#### `verify(self, item, directory, tree_sha)`
> Check every file against immutable source; ignore only gh's injected tracking fields.
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/suite.py:153`
#### `enroll(self, item)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/suite.py:177`
#### `latest(self, item)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/suite.py:190`
#### `status(self, daily=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state; write call (static hint).
**Source:** `skills/braingeneers-one/scripts/suite.py:200`
#### `installed_fingerprints(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/suite.py:228`
#### `install(self, name, update=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state; write call (static hint).
**Source:** `skills/braingeneers-one/scripts/suite.py:239`

## Functions
### `command(args, cwd=None)`
> Executes shell commands capturing output with timeout handling.
> **Called by:** skills/braingeneers-one/scripts/suite.py:257 (named-call hint); skills/braingeneers-one/scripts/suite.py:54 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/suite.py:41`
### `api(endpoint)`
> unclear — see source
> **Called by:** skills/braingeneers-one/scripts/suite.py:157 (named-call hint); skills/braingeneers-one/scripts/suite.py:169 (named-call hint); skills/braingeneers-one/scripts/suite.py:192 (named-call hint); skills/braingeneers-one/scripts/suite.py:194 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/suite.py:52`
### `frontmatter(data)`
> unclear — see source
> **Called by:** skills/braingeneers-one/scripts/suite.py:139 (named-call hint); skills/braingeneers-one/scripts/suite.py:170 (named-call hint); skills/braingeneers-one/scripts/suite.py:171 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/suite.py:59`
### `without_tracking(header)`
> unclear — see source
> **Called by:** skills/braingeneers-one/scripts/suite.py:172 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/suite.py:69`
### `files_at(directory)`
> unclear — see source
> **Called by:** skills/braingeneers-one/scripts/suite.py:162 (named-call hint); skills/braingeneers-one/scripts/suite.py:95 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/suite.py:79`
### `fingerprint(directory)`
> Computes reproducible SHA-256 tree hash across skill directories.
> **Called by:** skills/braingeneers-one/scripts/suite.py:179 (named-call hint); skills/braingeneers-one/scripts/suite.py:234 (named-call hint); skills/braingeneers-one/scripts/suite.py:250 (named-call hint); skills/braingeneers-one/scripts/suite.py:264 (named-call hint); skills/braingeneers-one/scripts/suite.py:267 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/suite.py:94`
### `blob_sha(data)`
> unclear — see source
> **Called by:** skills/braingeneers-one/scripts/suite.py:174 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/suite.py:98`
### `load_catalog(path=ONE / 'references/catalog.json')`
> unclear — see source
> **Called by:** skills/braingeneers-one/scripts/suite.py:123 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/suite.py:102`
### `main()`
> CLI entry point parsing suite subcommands and flags.
> **Called by:** skills/braingeneers-one/scripts/suite.py:353 (named-call hint). **Side effects:** write call (static hint).
**Source:** `skills/braingeneers-one/scripts/suite.py:292`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| `--catalog PATH`: Custom catalog YAML file path. |
| Commands: `check`, `update`, `freeze`, `sync`, `fingerprint`. |

## Data Shapes
- Input: Skill directory trees, YAML frontmatter from `SKILL.md`.
- Output: Canonical catalog YAML containing pinned GitHub references and tree hashes.

## Notes
- Dynamically imports vendored pure-Python PyYAML from `_vendor/yaml/` without touching global site-packages.
- Disables `.pyc` bytecode emission during vendored module import via `sys.dont_write_bytecode`.

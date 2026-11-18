# resolver.py

**Path:** `skills/braingeneers-one/scripts/_vendor/yaml/resolver.py`
**Module:** `skills.braingeneers-one.scripts._vendor.yaml.resolver`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Implicit tag resolution engine using compiled regular expression tables to determine data types (bool, int, float, null, timestamp) for untagged plain scalars.

## Connections
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.dumper` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.loader` — import consumer hint; not a proven runtime call.
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.error` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.nodes` — imports (static evidence).
- **Shared data:** Inherited by loaders in `loader.py` and dumpers in `dumper.py`.

## Dependencies
None

## Classes
### ResolverError(YAMLError)
> Exception raised on resolver configuration error.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/resolver.py:9`
**Kind:** class. **Instantiated by:** skills/braingeneers-one/scripts/_vendor/yaml/resolver.py:62 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/resolver.py:75 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/resolver.py:78 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/resolver.py:88 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None
### BaseResolver()
> Base tag resolver with configurable implicit type patterns.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/resolver.py:12`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `resolver_exact_paths` | inferred at runtime | `[]` |
| `resolver_prefix_paths` | inferred at runtime | `[]` |
**Methods:**
#### `add_implicit_resolver(cls, tag, regexp, first)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/resolver.py:26`
#### `add_path_resolver(cls, tag, path, kind=None)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/resolver.py:38`
#### `descend_resolver(self, current_node, current_index)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/resolver.py:91`
#### `ascend_resolver(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/resolver.py:114`
#### `check_resolver_prefix(self, depth, path, kind, current_node, current_index)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/resolver.py:120`
#### `resolve(self, kind, value, implicit)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/resolver.py:143`
### Resolver(BaseResolver)
> Standard YAML 1.1 tag resolver with full type detection rules.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/resolver.py:167`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None

## Functions
None

## Config / CLI
None

## Data Shapes
- Input: Scalar value string and implicit flag.
- Output: YAML tag identifier string (e.g., `tag:yaml.org,2002:int`, `tag:yaml.org,2002:bool`).

## Notes
- Indexes regex rules by initial character to accelerate tag resolution during scanning.

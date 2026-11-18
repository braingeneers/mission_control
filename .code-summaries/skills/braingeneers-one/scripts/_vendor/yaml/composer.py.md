# composer.py

**Path:** `skills/braingeneers-one/scripts/_vendor/yaml/composer.py`
**Module:** `skills.braingeneers-one.scripts._vendor.yaml.composer`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
PyYAML composer module building abstract syntax representation trees (`Node`, `ScalarNode`, `SequenceNode`, `MappingNode`) from parser event streams.

## Connections
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.loader` — import consumer hint; not a proven runtime call.
- **Uses:** `MarkedYAMLError` from `skills.braingeneers-one.scripts._vendor.yaml.error` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.events` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.nodes` — imports (static evidence).
- **Shared data:** Subclasses used by `loader.py`.
- **Shared data:** Imports events from `events.py` and nodes from `nodes.py`.

## Dependencies
None

## Classes
### ComposerError(MarkedYAMLError)
> Exception raised when composer encounters invalid document structure or undefined aliases.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/composer.py:8`
**Kind:** class. **Instantiated by:** skills/braingeneers-one/scripts/_vendor/yaml/composer.py:41 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/composer.py:68 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/composer.py:75 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None
### Composer()
> Event-to-node tree builder maintaining anchor cache and building document node hierarchies.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/composer.py:11`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `anchors` | inferred at runtime | `{}` |
**Methods:**
#### `check_node(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/composer.py:16`
#### `get_node(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/composer.py:24`
#### `get_single_node(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/composer.py:29`
#### `compose_document(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/composer.py:50`
#### `compose_node(self, parent, index)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/composer.py:63`
#### `compose_scalar_node(self, anchor)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/composer.py:88`
#### `compose_sequence_node(self, anchor)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/composer.py:99`
#### `compose_mapping_node(self, anchor)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/composer.py:117`

## Functions
None

## Config / CLI
None

## Data Shapes
- Input: Stream of parser events (`StreamStartEvent`, `MappingStartEvent`, etc.).
- Output: Representation node tree rooted at a `Node` instance.

## Notes
- Resolves YAML anchors and aliases into repeated graph node references.

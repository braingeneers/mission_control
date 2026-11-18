# serializer.py

**Path:** `skills/braingeneers-one/scripts/_vendor/yaml/serializer.py`
**Module:** `skills.braingeneers-one.scripts._vendor.yaml.serializer`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Serializes representation node graphs (`Node`, `MappingNode`, `SequenceNode`) into linearized event streams (`events.py`) with document boundaries and anchor alias references.

## Connections
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.dumper` — import consumer hint; not a proven runtime call.
- **Uses:** `YAMLError` from `skills.braingeneers-one.scripts._vendor.yaml.error` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.events` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.nodes` — imports (static evidence).
- **Shared data:** Inherited by dumpers in `dumper.py`.
- **Shared data:** Consumes nodes from `nodes.py` and emits events from `events.py`.

## Dependencies
None

## Classes
### SerializerError(YAMLError)
> Exception raised during node graph serialization.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/serializer.py:8`
**Kind:** class. **Instantiated by:** skills/braingeneers-one/scripts/_vendor/yaml/serializer.py:32 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/serializer.py:34 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/serializer.py:38 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/serializer.py:48 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/serializer.py:50 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None
### Serializer()
> Converts node hierarchy into stream of DocumentStart, Node, and DocumentEnd events.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/serializer.py:11`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, encoding=None, explicit_start=None, explicit_end=None, version=None, tags=None)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `anchors` | inferred at runtime | `{}` |
| `closed` | inferred at runtime | `None` |
| `last_anchor_id` | inferred at runtime | `0` |
| `serialized_nodes` | inferred at runtime | `{}` |
| `use_encoding` | inferred at runtime | `encoding` |
| `use_explicit_end` | inferred at runtime | `explicit_end` |
| `use_explicit_start` | inferred at runtime | `explicit_start` |
| `use_tags` | inferred at runtime | `tags` |
| `use_version` | inferred at runtime | `version` |
**Methods:**
#### `open(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/serializer.py:27`
#### `close(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/serializer.py:36`
#### `serialize(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/serializer.py:46`
#### `anchor_node(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/serializer.py:60`
#### `generate_anchor(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/serializer.py:74`
#### `serialize_node(self, node, parent, index)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/serializer.py:78`

## Functions
None

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Options: `encoding`, `explicit_start`, `explicit_end`, `version`, `tags`. |

## Data Shapes
- Input: Representation node tree rooted at `Node`.
- Output: Stream of emitter events.

## Notes
- Identifies multi-referenced nodes and assigns anchor names for alias emission.

# nodes.py

**Path:** `skills/braingeneers-one/scripts/_vendor/yaml/nodes.py`
**Module:** `skills.braingeneers-one.scripts._vendor.yaml.nodes`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Defines abstract syntax graph representation node classes (`Node`, `ScalarNode`, `SequenceNode`, `MappingNode`) used between composition and construction.

## Connections
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.composer` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.constructor` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.representer` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.resolver` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.serializer` — import consumer hint; not a proven runtime call.
- **Shared data:** Produced by `composer.py` and `representer.py`.
- **Shared data:** Consumed by `constructor.py` and `serializer.py`.

## Dependencies
None

## Classes
### Node(object)
> Base class for all YAML representation nodes.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/nodes.py:2`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, tag, value, start_mark, end_mark)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `end_mark` | inferred at runtime | `end_mark` |
| `start_mark` | inferred at runtime | `start_mark` |
| `tag` | inferred at runtime | `tag` |
| `value` | inferred at runtime | `value` |
**Methods:**
#### `__repr__(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/nodes.py:8`
### ScalarNode(Node)
> Node holding scalar leaf values.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/nodes.py:25`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, tag, value, start_mark=None, end_mark=None, style=None)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `end_mark` | inferred at runtime | `end_mark` |
| `start_mark` | inferred at runtime | `start_mark` |
| `style` | inferred at runtime | `style` |
| `tag` | inferred at runtime | `tag` |
| `value` | inferred at runtime | `value` |
**Methods:**
None
### CollectionNode(Node)
> unclear — see source
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/nodes.py:35`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, tag, value, start_mark=None, end_mark=None, flow_style=None)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `end_mark` | inferred at runtime | `end_mark` |
| `flow_style` | inferred at runtime | `flow_style` |
| `start_mark` | inferred at runtime | `start_mark` |
| `tag` | inferred at runtime | `tag` |
| `value` | inferred at runtime | `value` |
**Methods:**
None
### SequenceNode(CollectionNode)
> Node representing an ordered sequence of child nodes.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/nodes.py:44`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None
### MappingNode(CollectionNode)
> Node representing key-value node pairs.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/nodes.py:47`
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
- `ScalarNode`: `(tag, value, start_mark, end_mark, style)`
- `SequenceNode`: `(tag, value: list[Node], start_mark, end_mark, flow_style)`
- `MappingNode`: `(tag, value: list[tuple[Node, Node]], start_mark, end_mark, flow_style)`

## Notes
- Nodes retain start and end source marks for error reporting during construction.

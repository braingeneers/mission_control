# representer.py

**Path:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py`
**Module:** `skills.braingeneers-one.scripts._vendor.yaml.representer`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
PyYAML representer engine converting native Python objects, containers, and primitives into abstract representation node trees.

## Connections
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.dumper` — import consumer hint; not a proven runtime call.
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.error` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.nodes` — imports (static evidence).
- **Shared data:** Inherited by dumpers in `dumper.py`.
- **Shared data:** Produces nodes defined in `nodes.py`.

## Dependencies
None

## Classes
### RepresenterError(YAMLError)
> Exception raised when an object cannot be serialized to YAML.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:10`
**Kind:** class. **Instantiated by:** skills/braingeneers-one/scripts/_vendor/yaml/representer.py:231 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/representer.py:321 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None
### BaseRepresenter()
> Base serializer mapping Python types to representation nodes.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:13`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, default_style=None, default_flow_style=False, sort_keys=True)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `alias_key` | inferred at runtime | `None` |
| `default_flow_style` | inferred at runtime | `default_flow_style` |
| `default_style` | inferred at runtime | `default_style` |
| `object_keeper` | inferred at runtime | `[]` |
| `represented_objects` | inferred at runtime | `{}` |
| `sort_keys` | inferred at runtime | `sort_keys` |
**Methods:**
#### `represent(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:26`
#### `represent_data(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:33`
#### `add_representer(cls, data_type, representer)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:66`
#### `add_multi_representer(cls, data_type, representer)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:72`
#### `represent_scalar(self, tag, value, style=None)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:77`
#### `represent_sequence(self, tag, sequence, flow_style=None)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:85`
#### `represent_mapping(self, tag, mapping, flow_style=None)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:103`
#### `ignore_aliases(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:131`
### SafeRepresenter(BaseRepresenter)
> Serializes standard safe Python types.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:134`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
#### `ignore_aliases(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:136`
#### `represent_none(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:144`
#### `represent_str(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:147`
#### `represent_binary(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:150`
#### `represent_bool(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:157`
#### `represent_int(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:164`
#### `represent_float(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:171`
#### `represent_list(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:191`
#### `represent_dict(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:206`
#### `represent_set(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:209`
#### `represent_date(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:215`
#### `represent_datetime(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:219`
#### `represent_yaml_object(self, tag, data, cls, flow_style=None)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:223`
#### `represent_undefined(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:230`
### Representer(SafeRepresenter)
> Extended representer handling custom Python classes, functions, and modules.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:272`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
#### `represent_complex(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:274`
#### `represent_tuple(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:285`
#### `represent_name(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:288`
#### `represent_module(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:292`
#### `represent_object(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:296`
#### `represent_ordered_dict(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/representer.py:358`

## Functions
None

## Config / CLI
None

## Data Shapes
- Input: Native Python objects (int, float, str, dict, list, set, custom classes).
- Output: Representation node tree rooted at a `Node` instance.

## Notes
- Detects recursive data structure references and emits YAML anchors.
- Provides `BaseRepresenter`, `SafeRepresenter`, and `Representer` classes.

# constructor.py

**Path:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py`
**Module:** `skills.braingeneers-one.scripts._vendor.yaml.constructor`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
PyYAML constructor engine transforming abstract representation nodes (`MappingNode`, `SequenceNode`, `ScalarNode`) into native Python objects, mappings, lists, and primitives.

## Connections
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.loader` — import consumer hint; not a proven runtime call.
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.error` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.nodes` — imports (static evidence).
- **Shared data:** Composed into loader classes in `loader.py`.
- **Shared data:** Uses node types from `nodes.py`.

## Dependencies
None

## Classes
### ConstructorError(MarkedYAMLError)
> Exception raised during object construction from representation nodes.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:16`
**Kind:** class. **Instantiated by:** skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:119 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:126 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:134 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:141 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:149 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:194 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:204 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:298 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:307 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:359 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:363 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:367 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:380 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:384 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:388 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:39 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:427 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:504 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:513 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:527 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:533 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:536 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:542 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:553 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:556 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:560 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:568 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:575 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:587 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:74 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None
### BaseConstructor()
> Base class managing constructed objects, memoized anchors, and tag constructor hooks.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:19`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `constructed_objects` | inferred at runtime | `{}` |
| `deep_construct` | inferred at runtime | `False` |
| `recursive_objects` | inferred at runtime | `{}` |
| `state_generators` | inferred at runtime | `[]` |
**Methods:**
#### `check_data(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:30`
#### `check_state_key(self, key)`
> Block special attributes/methods from being set in a newly created object, to prevent user-controlled methods from being called during deserialization
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:34`
#### `get_data(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:42`
#### `get_single_data(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:47`
#### `construct_document(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:54`
#### `construct_object(self, node, deep=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:67`
#### `construct_scalar(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:117`
#### `construct_sequence(self, node, deep=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:124`
#### `construct_mapping(self, node, deep=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:132`
#### `construct_pairs(self, node, deep=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:147`
#### `add_constructor(cls, tag, constructor)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:160`
#### `add_multi_constructor(cls, tag_prefix, multi_constructor)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:166`
### SafeConstructor(BaseConstructor)
> Constructor supporting standard safe YAML tags (integers, strings, floats, timestamps, sequences, mappings).
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:171`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
#### `construct_scalar(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:173`
#### `flatten_mapping(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:180`
#### `construct_mapping(self, node, deep=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:215`
#### `construct_yaml_null(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:220`
#### `construct_yaml_bool(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:233`
#### `construct_yaml_int(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:237`
#### `construct_yaml_float(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:270`
#### `construct_yaml_binary(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:294`
#### `construct_yaml_timestamp(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:322`
#### `construct_yaml_omap(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:353`
#### `construct_yaml_pairs(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:375`
#### `construct_yaml_set(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:396`
#### `construct_yaml_str(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:402`
#### `construct_yaml_seq(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:405`
#### `construct_yaml_map(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:410`
#### `construct_yaml_object(self, node, cls)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:416`
#### `construct_undefined(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:426`
### FullConstructor(SafeConstructor)
> Constructor supporting arbitrary Python module lookups and object instantiation.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:482`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** inherited / implicit
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `state_keys_blacklist_regexp` | inferred at runtime | `re.compile('(' + '\|'.join(self.get_state_keys_blacklist()) + ')')` |
**Methods:**
#### `get_state_keys_blacklist(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:486`
#### `get_state_keys_blacklist_regexp(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:489`
#### `construct_python_str(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:494`
#### `construct_python_unicode(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:497`
#### `construct_python_bytes(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:500`
#### `construct_python_long(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:516`
#### `construct_python_complex(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:519`
#### `construct_python_tuple(self, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:522`
#### `find_python_module(self, name, mark, unsafe=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:525`
#### `find_python_name(self, name, mark, unsafe=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:540`
#### `construct_python_name(self, suffix, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:565`
#### `construct_python_module(self, suffix, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:572`
#### `make_python_instance(self, suffix, node, args=None, kwds=None, newobj=False, unsafe=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:579`
#### `set_python_instance_state(self, instance, state, unsafe=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:595`
#### `construct_python_object(self, suffix, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:614`
#### `construct_python_object_apply(self, suffix, node, newobj=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:623`
#### `construct_python_object_new(self, suffix, node)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:658`
### UnsafeConstructor(FullConstructor)
> unclear — see source
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:713`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
#### `find_python_module(self, name, mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:715`
#### `find_python_name(self, name, mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:718`
#### `make_python_instance(self, suffix, node, args=None, kwds=None, newobj=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:721`
#### `set_python_instance_state(self, instance, state)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:725`
### Constructor(UnsafeConstructor)
> Default PyYAML constructor subclass extending SafeConstructor.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/constructor.py:747`
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
- Input: `Node` hierarchy.
- Output: Native Python objects (str, int, float, bool, list, dict, set, datetime).

## Notes
- Provides `BaseConstructor`, `SafeConstructor`, `FullConstructor`, and `UnsafeConstructor` hierarchies with tag dispatch tables.

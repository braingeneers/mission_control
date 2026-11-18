# __init__.py

**Path:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py`
**Module:** `skills.braingeneers-one.scripts._vendor.yaml`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Vendored PyYAML package root providing public serialization and deserialization APIs (`load`, `safe_load`, `dump`, `safe_dump`, `scan`, `parse`, `compose`).

## Connections
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.dumper` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.error` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.events` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.loader` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.nodes` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.tokens` — imports (static evidence).
- **Shared data:** Imported by `skills/braingeneers-one/scripts/suite.py`.
- **Shared data:** Exposes classes from `loader.py`, `dumper.py`, `composer.py`, and `error.py`.

## Dependencies
None

## Classes
### YAMLObjectMetaclass(type)
> The metaclass for YAMLObject.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:347`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(cls, name, bases, kwds)`
**Key attributes:**
None
**Methods:**
None
### YAMLObject()
> An object that can dump itself to a YAML stream and load itself from a YAML stream.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:362`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
#### `from_yaml(cls, loader, node)`
> Convert a representation node to a Python object.
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:377`
#### `to_yaml(cls, dumper, data)`
> Convert a Python object to a representation node.
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:384`

## Functions
### `warnings(settings=None)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:24`
### `scan(stream, Loader=Loader)`
> Scan a YAML stream and produce scanning tokens.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:29`
### `parse(stream, Loader=Loader)`
> Parse a YAML stream and produce parsing events.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:40`
### `compose(stream, Loader=Loader)`
> Parse the first YAML document in a stream and produce the corresponding representation tree.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:51`
### `compose_all(stream, Loader=Loader)`
> Parse all YAML documents in a stream and produce corresponding representation trees.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:62`
### `load(stream, Loader)`
> Parses the first YAML document from a stream using the specified loader.
> **Called by:** skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:105 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:125 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:145 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:74`
### `load_all(stream, Loader)`
> Parse all YAML documents in a stream and produce corresponding Python objects.
> **Called by:** skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:115 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:135 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:155 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:85`
### `full_load(stream)`
> Parse the first YAML document in a stream and produce the corresponding Python object.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:97`
### `full_load_all(stream)`
> Parse all YAML documents in a stream and produce corresponding Python objects.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:107`
### `safe_load(stream)`
> Parses YAML using SafeLoader, restricting objects to standard safe types.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:117`
### `safe_load_all(stream)`
> Parse all YAML documents in a stream and produce corresponding Python objects.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:127`
### `unsafe_load(stream)`
> Parse the first YAML document in a stream and produce the corresponding Python object.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:137`
### `unsafe_load_all(stream)`
> Parse all YAML documents in a stream and produce corresponding Python objects.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:147`
### `emit(events, stream=None, Dumper=Dumper, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None)`
> Emit YAML parsing events into a stream. If stream is None, return the produced string instead.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:157`
### `serialize_all(nodes, stream=None, Dumper=Dumper, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None, encoding=None, explicit_start=None, explicit_end=None, version=None, tags=None)`
> Serialize a sequence of representation trees into a YAML stream. If stream is None, return the produced string instead.
> **Called by:** skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:213 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:178`
### `serialize(node, stream=None, Dumper=Dumper, **kwds)`
> Serialize a representation tree into a YAML stream. If stream is None, return the produced string instead.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:208`
### `dump_all(documents, stream=None, Dumper=Dumper, default_style=None, default_flow_style=False, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None, encoding=None, explicit_start=None, explicit_end=None, version=None, tags=None, sort_keys=True)`
> Serialize a sequence of Python objects into a YAML stream. If stream is None, return the produced string instead.
> **Called by:** skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:253 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:261 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:269 (named-call hint). **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:215`
### `dump(data, stream=None, Dumper=Dumper, **kwds)`
> Serializes a Python object hierarchy into a YAML document stream.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:248`
### `safe_dump_all(documents, stream=None, **kwds)`
> Serialize a sequence of Python objects into a YAML stream. Produce only basic YAML tags. If stream is None, return the produced string instead.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:255`
### `safe_dump(data, stream=None, **kwds)`
> Serializes standard Python objects to YAML using SafeDumper.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:263`
### `add_implicit_resolver(tag, regexp, first=None, Loader=None, Dumper=Dumper)`
> Add an implicit scalar detector. If an implicit scalar value matches the given regexp, the corresponding tag is assigned to the scalar. first is a sequence of possible initial characters or None.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:271`
### `add_path_resolver(tag, path, kind=None, Loader=None, Dumper=Dumper)`
> Add a path based resolver for the given tag. A path is a list of keys that forms a path to a node in the representation tree. Keys can be string values, integers, or None.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:287`
### `add_constructor(tag, constructor, Loader=None)`
> Add a constructor for the given tag. Constructor is a function that accepts a Loader instance and a node object and produces the corresponding Python object.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:302`
### `add_multi_constructor(tag_prefix, multi_constructor, Loader=None)`
> Add a multi-constructor for the given tag prefix. Multi-constructor is called for a node if its tag starts with tag_prefix. Multi-constructor accepts a Loader instance, a tag suffix, and a node object and produces the corresponding Python object.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:315`
### `add_representer(data_type, representer, Dumper=Dumper)`
> Add a representer for the given type. Representer is a function accepting a Dumper instance and an instance of the given data type and producing the corresponding representation node.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:329`
### `add_multi_representer(data_type, multi_representer, Dumper=Dumper)`
> Add a representer for the given type. Multi-representer is a function accepting a Dumper instance and an instance of the given data type or subtype and producing the corresponding representation node.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/__init__.py:338`

## Config / CLI
None

## Data Shapes
- Input/Output: YAML character streams or strings and equivalent native Python data structures (dicts, lists, scalars).

## Notes
- Vendored pure-Python PyYAML 6.0.3 used to guarantee reproducible YAML handling across environments without external C-extensions.

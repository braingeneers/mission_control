# dumper.py

**Path:** `skills/braingeneers-one/scripts/_vendor/yaml/dumper.py`
**Module:** `skills.braingeneers-one.scripts._vendor.yaml.dumper`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
PyYAML dumper composite classes uniting emitter, serializer, representer, and resolver components to serialize Python objects into YAML streams.

## Connections
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml` — import consumer hint; not a proven runtime call.
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.emitter` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.representer` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.resolver` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.serializer` — imports (static evidence).
- **Shared data:** Combines `Emitter`, `Serializer`, `Representer`, and `Resolver`.
- **Shared data:** Used by top-level `yaml.dump` and `yaml.safe_dump` in `__init__.py`.

## Dependencies
None

## Classes
### BaseDumper(Emitter, Serializer, BaseRepresenter, BaseResolver)
> Composite base dumper inheriting Emitter, Serializer, BaseRepresenter, and BaseResolver.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/dumper.py:9`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, stream, default_style=None, default_flow_style=False, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None, encoding=None, explicit_start=None, explicit_end=None, version=None, tags=None, sort_keys=True)`
**Key attributes:**
None
**Methods:**
None
### SafeDumper(Emitter, Serializer, SafeRepresenter, Resolver)
> Dumper restricting representation to standard YAML types.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/dumper.py:27`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, stream, default_style=None, default_flow_style=False, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None, encoding=None, explicit_start=None, explicit_end=None, version=None, tags=None, sort_keys=True)`
**Key attributes:**
None
**Methods:**
None
### Dumper(Emitter, Serializer, Representer, Resolver)
> Default dumper supporting standard and custom Python object serialization.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/dumper.py:45`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, stream, default_style=None, default_flow_style=False, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None, encoding=None, explicit_start=None, explicit_end=None, version=None, tags=None, sort_keys=True)`
**Key attributes:**
None
**Methods:**
None

## Functions
None

## Config / CLI
None

## Data Shapes
- Input: Python objects and destination output stream.
- Output: Formatted YAML character stream.

## Notes
- Defines `BaseDumper`, `SafeDumper`, and `Dumper` combining mixins via multiple inheritance.

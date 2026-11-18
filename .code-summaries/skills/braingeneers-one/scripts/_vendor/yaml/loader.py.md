# loader.py

**Path:** `skills/braingeneers-one/scripts/_vendor/yaml/loader.py`
**Module:** `skills.braingeneers-one.scripts._vendor.yaml.loader`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Defines composite loader classes (`BaseLoader`, `FullLoader`, `SafeLoader`, `Loader`, `UnsafeLoader`) combining reader, scanner, parser, composer, constructor, and resolver components.

## Connections
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml` — import consumer hint; not a proven runtime call.
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.composer` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.constructor` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.parser` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.reader` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.resolver` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.scanner` — imports (static evidence).
- **Shared data:** Composes `Reader`, `Scanner`, `Parser`, `Composer`, `Constructor`, `Resolver`.
- **Shared data:** Instantiated by `yaml.load` and `yaml.safe_load` in `__init__.py`.

## Dependencies
None

## Classes
### BaseLoader(Reader, Scanner, Parser, Composer, BaseConstructor, BaseResolver)
> Composite loader combining basic reader, scanner, parser, composer, and base constructor.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/loader.py:11`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, stream)`
**Key attributes:**
None
**Methods:**
None
### FullLoader(Reader, Scanner, Parser, Composer, FullConstructor, Resolver)
> Loader supporting extended Python types without arbitrary code execution.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/loader.py:21`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, stream)`
**Key attributes:**
None
**Methods:**
None
### SafeLoader(Reader, Scanner, Parser, Composer, SafeConstructor, Resolver)
> Loader restricted to safe standard YAML data types.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/loader.py:31`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, stream)`
**Key attributes:**
None
**Methods:**
None
### Loader(Reader, Scanner, Parser, Composer, Constructor, Resolver)
> Default PyYAML loader with full Python object construction capabilities.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/loader.py:41`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, stream)`
**Key attributes:**
None
**Methods:**
None
### UnsafeLoader(Reader, Scanner, Parser, Composer, Constructor, Resolver)
> unclear — see source
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/loader.py:55`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, stream)`
**Key attributes:**
None
**Methods:**
None

## Functions
None

## Config / CLI
None

## Data Shapes
- Input: Input character or byte stream.
- Output: Constructed Python data structures.

## Notes
- Uses multiple inheritance to compose the PyYAML parsing pipeline into unified loader interfaces.

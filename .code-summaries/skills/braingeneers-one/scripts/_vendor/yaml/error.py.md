# error.py

**Path:** `skills/braingeneers-one/scripts/_vendor/yaml/error.py`
**Module:** `skills.braingeneers-one.scripts._vendor.yaml.error`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Defines base exception hierarchy and source location marker (`Mark`) tracking line, column, snippet, and buffer index for precise YAML diagnostic messages.

## Connections
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.composer` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.constructor` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.emitter` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.parser` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.reader` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.representer` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.resolver` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.scanner` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.serializer` — import consumer hint; not a proven runtime call.
- **Shared data:** Imported by all PyYAML parsing, scanning, and composing components.

## Dependencies
None

## Classes
### Mark()
> Represents precise source file location coordinates with context snippet rendering.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/error.py:4`
**Kind:** class. **Instantiated by:** skills/braingeneers-one/scripts/_vendor/yaml/reader.py:116 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/reader.py:119 (named-call hint)
**Constructor:** `__init__(self, name, index, line, column, buffer, pointer)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `buffer` | inferred at runtime | `buffer` |
| `column` | inferred at runtime | `column` |
| `index` | inferred at runtime | `index` |
| `line` | inferred at runtime | `line` |
| `name` | inferred at runtime | `name` |
| `pointer` | inferred at runtime | `pointer` |
**Methods:**
#### `get_snippet(self, indent=4, max_length=75)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/error.py:14`
#### `__str__(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/error.py:37`
### YAMLError(Exception)
> Base exception class for all PyYAML errors.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/error.py:45`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None
### MarkedYAMLError(YAMLError)
> Structured exception rendering error messages with line/column markers.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/error.py:48`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, context=None, context_mark=None, problem=None, problem_mark=None, note=None)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `context` | inferred at runtime | `context` |
| `context_mark` | inferred at runtime | `context_mark` |
| `note` | inferred at runtime | `note` |
| `problem` | inferred at runtime | `problem` |
| `problem_mark` | inferred at runtime | `problem_mark` |
**Methods:**
#### `__str__(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/error.py:58`

## Functions
None

## Config / CLI
None

## Data Shapes
- `Mark`: Holds `name: str`, `index: int`, `line: int`, `column: int`, `buffer: str`, `pointer: int`.
- `MarkedYAMLError`: Exception storing context, context_mark, problem, problem_mark, note.

## Notes
- Standard PyYAML error reporting base class inherited across scanner, parser, composer, and constructor.

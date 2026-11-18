# reader.py

**Path:** `skills/braingeneers-one/scripts/_vendor/yaml/reader.py`
**Module:** `skills.braingeneers-one.scripts._vendor.yaml.reader`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Unicode input stream reader handling byte decoding, BOM detection, character filtering, lookahead buffering, and coordinate tracking (index, line, column).

## Connections
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.loader` — import consumer hint; not a proven runtime call.
- **Uses:** `Mark` from `skills.braingeneers-one.scripts._vendor.yaml.error` — imports (static evidence).
- **Uses:** `YAMLError` from `skills.braingeneers-one.scripts._vendor.yaml.error` — imports (static evidence).
- **Shared data:** Inherited by loaders in `loader.py`.
- **Shared data:** Uses `Mark` and `MarkedYAMLError` from `error.py`.

## Dependencies
None

## Classes
### ReaderError(YAMLError)
> Exception raised on encoding errors or illegal characters.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/reader.py:24`
**Kind:** class. **Instantiated by:** skills/braingeneers-one/scripts/_vendor/yaml/reader.py:143 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/reader.py:164 (named-call hint)
**Constructor:** `__init__(self, name, position, character, encoding, reason)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `character` | inferred at runtime | `character` |
| `encoding` | inferred at runtime | `encoding` |
| `name` | inferred at runtime | `name` |
| `position` | inferred at runtime | `position` |
| `reason` | inferred at runtime | `reason` |
**Methods:**
#### `__str__(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/reader.py:33`
### Reader(object)
> Low-level character buffer reader providing peek, forward, and coordinate tracking.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/reader.py:45`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, stream)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `buffer` | inferred at runtime | `''` |
| `column` | inferred at runtime | `0` |
| `encoding` | inferred at runtime | `None` |
| `eof` | inferred at runtime | `True` |
| `index` | inferred at runtime | `0` |
| `line` | inferred at runtime | `0` |
| `name` | inferred at runtime | `None` |
| `pointer` | inferred at runtime | `0` |
| `raw_buffer` | inferred at runtime | `None` |
| `raw_decode` | inferred at runtime | `None` |
| `stream` | inferred at runtime | `None` |
| `stream_pointer` | inferred at runtime | `0` |
**Methods:**
#### `peek(self, index=0)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/reader.py:87`
#### `prefix(self, length=1)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/reader.py:94`
#### `forward(self, length=1)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/reader.py:99`
#### `get_mark(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/reader.py:114`
#### `determine_encoding(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/reader.py:122`
#### `check_printable(self, data)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/reader.py:138`
#### `update(self, length)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/reader.py:146`
#### `update_raw(self, size=4096)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/reader.py:177`

## Functions
None

## Config / CLI
None

## Data Shapes
- Input: String or byte stream.
- Output: Stream of decoded Unicode characters with position coordinates.

## Notes
- Rejects non-printable and invalid control characters per YAML specification.
- Normalizes diverse newline conventions (CR, LF, CRLF) to standard line feeds.

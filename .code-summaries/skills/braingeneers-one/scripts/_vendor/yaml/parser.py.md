# parser.py

**Path:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py`
**Module:** `skills.braingeneers-one.scripts._vendor.yaml.parser`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Recursive descent event-driven parser transforming token streams from the scanner into high-level parsing events according to YAML grammar productions.

## Connections
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.loader` — import consumer hint; not a proven runtime call.
- **Uses:** `MarkedYAMLError` from `skills.braingeneers-one.scripts._vendor.yaml.error` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.events` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.scanner` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.tokens` — imports (static evidence).
- **Shared data:** Inherited by loaders in `loader.py`.
- **Shared data:** Consumes tokens from `tokens.py` and produces events from `events.py`.

## Dependencies
None

## Classes
### ParserError(MarkedYAMLError)
> Exception raised when input tokens violate YAML syntax grammar.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:69`
**Kind:** class. **Instantiated by:** skills/braingeneers-one/scripts/_vendor/yaml/parser.py:171 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/parser.py:224 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/parser.py:228 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/parser.py:235 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/parser.py:305 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/parser.py:369 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/parser.py:392 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/parser.py:438 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/parser.py:483 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/parser.py:549 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None
### Parser()
> State-machine grammar parser converting lexer tokens into structured events.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:72`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `current_event` | inferred at runtime | `None` |
| `marks` | inferred at runtime | `[]` |
| `state` | inferred at runtime | `self.parse_stream_start` |
| `states` | inferred at runtime | `[]` |
| `tag_handles` | inferred at runtime | `{}` |
| `yaml_version` | inferred at runtime | `None` |
**Methods:**
#### `dispose(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:89`
#### `check_event(self, *choices)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:94`
#### `peek_event(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:107`
#### `get_event(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:114`
#### `parse_stream_start(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:127`
#### `parse_implicit_document_start(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:139`
#### `parse_document_start(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:159`
#### `parse_document_end(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:190`
#### `parse_document_content(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:208`
#### `process_directives(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:217`
#### `parse_block_node(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:264`
#### `parse_flow_node(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:267`
#### `parse_block_node_or_indentless_sequence(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:270`
#### `parse_node(self, block=False, indentless_sequence=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:273`
#### `parse_block_sequence_first_entry(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:376`
#### `parse_block_sequence_entry(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:381`
#### `parse_indentless_sequence_entry(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:402`
#### `parse_block_mapping_first_key(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:422`
#### `parse_block_mapping_key(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:427`
#### `parse_block_mapping_value(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:446`
#### `parse_flow_sequence_first_entry(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:471`
#### `parse_flow_sequence_entry(self, first=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:476`
#### `parse_flow_sequence_entry_mapping_key(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:502`
#### `parse_flow_sequence_entry_mapping_value(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:512`
#### `parse_flow_sequence_entry_mapping_end(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:526`
#### `parse_flow_mapping_first_key(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:537`
#### `parse_flow_mapping_key(self, first=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:542`
#### `parse_flow_mapping_value(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:569`
#### `parse_flow_mapping_empty_value(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:583`
#### `process_empty_scalar(self, mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/parser.py:587`

## Functions
None

## Config / CLI
None

## Data Shapes
- Input: Token stream from `scanner.py`.
- Output: Event stream conforming to `events.py`.

## Notes
- Maintains parsing state stack transitioning between document, block, and flow grammar rules.

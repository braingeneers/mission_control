# scanner.py

**Path:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py`
**Module:** `skills.braingeneers-one.scripts._vendor.yaml.scanner`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Low-level lexical tokenizer and scanner scanning Unicode character streams into YAML tokens (directives, document markers, block/flow collections, keys, values, and scalars).

## Connections
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.loader` — import consumer hint; not a proven runtime call.
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.parser` — import consumer hint; not a proven runtime call.
- **Uses:** `MarkedYAMLError` from `skills.braingeneers-one.scripts._vendor.yaml.error` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.tokens` — imports (static evidence).
- **Shared data:** Inherited by loaders in `loader.py`.
- **Shared data:** Uses `tokens.py` and `error.py`.

## Dependencies
None

## Classes
### ScannerError(MarkedYAMLError)
> Exception raised on invalid character sequences or indentation errors.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:32`
**Kind:** class. **Instantiated by:** skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1067 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1074 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1087 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1101 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1213 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1223 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1238 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1261 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1354 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1365 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1393 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1405 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1413 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:258 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:291 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:318 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:491 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:524 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:577 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:815 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:822 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:833 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:839 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:848 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:872 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:881 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:894 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:922 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:929 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:944 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:970 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None
### SimpleKey()
> Tracks potential simple key tokens awaiting value colons.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:35`
**Kind:** class. **Instantiated by:** skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:308 (named-call hint)
**Constructor:** `__init__(self, token_number, required, index, line, column, mark)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `column` | inferred at runtime | `column` |
| `index` | inferred at runtime | `index` |
| `line` | inferred at runtime | `line` |
| `mark` | inferred at runtime | `mark` |
| `required` | inferred at runtime | `required` |
| `token_number` | inferred at runtime | `token_number` |
**Methods:**
None
### Scanner()
> Lexical analyzer breaking input characters into structured YAML tokens.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:46`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `allow_simple_key` | inferred at runtime | `True` |
| `done` | inferred at runtime | `False` |
| `flow_level` | inferred at runtime | `0` |
| `indent` | inferred at runtime | `-1` |
| `indents` | inferred at runtime | `[]` |
| `possible_simple_keys` | inferred at runtime | `{}` |
| `tokens` | inferred at runtime | `[]` |
| `tokens_taken` | inferred at runtime | `0` |
**Methods:**
#### `check_token(self, *choices)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:113`
#### `peek_token(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:125`
#### `get_token(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:135`
#### `need_more_tokens(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:145`
#### `fetch_more_tokens(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:156`
#### `next_possible_simple_key(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:264`
#### `stale_possible_simple_keys(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:279`
#### `save_possible_simple_key(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:295`
#### `remove_possible_simple_key(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:312`
#### `unwind_indent(self, column)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:325`
#### `add_indent(self, column)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:349`
#### `fetch_stream_start(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:359`
#### `fetch_stream_end(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:371`
#### `fetch_directive(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:390`
#### `fetch_document_start(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:402`
#### `fetch_document_end(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:405`
#### `fetch_document_indicator(self, TokenClass)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:408`
#### `fetch_flow_sequence_start(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:424`
#### `fetch_flow_mapping_start(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:427`
#### `fetch_flow_collection_start(self, TokenClass)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:430`
#### `fetch_flow_sequence_end(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:447`
#### `fetch_flow_mapping_end(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:450`
#### `fetch_flow_collection_end(self, TokenClass)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:453`
#### `fetch_flow_entry(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:470`
#### `fetch_block_entry(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:484`
#### `fetch_key(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:517`
#### `fetch_value(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:545`
#### `fetch_alias(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:601`
#### `fetch_anchor(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:612`
#### `fetch_tag(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:623`
#### `fetch_literal(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:634`
#### `fetch_folded(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:637`
#### `fetch_block_scalar(self, style)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:640`
#### `fetch_single(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:651`
#### `fetch_double(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:654`
#### `fetch_flow_scalar(self, style)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:657`
#### `fetch_plain(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:668`
#### `check_directive(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:683`
#### `check_document_start(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:690`
#### `check_document_end(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:698`
#### `check_block_entry(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:706`
#### `check_key(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:711`
#### `check_value(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:721`
#### `check_plain(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:731`
#### `scan_to_next_token(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:752`
#### `scan_directive(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:787`
#### `scan_directive_name(self, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:806`
#### `scan_yaml_directive_value(self, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:827`
#### `scan_yaml_directive_number(self, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:844`
#### `scan_tag_directive_value(self, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:857`
#### `scan_tag_directive_handle(self, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:867`
#### `scan_tag_directive_prefix(self, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:876`
#### `scan_directive_ignored_line(self, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:885`
#### `scan_anchor(self, TokenClass)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:899`
#### `scan_tag(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:935`
#### `scan_block_scalar(self, style)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:976`
#### `scan_block_scalar_indicators(self, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1052`
#### `scan_block_scalar_ignored_line(self, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1092`
#### `scan_block_scalar_indentation(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1106`
#### `scan_block_scalar_breaks(self, indent)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1121`
#### `scan_flow_scalar(self, style)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1134`
#### `scan_flow_scalar_non_spaces(self, double, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1185`
#### `scan_flow_scalar_spaces(self, double, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1228`
#### `scan_flow_scalar_breaks(self, double, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1252`
#### `scan_plain(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1270`
#### `scan_plain_spaces(self, indent, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1311`
#### `scan_tag_handle(self, name, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1348`
#### `scan_tag_uri(self, name, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1372`
#### `scan_uri_escapes(self, name, start_mark)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1397`
#### `scan_line_break(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/scanner.py:1416`

## Functions
None

## Config / CLI
None

## Data Shapes
- Input: Decoded character stream from `reader.py`.
- Output: Stream of `Token` instances (`ScalarToken`, `BlockSequenceStartToken`, etc.).

## Notes
- Manages indentation stack to distinguish indentation-sensitive YAML blocks from inline flow syntax.
- Handles simple keys and complex block scalar headers (chomping and indentation indicators).

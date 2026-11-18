# emitter.py

**Path:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py`
**Module:** `skills.braingeneers-one.scripts._vendor.yaml.emitter`
**Feature Area:** `skills`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Low-level YAML character stream emitter formatting parser events into formatted text with proper indentation, line wrapping, block/flow collection styles, and scalar quoting.

## Connections
- **Used by:** `skills.braingeneers-one.scripts._vendor.yaml.dumper` — import consumer hint; not a proven runtime call.
- **Uses:** `YAMLError` from `skills.braingeneers-one.scripts._vendor.yaml.error` — imports (static evidence).
- **Uses:** `*` from `skills.braingeneers-one.scripts._vendor.yaml.events` — imports (static evidence).
- **Shared data:** Inherited by `BaseDumper` in `dumper.py`.
- **Shared data:** Consumes event objects from `events.py`.

## Dependencies
None

## Classes
### EmitterError(YAMLError)
> Exception raised on invalid event sequencing or formatting state errors.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:14`
**Kind:** class. **Instantiated by:** skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:167 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:171 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:211 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:223 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:258 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:262 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:487 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:542 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:547 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:549 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:553 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:559 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:582 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:618 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:622 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None
### ScalarAnalysis()
> Dataclass recording scalar string characteristics (multiline, empty, special characters).
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:17`
**Kind:** class. **Instantiated by:** skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:630 (named-call hint); skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:778 (named-call hint)
**Constructor:** `__init__(self, scalar, empty, multiline, allow_flow_plain, allow_block_plain, allow_single_quoted, allow_double_quoted, allow_block)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `allow_block` | inferred at runtime | `allow_block` |
| `allow_block_plain` | inferred at runtime | `allow_block_plain` |
| `allow_double_quoted` | inferred at runtime | `allow_double_quoted` |
| `allow_flow_plain` | inferred at runtime | `allow_flow_plain` |
| `allow_single_quoted` | inferred at runtime | `allow_single_quoted` |
| `empty` | inferred at runtime | `empty` |
| `multiline` | inferred at runtime | `multiline` |
| `scalar` | inferred at runtime | `scalar` |
**Methods:**
None
### Emitter()
> State machine output formatter managing indentation levels, flow contexts, and character output.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:31`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** `__init__(self, stream, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None)`
**Key attributes:**
| Name | Type | Assignment / meaning |
| --- | --- | --- |
| `allow_unicode` | inferred at runtime | `allow_unicode` |
| `analysis` | inferred at runtime | `None` |
| `best_indent` | inferred at runtime | `2` |
| `best_line_break` | inferred at runtime | `'\n'` |
| `best_width` | inferred at runtime | `80` |
| `canonical` | inferred at runtime | `canonical` |
| `column` | inferred at runtime | `0` |
| `encoding` | inferred at runtime | `None` |
| `event` | inferred at runtime | `None` |
| `events` | inferred at runtime | `[]` |
| `flow_level` | inferred at runtime | `0` |
| `indent` | inferred at runtime | `None` |
| `indention` | inferred at runtime | `True` |
| `indents` | inferred at runtime | `[]` |
| `line` | inferred at runtime | `0` |
| `mapping_context` | inferred at runtime | `False` |
| `open_ended` | inferred at runtime | `False` |
| `prepared_anchor` | inferred at runtime | `None` |
| `prepared_tag` | inferred at runtime | `None` |
| `root_context` | inferred at runtime | `False` |
| `sequence_context` | inferred at runtime | `False` |
| `simple_key_context` | inferred at runtime | `False` |
| `state` | inferred at runtime | `self.expect_stream_start` |
| `states` | inferred at runtime | `[]` |
| `stream` | inferred at runtime | `stream` |
| `style` | inferred at runtime | `None` |
| `tag_prefixes` | inferred at runtime | `None` |
| `whitespace` | inferred at runtime | `True` |
**Methods:**
#### `dispose(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:106`
#### `emit(self, event)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:111`
#### `need_more_events(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:120`
#### `need_events(self, count)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:133`
#### `increase_indent(self, flow=False, indentless=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:146`
#### `expect_stream_start(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:160`
#### `expect_nothing(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:170`
#### `expect_first_document_start(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:175`
#### `expect_document_start(self, first=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:178`
#### `expect_document_end(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:214`
#### `expect_document_root(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:226`
#### `expect_node(self, root=False, sequence=False, mapping=False, simple_key=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:232`
#### `expect_alias(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:260`
#### `expect_scalar(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:266`
#### `expect_flow_sequence(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:274`
#### `expect_first_flow_sequence_item(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:280`
#### `expect_flow_sequence_item(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:292`
#### `expect_flow_mapping(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:310`
#### `expect_first_flow_mapping_key(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:316`
#### `expect_flow_mapping_key(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:333`
#### `expect_flow_mapping_simple_value(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:354`
#### `expect_flow_mapping_value(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:359`
#### `expect_block_sequence(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:368`
#### `expect_first_block_sequence_item(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:373`
#### `expect_block_sequence_item(self, first=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:376`
#### `expect_block_mapping(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:388`
#### `expect_first_block_mapping_key(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:392`
#### `expect_block_mapping_key(self, first=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:395`
#### `expect_block_mapping_simple_value(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:409`
#### `expect_block_mapping_value(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:414`
#### `check_empty_sequence(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:422`
#### `check_empty_mapping(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:426`
#### `check_empty_document(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:430`
#### `check_simple_key(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:437`
#### `process_anchor(self, indicator)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:459`
#### `process_tag(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:469`
#### `choose_scalar_style(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:494`
#### `process_scalar(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:515`
#### `prepare_version(self, version)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:539`
#### `prepare_tag_handle(self, handle)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:545`
#### `prepare_tag_prefix(self, prefix)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:557`
#### `prepare_tag(self, tag)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:580`
#### `prepare_anchor(self, anchor)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:616`
#### `analyze_scalar(self, scalar)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:626`
#### `flush_stream(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:788`
#### `write_stream_start(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** write call (static hint).
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:792`
#### `write_stream_end(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:797`
#### `write_indicator(self, indicator, need_whitespace, whitespace=False, indention=False)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state; write call (static hint).
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:800`
#### `write_indent(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state; write call (static hint).
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:814`
#### `write_line_break(self, data=None)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state; write call (static hint).
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:827`
#### `write_version_directive(self, version_text)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** write call (static hint).
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:838`
#### `write_tag_directive(self, handle_text, prefix_text)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** write call (static hint).
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:845`
#### `write_single_quoted(self, text, split=True)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state; write call (static hint).
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:854`
#### `write_double_quoted(self, text, split=True)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state; write call (static hint).
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:926`
#### `determine_block_hints(self, text)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:980`
#### `write_folded(self, text)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state; write call (static hint).
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:991`
#### `write_literal(self, text)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state; write call (static hint).
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:1045`
#### `write_plain(self, text, split=True)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state; write call (static hint).
**Source:** `skills/braingeneers-one/scripts/_vendor/yaml/emitter.py:1080`

## Functions
None

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Options: `canonical`, `indent`, `width`, `allow_unicode`, `line_break`. |

## Data Shapes
- Input: Stream of events (`ScalarEvent`, `SequenceStartEvent`, `MappingStartEvent`).
- Output: Stream writes to text/byte file-like stream object.

## Notes
- Handles literal, folded, single-quoted, double-quoted, and plain scalar presentation styles.
- Buffers states and events in internal queues before flushing to destination stream.

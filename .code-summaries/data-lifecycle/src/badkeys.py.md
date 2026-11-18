# badkeys.py

**Path:** `data-lifecycle/src/badkeys.py`
**Module:** `data-lifecycle.src.badkeys`
**Feature Area:** `data-lifecycle`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Defines data models, serialization utilities, and Slack formatting for recording problematic S3 bucket keys (control characters, unicode escaping, and HeadObject success followed by GetObject failure).

## Connections
- **Used by:** `data-lifecycle.src.generate_puts_deletes` — import consumer hint; not a proven runtime call.
- **Used by:** `data-lifecycle.src.stage4_process_puts_deletes` — import consumer hint; not a proven runtime call.
- **Shared data:** Imported by `generate_puts_deletes.py`, `stage4_process_puts_deletes.py`, and `analyze_two_run_check.py`.

## Dependencies
None

## Classes
### BadKeyRecord()
> Frozen dataclass modeling an invalid or failing S3 key and its failure category.
**Source:** `data-lifecycle/src/badkeys.py:21`
**Kind:** class. **Instantiated by:** data-lifecycle/src/badkeys.py:44 (named-call hint); data-lifecycle/src/badkeys.py:65 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None

## Functions
### `escape_bucket_key(bucket_key: str) -> str`
> Encodes key with `unicode_escape` to safely render in logs and TSVs.
> **Called by:** data-lifecycle/src/badkeys.py:46 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/badkeys.py:27`
### `unescape_bucket_key(bucket_key_escaped: str) -> str`
> Decodes unicode-escaped key back to original raw string.
> **Called by:** data-lifecycle/src/badkeys.py:68 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/badkeys.py:31`
### `describe_issue(issue: str) -> str`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/badkeys.py:38`
### `make_badkey_record(issue: str, bucket_key: str) -> BadKeyRecord`
> Instantiates a BadKeyRecord from an issue type and raw key.
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:233 (named-call hint); data-lifecycle/src/generate_puts_deletes.py:678 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:1009 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/badkeys.py:42`
### `parse_badkeys_tsv_text(tsv_text: str) -> list[BadKeyRecord]`
> unclear — see source
> **Called by:** data-lifecycle/src/badkeys.py:78 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/badkeys.py:51`
### `read_badkeys_tsv(path: str | os.PathLike[str]) -> list[BadKeyRecord]`
> Reads TSV file into a list of BadKeyRecord instances.
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:1017 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/badkeys.py:74`
### `dedupe_badkey_records(records: Iterable[BadKeyRecord]) -> list[BadKeyRecord]`
> unclear — see source
> **Called by:** data-lifecycle/src/badkeys.py:108 (named-call hint); data-lifecycle/src/badkeys.py:71 (named-call hint); data-lifecycle/src/badkeys.py:94 (named-call hint); data-lifecycle/src/badkeys.py:98 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/badkeys.py:81`
### `merge_badkey_records(*record_groups: Iterable[BadKeyRecord]) -> list[BadKeyRecord]`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:1017 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/badkeys.py:90`
### `write_badkeys_tsv(path: str | os.PathLike[str], records: Iterable[BadKeyRecord]) -> list[BadKeyRecord]`
> Writes BadKeyRecord collection to a tab-separated file.
> **Called by:** data-lifecycle/src/generate_puts_deletes.py:683 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:1018 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/src/badkeys.py:97`
### `source_get_failed_records(records: Iterable[BadKeyRecord]) -> list[BadKeyRecord]`
> unclear — see source
> **Called by:** data-lifecycle/src/badkeys.py:117 (named-call hint); data-lifecycle/src/stage4_process_puts_deletes.py:1020 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/badkeys.py:105`
### `render_source_get_failed_slack_section(records: Iterable[BadKeyRecord], max_examples: int=5) -> str`
> Formats Slack markdown blocks for HeadObject success/GetObject missing issues.
> **Called by:** data-lifecycle/src/badkeys.py:146 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/badkeys.py:113`
### `append_source_get_failed_slack_section(slack_message: str, records: Iterable[BadKeyRecord], max_examples: int=5) -> str`
> unclear — see source
> **Called by:** data-lifecycle/src/stage4_process_puts_deletes.py:1024 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/badkeys.py:141`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| Env `CONTROL_CHARACTER_ISSUE`: Label for keys rejected due to ASCII/Unicode control characters. |
| Env `SOURCE_GET_FAILED_AFTER_HEAD_SUCCESS`: Label for keys visible via HeadObject but missing upon GetObject. |

## Data Shapes
- Input/Output TSV: Tab-separated values with columns `issue`, `bucket_key_escaped`, `bucket_key`.
- `BadKeyRecord`: Dataclass containing `issue: str`, `bucket_key_escaped: str`, `bucket_key: str`.

## Notes
- Escapes control characters and unusual characters using ASCII `unicode_escape`.
- Renders markdown blocks for reporting failed keys directly into Slack incident channels.

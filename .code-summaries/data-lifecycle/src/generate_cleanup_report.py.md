# generate_cleanup_report.py

**Path:** `data-lifecycle/src/generate_cleanup_report.py`
**Module:** `data-lifecycle.src.generate_cleanup_report`
**Feature Area:** `data-lifecycle`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Generates the monthly data-retention report bundle including interactive HTML, multipage PDF summary charts, Slack notification payload, and retention candidate CSV from scientific and backup inventories.

## Connections
- **Uses:** `apply_last_modified_updates` from `data-lifecycle.src.generate_puts_deletes` — imports (static evidence).
- **Uses:** `build_cleanup_window_entries` from `data-lifecycle.src.generate_puts_deletes` — imports (static evidence).
- **Uses:** `load_config_file` from `data-lifecycle.src.generate_puts_deletes` — imports (static evidence).
- **Uses:** `load_inventories` from `data-lifecycle.src.generate_puts_deletes` — imports (static evidence).
- **Uses:** `DEFAULT_COST_PER_GB_MONTH` from `data-lifecycle.src.glacier_cost_analysis_plot` — imports (static evidence).
- **Uses:** `DEFAULT_PER_OBJECT_OVERHEAD_BYTES` from `data-lifecycle.src.glacier_cost_analysis_plot` — imports (static evidence).
- **Uses:** `build_retention_points` from `data-lifecycle.src.glacier_cost_analysis_plot` — imports (static evidence).
- **Uses:** `parse_inventory_summary` from `data-lifecycle.src.glacier_cost_analysis_plot` — imports (static evidence).
- **Shared data:** Imports `load_inventories`, `load_config_file`, and `build_cleanup_window_entries` from `generate_puts_deletes.py`.
- **Shared data:** Imports cost projection formulas and `build_retention_points` from `glacier_cost_analysis_plot.py`.

## Dependencies
- `matplotlib` — external or unresolved local import; source import evidence.
- `matplotlib.backends.backend_pdf.PdfPages` — external or unresolved local import; source import evidence.
- `matplotlib.patches.FancyBboxPatch` — external or unresolved local import; source import evidence.
- `matplotlib.patches.Rectangle` — external or unresolved local import; source import evidence.
- `matplotlib.pyplot` — external or unresolved local import; source import evidence.
- `pandas` — external or unresolved local import; source import evidence.

## Classes
None

## Functions
### `parse_args() -> argparse.Namespace`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:709 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:61`
### `candidate_identifier(row: dict[str, object]) -> str`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:124 (named-call hint); data-lifecycle/src/generate_cleanup_report.py:146 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:77`
### `deep_link(base_url: str, phase: str, grouping_type: str, grouping_key: str, bucket_key: str, candidate_id: str) -> str`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:125 (named-call hint); data-lifecycle/src/generate_cleanup_report.py:147 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:85`
### `build_candidates(cleanup: pd.DataFrame, base_url: str) -> list[dict[str, object]]`
> Extracts datasets and objects eligible for cleanup within the current retention policy window.
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:652 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:108`
### `write_candidates_csv(path: Path, candidates: list[dict[str, object]]) -> None`
> Dumps candidate records to CSV with path, size, date, and atomic group tags.
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:659 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:161`
### `cost_appendix(glacier_inventory: Path, output: Path, as_of: datetime, current_days: int) -> list[dict[str, object]]`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:653 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:180`
### `render_html(path: Path, run_id: str, generated_at: datetime, candidates: list[dict[str, object]], cost_rows: list[dict[str, object]]) -> None`
> Builds standalone HTML report with candidate tables and policy breakdown.
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:671 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/src/generate_cleanup_report.py:208`
### `_candidate_path_parts(candidate: dict[str, object]) -> list[str]`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:249 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:243`
### `compact_candidate_names(candidates: list[dict[str, object]]) -> list[str]`
> Return the shortest unique trailing path for each candidate.
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:318 (named-call hint); data-lifecycle/src/generate_cleanup_report.py:585 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:247`
### `_display_date(value: object) -> str`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:362 (named-call hint); data-lifecycle/src/generate_cleanup_report.py:363 (named-call hint); data-lifecycle/src/generate_cleanup_report.py:422 (named-call hint); data-lifecycle/src/generate_cleanup_report.py:581 (named-call hint); data-lifecycle/src/generate_cleanup_report.py:582 (named-call hint); data-lifecycle/src/generate_cleanup_report.py:589 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:266`
### `_candidate_source(candidate: dict[str, object]) -> str`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:423 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:271`
### `_shorten_middle(value: str, limit: int) -> str`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:424 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:275`
### `_object_count_label(value: object) -> str`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:592 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:282`
### `_pdf_footer(figure, page_number: int, page_count: int) -> None`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:401 (named-call hint); data-lifecycle/src/generate_cleanup_report.py:464 (named-call hint); data-lifecycle/src/generate_cleanup_report.py:546 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:287`
### `render_pdf(path: Path, generated_at: datetime, candidates: list[dict[str, object]], cost_rows: list[dict[str, object]]) -> None`
> Renders multipage PDF report containing summary metrics, cost analysis charts, and top cleanup items.
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:672 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/src/generate_cleanup_report.py:302`
### `_slack_text(value: object) -> str`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:556 (named-call hint); data-lifecycle/src/generate_cleanup_report.py:557 (named-call hint); data-lifecycle/src/generate_cleanup_report.py:590 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:551`
### `_slack_link(url: str, label: str) -> str`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:577 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:555`
### `render_slack_summary(path: Path, generated_at: datetime, candidates: list[dict[str, object]], report_url: str) -> None`
> Generates JSON payload for Slack webhook notifying team of pending cleanups.
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:675 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/src/generate_cleanup_report.py:560`
### `main(args: argparse.Namespace) -> None`
> CLI driver for the monthly cleanup reporting bundle generation.
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:709 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/src/generate_cleanup_report.py:616`
### `_iso(value: datetime) -> str`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:685 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/generate_cleanup_report.py:704`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| `--config PATH`: Path to `data-lifecycle.yaml` configuration file. |
| `--scientific-inventory PATH`: S3 inventory manifest or CSV of primary storage. |
| `--backup-inventory PATH`: S3 inventory manifest or CSV of Glacier backup storage. |
| `--output-dir PATH`: Directory where generated reports and artifacts are saved. |
| `--as-of-date YYYY-MM-DD`: Effective evaluation date for retention policy. |

## Data Shapes
- Input: Scientific and backup S3 inventories (CSV or gzip-compressed CSV).
- Output: `retention_candidates.csv`, `retention_report.html`, `retention_summary.pdf`, `slack_summary.json`.

## Notes
- Uses `matplotlib.backends.backend_pdf.PdfPages` to render PDF slides with custom styled tables and cost graphs.
- Deep links candidate datasets to MinIO/Ceph browser or AWS S3 console.

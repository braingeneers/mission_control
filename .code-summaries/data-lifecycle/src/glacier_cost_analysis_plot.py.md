# glacier_cost_analysis_plot.py

**Path:** `data-lifecycle/src/glacier_cost_analysis_plot.py`
**Module:** `data-lifecycle.src.glacier_cost_analysis_plot`
**Feature Area:** `data-lifecycle`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Plots estimated AWS Glacier storage costs vs retention policy duration in years, computing cumulative retained volumes and projecting monthly expenses from Ceph/S3 inventory files.

## Connections
- **Used by:** `data-lifecycle.src.generate_cleanup_report` — import consumer hint; not a proven runtime call.
- **Shared data:** Imported by `generate_cleanup_report.py` for retention point modeling and cost calculations.
- **Shared data:** Fetches inventory files from Ceph/S3 via boto3.

## Dependencies
- `boto3` — external or unresolved local import; source import evidence.
- `matplotlib` — external or unresolved local import; source import evidence.
- `matplotlib.pyplot` — external or unresolved local import; source import evidence.
- `matplotlib.ticker.FuncFormatter` — external or unresolved local import; source import evidence.
- `yaml` — external or unresolved local import; source import evidence.

## Classes
### RetentionPoint()
> Dataclass holding retention year cutoff, object count, total bytes, and estimated monthly cost.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:53`
**Kind:** class. **Instantiated by:** data-lifecycle/src/glacier_cost_analysis_plot.py:381 (named-call hint); data-lifecycle/src/glacier_cost_analysis_plot.py:433 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None
### InventorySummary()
> Dataclass representing aggregated object counts, total volume, and date bounds from an inventory.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:265`
**Kind:** class. **Instantiated by:** data-lifecycle/src/glacier_cost_analysis_plot.py:325 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None

## Functions
### `parse_args() -> argparse.Namespace`
> unclear — see source
> **Called by:** data-lifecycle/src/glacier_cost_analysis_plot.py:657 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:63`
### `parse_s3_uri(uri: str) -> tuple[str, str]`
> unclear — see source
> **Called by:** data-lifecycle/src/glacier_cost_analysis_plot.py:187 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:165`
### `resolve_nrp_endpoint(cli_value: str | None) -> str`
> unclear — see source
> **Called by:** data-lifecycle/src/glacier_cost_analysis_plot.py:678 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:175`
### `make_s3_client(region: str, profile: str | None, endpoint_url: str | None)`
> unclear — see source
> **Called by:** data-lifecycle/src/glacier_cost_analysis_plot.py:682 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:179`
### `list_inventory_candidates(s3_client, inventory_s3_uri: str) -> tuple[str, list[dict]]`
> unclear — see source
> **Called by:** data-lifecycle/src/glacier_cost_analysis_plot.py:211 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:186`
### `download_inventory_from_s3(s3_client, inventory_s3_uri: str) -> tuple[Path, str, datetime]`
> unclear — see source
> **Called by:** data-lifecycle/src/glacier_cost_analysis_plot.py:687 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:208`
### `open_inventory_text(path: Path)`
> unclear — see source
> **Called by:** data-lifecycle/src/glacier_cost_analysis_plot.py:288 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:229`
### `parse_inventory_timestamp(text: str) -> datetime`
> unclear — see source
> **Called by:** data-lifecycle/src/glacier_cost_analysis_plot.py:298 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:235`
### `parse_local_inventory_timestamp(text: str) -> datetime`
> unclear — see source
> **Called by:** data-lifecycle/src/glacier_cost_analysis_plot.py:302 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:240`
### `load_cold_storage_expire_days(config_path: Path) -> int | None`
> unclear — see source
> **Called by:** data-lifecycle/src/glacier_cost_analysis_plot.py:704 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:248`
### `parse_inventory_summary(path: Path) -> InventorySummary`
> unclear — see source
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:181 (named-call hint); data-lifecycle/src/glacier_cost_analysis_plot.py:692 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:277`
### `build_retention_points(summary: InventorySummary, as_of: date, years: Iterable[int], cost_per_gb_month: float, per_object_overhead_bytes: int) -> list[RetentionPoint]`
> Calculates retained volume and cost projections across 1 to 10 year retention windows.
> **Called by:** data-lifecycle/src/generate_cleanup_report.py:182 (named-call hint); data-lifecycle/src/glacier_cost_analysis_plot.py:402 (named-call hint); data-lifecycle/src/glacier_cost_analysis_plot.py:696 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:338`
### `compute_single_retention_point(summary: InventorySummary, as_of: date, retention_days: int, cost_per_gb_month: float, per_object_overhead_bytes: int) -> RetentionPoint`
> unclear — see source
> **Called by:** data-lifecycle/src/glacier_cost_analysis_plot.py:707 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:394`
### `fmt_tib(value: float, _pos=None) -> str`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:444`
### `fmt_usd(value: float, _pos=None) -> str`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:448`
### `write_summary_csv(points: list[RetentionPoint], path: Path) -> None`
> unclear — see source
> **Called by:** data-lifecycle/src/glacier_cost_analysis_plot.py:717 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:456`
### `plot_retention_analysis(points: list[RetentionPoint], output_png: Path, title: str, cost_per_gb_month: float, per_object_overhead_bytes: int, as_of: date, inventory_label: str, inventory_last_modified: datetime | None, summary: InventorySummary, current_policy_point: RetentionPoint | None=None) -> None`
> Renders dual-axis Matplotlib chart showing storage volume (TiB) and monthly bill ($) vs years.
> **Called by:** data-lifecycle/src/glacier_cost_analysis_plot.py:718 (named-call hint). **Side effects:** write call (static hint).
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:485`
### `coerce_as_of_date(text: str | None) -> date`
> unclear — see source
> **Called by:** data-lifecycle/src/glacier_cost_analysis_plot.py:665 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:650`
### `main() -> int`
> CLI entry point parsing arguments and generating cost analysis plot and CSV.
> **Called by:** data-lifecycle/src/glacier_cost_analysis_plot.py:759 (named-call hint). **Side effects:** unclear — see source.
**Source:** `data-lifecycle/src/glacier_cost_analysis_plot.py:656`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| `--inventory-path PATH`: Local path or S3 URI to `local_inventory.csv(.gz)`. |
| `--output-plot PATH`: Output image path for generated cost curve plot (PNG/PDF). |
| `--output-csv PATH`: Path to write tabulated cost projection CSV. |
| `--cost-per-gb-month USD`: Configured Glacier pricing rate (default: `0.0036`). |
| `--as-of-date YYYY-MM-DD`: Baseline date for calculating retention age. |

## Data Shapes
- Input: Inventory CSV/GZIP with columns `Bucket`, `Key`, `Size`, `LastModifiedDate`.
- Output: Tabular CSV (`retention_years`, `retained_tb`, `monthly_cost_usd`) and Matplotlib cost curve plot.

## Notes
- Reads `cold_storage_expire_days` from `src/data-lifecycle.yaml` to mark current retention threshold on chart.
- Accounts for AWS per-object metadata storage overhead (32KB per object) in pricing calculations.

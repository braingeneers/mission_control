#!/usr/bin/env python3
"""Plot estimated AWS/Glacier storage cost vs retention-policy years.

Default behavior:
1. Fetch `local_inventory.csv(.gz)` from the configured Braingeneers Ceph/S3 inventory path.
2. Parse object sizes and last-modified timestamps from the inventory.
3. Compute retained storage for hypothetical retention windows (1-10 years).
4. Overlay estimated monthly cost using a configurable USD/GB-month rate.

The script also reads `src/data-lifecycle.yaml` to highlight the current
`deletion.cold_storage_expire_days` policy on the chart.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import os
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import boto3
import matplotlib
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402


DEFAULT_INVENTORY_S3_URI = "s3://braingeneers/services/data-lifecycle/inventory/local_inventory.csv.gz"
DEFAULT_NRP_ENDPOINT = "https://s3.braingeneers.gi.ucsc.edu"
DEFAULT_POLICY_CONFIG = Path("src/data-lifecycle.yaml")
DEFAULT_OUTPUT_PNG = Path("tmp/glacier_cost_analysis.png")
DEFAULT_OUTPUT_CSV = Path("tmp/glacier_cost_analysis_summary.csv")

# AWS S3 Glacier Deep Archive storage price in US West (Oregon), USD per GB-month.
# Source checked on 2026-02-23. Keep overrideable via CLI.
DEFAULT_COST_PER_GB_MONTH = 0.00099

# AWS archive classes incur 40 KB metadata overhead (8 KB at Standard + 32 KB archive).
# This is included by default for a closer billed-storage estimate and can be disabled.
DEFAULT_PER_OBJECT_OVERHEAD_BYTES = 40 * 1024


@dataclass(frozen=True)
class RetentionPoint:
    retention_years: float
    retention_days: int
    retained_objects: int
    retained_bytes: int
    retained_gb_decimal: float
    retained_tib_binary: float
    monthly_cost_usd: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Visualize AWS/Glacier retained storage and estimated monthly cost "
            "as a function of retention policy length."
        )
    )
    parser.add_argument(
        "--inventory-s3-uri",
        default=DEFAULT_INVENTORY_S3_URI,
        help=(
            "S3-compatible inventory URI (object or prefix). Defaults to local_inventory "
            "in the Braingeneers lifecycle inventory path: "
            f"(default: {DEFAULT_INVENTORY_S3_URI})"
        ),
    )
    parser.add_argument(
        "--inventory-file",
        help=(
            "Local inventory CSV/CSV.GZ file (optional; skips S3 fetch). Supports local_inventory "
            "format and AWS inventory format."
        ),
    )
    parser.add_argument(
        "--policy-config",
        default=str(DEFAULT_POLICY_CONFIG),
        help=f"Path to data-lifecycle YAML for current-policy marker (default: {DEFAULT_POLICY_CONFIG})",
    )
    parser.add_argument(
        "--aws-profile",
        help="Optional AWS/credential profile for reading the inventory S3-compatible prefix.",
    )
    parser.add_argument(
        "--aws-region",
        default="us-west-2",
        help="Region sent to boto3 S3 client (default: us-west-2).",
    )
    parser.add_argument(
        "--s3-endpoint",
        help=(
            "S3-compatible endpoint for the inventory prefix. Defaults to "
            "NRP_ENDPOINT, then ENDPOINT, then https://s3.braingeneers.gi.ucsc.edu"
        ),
    )
    parser.add_argument(
        "--cost-per-gb-month",
        type=float,
        default=DEFAULT_COST_PER_GB_MONTH,
        help=(
            "Estimated storage price in USD per GB-month used for monthly cost "
            f"(default: {DEFAULT_COST_PER_GB_MONTH:.5f}, US West/Oregon Deep Archive)."
        ),
    )
    parser.add_argument(
        "--per-object-overhead-bytes",
        type=int,
        default=DEFAULT_PER_OBJECT_OVERHEAD_BYTES,
        help=(
            "Additional billed bytes per object (default: 40960 for AWS archive metadata overhead). "
            "Set 0 to disable."
        ),
    )
    parser.add_argument(
        "--min-years",
        type=int,
        default=1,
        help="Minimum retention window in years (default: 1).",
    )
    parser.add_argument(
        "--max-years",
        type=int,
        default=10,
        help="Maximum retention window in years (default: 10).",
    )
    parser.add_argument(
        "--year-step",
        type=int,
        default=1,
        help="Step size in years for sampled retention windows (default: 1).",
    )
    parser.add_argument(
        "--as-of-date",
        help="Reference date for retention calculations (YYYY-MM-DD). Defaults to current UTC date.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PNG),
        help=f"Output PNG path (default: {DEFAULT_OUTPUT_PNG})",
    )
    parser.add_argument(
        "--output-csv",
        default=str(DEFAULT_OUTPUT_CSV),
        help=f"Output summary CSV path (default: {DEFAULT_OUTPUT_CSV})",
    )
    parser.add_argument(
        "--title",
        default="Estimated AWS/Glacier Cost vs Retention Policy (from local inventory)",
        help="Plot title.",
    )
    return parser.parse_args()


def parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Expected s3:// URI, got: {uri}")
    bucket_and_key = uri[5:]
    bucket, _, key = bucket_and_key.partition("/")
    if not bucket:
        raise ValueError(f"Missing bucket in S3 URI: {uri}")
    return bucket, key


def resolve_nrp_endpoint(cli_value: str | None) -> str:
    return cli_value or os.getenv("NRP_ENDPOINT") or os.getenv("ENDPOINT") or DEFAULT_NRP_ENDPOINT


def make_s3_client(region: str, profile: str | None, endpoint_url: str | None):
    if profile:
        session = boto3.Session(profile_name=profile, region_name=region)
        return session.client("s3", endpoint_url=endpoint_url)
    return boto3.client("s3", region_name=region, endpoint_url=endpoint_url)


def list_inventory_candidates(s3_client, inventory_s3_uri: str) -> tuple[str, list[dict]]:
    bucket, prefix = parse_s3_uri(inventory_s3_uri)
    paginator = s3_client.get_paginator("list_objects_v2")
    objects: list[dict] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            objects.append(obj)

    if not objects:
        raise FileNotFoundError(f"No objects found under {inventory_s3_uri}")

    preferred = [o for o in objects if o["Key"].endswith(".csv.gz") or o["Key"].endswith(".csv")]
    if preferred:
        objects = preferred

    objects.sort(key=lambda o: (o["LastModified"], o["Key"]))
    return bucket, objects


def download_inventory_from_s3(
    s3_client, inventory_s3_uri: str
) -> tuple[Path, str, datetime]:
    bucket, objects = list_inventory_candidates(s3_client, inventory_s3_uri)
    latest = objects[-1]
    key = latest["Key"]
    if len(objects) != 1:
        print(
            f"[info] Found {len(objects)} candidate objects under {inventory_s3_uri}; "
            f"using latest by LastModified: s3://{bucket}/{key}",
            file=sys.stderr,
        )

    suffix = ".csv.gz" if key.endswith(".csv.gz") else ".csv"
    tmp = tempfile.NamedTemporaryFile(prefix="aws_inventory_", suffix=suffix, delete=False)
    tmp_path = Path(tmp.name)
    with tmp:
        s3_client.download_fileobj(bucket, key, tmp)
    return tmp_path, f"s3://{bucket}/{key}", latest["LastModified"]


def open_inventory_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", newline="", encoding="utf-8")
    return path.open("rt", newline="", encoding="utf-8")


def parse_inventory_timestamp(text: str) -> datetime:
    # AWS inventory timestamps look like "2023-05-25T22:35:45.000Z"
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def parse_local_inventory_timestamp(text: str) -> datetime:
    # local_inventory timestamps look like "2025-05-19T18:51:44+00:00"
    ts = datetime.fromisoformat(text)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def load_cold_storage_expire_days(config_path: Path) -> int | None:
    if not config_path.exists():
        print(f"[warn] Policy config not found: {config_path}", file=sys.stderr)
        return None
    with config_path.open("rt", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    try:
        return int(config["deletion"]["cold_storage_expire_days"])
    except Exception:
        print(
            f"[warn] Could not read deletion.cold_storage_expire_days from {config_path}",
            file=sys.stderr,
        )
        return None


@dataclass
class InventorySummary:
    bytes_by_day: dict[date, int]
    count_by_day: dict[date, int]
    row_count: int
    skipped_rows: int
    min_ts: datetime | None
    max_ts: datetime | None
    storage_class_counts: Counter
    storage_class_bytes: Counter
    detected_format: str | None


def parse_inventory_summary(path: Path) -> InventorySummary:
    bytes_by_day: dict[date, int] = defaultdict(int)
    count_by_day: dict[date, int] = defaultdict(int)
    storage_class_counts: Counter = Counter()
    storage_class_bytes: Counter = Counter()
    row_count = 0
    skipped_rows = 0
    min_ts: datetime | None = None
    max_ts: datetime | None = None
    detected_format: str | None = None

    with open_inventory_text(path) as f:
        reader = csv.reader(f)
        for row in reader:
            row_count += 1
            try:
                # Auto-detect supported formats:
                # - local_inventory: LastModified,BucketKey,Size
                # - AWS inventory: Bucket,Key,Size,LastModified,StorageClass,...
                if len(row) >= 5:
                    size_bytes = int(row[2])
                    ts = parse_inventory_timestamp(row[3])
                    storage_class = row[4].strip() or "UNKNOWN"
                    row_format = "aws_inventory"
                elif len(row) >= 3:
                    ts = parse_local_inventory_timestamp(row[0])
                    size_bytes = int(row[2])
                    storage_class = "LOCAL_INVENTORY"
                    row_format = "local_inventory"
                else:
                    skipped_rows += 1
                    continue
            except Exception:
                skipped_rows += 1
                continue
            if detected_format is None:
                detected_format = row_format

            day = ts.date()
            bytes_by_day[day] += size_bytes
            count_by_day[day] += 1
            storage_class_counts[storage_class] += 1
            storage_class_bytes[storage_class] += size_bytes
            if min_ts is None or ts < min_ts:
                min_ts = ts
            if max_ts is None or ts > max_ts:
                max_ts = ts

    return InventorySummary(
        bytes_by_day=dict(bytes_by_day),
        count_by_day=dict(count_by_day),
        row_count=row_count,
        skipped_rows=skipped_rows,
        min_ts=min_ts,
        max_ts=max_ts,
        storage_class_counts=storage_class_counts,
        storage_class_bytes=storage_class_bytes,
        detected_format=detected_format,
    )


def build_retention_points(
    summary: InventorySummary,
    as_of: date,
    years: Iterable[int],
    cost_per_gb_month: float,
    per_object_overhead_bytes: int,
) -> list[RetentionPoint]:
    if not summary.bytes_by_day:
        return []

    sorted_days = sorted(summary.bytes_by_day)
    n = len(sorted_days)
    day_bytes = [summary.bytes_by_day[d] for d in sorted_days]
    day_counts = [summary.count_by_day.get(d, 0) for d in sorted_days]

    suffix_bytes = [0] * (n + 1)
    suffix_counts = [0] * (n + 1)
    for i in range(n - 1, -1, -1):
        suffix_bytes[i] = suffix_bytes[i + 1] + day_bytes[i]
        suffix_counts[i] = suffix_counts[i + 1] + day_counts[i]

    points: list[RetentionPoint] = []
    for years_value in years:
        retention_days = int(round(years_value * 365.25))
        cutoff_date = as_of - timedelta(days=retention_days)

        # First date that is still retained (>= cutoff_date).
        lo, hi = 0, n
        while lo < hi:
            mid = (lo + hi) // 2
            if sorted_days[mid] < cutoff_date:
                lo = mid + 1
            else:
                hi = mid
        idx = lo

        retained_bytes = suffix_bytes[idx]
        retained_objects = suffix_counts[idx]
        billed_bytes = retained_bytes + retained_objects * max(0, per_object_overhead_bytes)
        retained_gb_decimal = billed_bytes / 1_000_000_000.0
        retained_tib_binary = billed_bytes / float(1 << 40)
        monthly_cost_usd = retained_gb_decimal * cost_per_gb_month
        points.append(
            RetentionPoint(
                retention_years=float(years_value),
                retention_days=retention_days,
                retained_objects=retained_objects,
                retained_bytes=billed_bytes,
                retained_gb_decimal=retained_gb_decimal,
                retained_tib_binary=retained_tib_binary,
                monthly_cost_usd=monthly_cost_usd,
            )
        )
    return points


def compute_single_retention_point(
    summary: InventorySummary,
    as_of: date,
    retention_days: int,
    cost_per_gb_month: float,
    per_object_overhead_bytes: int,
) -> RetentionPoint:
    years_value = retention_days / 365.25
    points = build_retention_points(
        summary,
        as_of=as_of,
        years=[max(0, int(round(years_value)))],
        cost_per_gb_month=cost_per_gb_month,
        per_object_overhead_bytes=per_object_overhead_bytes,
    )
    # build_retention_points rounds years -> days, so compute exact retention_days separately.
    # Reuse the same binary-search logic with a direct cutoff for an exact marker.
    sorted_days = sorted(summary.bytes_by_day)
    n = len(sorted_days)
    day_bytes = [summary.bytes_by_day[d] for d in sorted_days]
    day_counts = [summary.count_by_day.get(d, 0) for d in sorted_days]
    suffix_bytes = [0] * (n + 1)
    suffix_counts = [0] * (n + 1)
    for i in range(n - 1, -1, -1):
        suffix_bytes[i] = suffix_bytes[i + 1] + day_bytes[i]
        suffix_counts[i] = suffix_counts[i + 1] + day_counts[i]
    cutoff_date = as_of - timedelta(days=retention_days)
    lo, hi = 0, n
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_days[mid] < cutoff_date:
            lo = mid + 1
        else:
            hi = mid
    idx = lo
    retained_bytes = suffix_bytes[idx]
    retained_objects = suffix_counts[idx]
    billed_bytes = retained_bytes + retained_objects * max(0, per_object_overhead_bytes)
    retained_gb_decimal = billed_bytes / 1_000_000_000.0
    return RetentionPoint(
        retention_years=retention_days / 365.25,
        retention_days=retention_days,
        retained_objects=retained_objects,
        retained_bytes=billed_bytes,
        retained_gb_decimal=retained_gb_decimal,
        retained_tib_binary=billed_bytes / float(1 << 40),
        monthly_cost_usd=retained_gb_decimal * cost_per_gb_month,
    )


def fmt_tib(value: float, _pos=None) -> str:
    return f"{value:,.1f} TiB"


def fmt_usd(value: float, _pos=None) -> str:
    if abs(value) >= 1000:
        return f"${value:,.0f}"
    if abs(value) >= 100:
        return f"${value:,.1f}"
    return f"${value:,.2f}"


def write_summary_csv(points: list[RetentionPoint], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wt", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "retention_years",
                "retention_days",
                "retained_objects",
                "retained_bytes_billed",
                "retained_gb_decimal_billed",
                "retained_tib_binary_billed",
                "monthly_cost_usd",
            ]
        )
        for p in points:
            writer.writerow(
                [
                    f"{p.retention_years:.2f}",
                    p.retention_days,
                    p.retained_objects,
                    p.retained_bytes,
                    f"{p.retained_gb_decimal:.6f}",
                    f"{p.retained_tib_binary:.6f}",
                    f"{p.monthly_cost_usd:.6f}",
                ]
            )


def plot_retention_analysis(
    points: list[RetentionPoint],
    output_png: Path,
    title: str,
    cost_per_gb_month: float,
    per_object_overhead_bytes: int,
    as_of: date,
    inventory_label: str,
    inventory_last_modified: datetime | None,
    summary: InventorySummary,
    current_policy_point: RetentionPoint | None = None,
) -> None:
    if not points:
        raise ValueError("No data points to plot.")

    years = [p.retention_years for p in points]
    tib = [p.retained_tib_binary for p in points]
    tib_to_usd_factor = (float(1 << 40) / 1_000_000_000.0) * cost_per_gb_month

    plt.rcParams.update(
        {
            "figure.facecolor": "#f7f7f2",
            "axes.facecolor": "#fcfcf8",
            "axes.edgecolor": "#cfd3c7",
            "axes.labelcolor": "#24302a",
            "text.color": "#24302a",
            "axes.titleweight": "bold",
            "axes.grid": True,
            "grid.color": "#d7dccf",
            "grid.alpha": 0.55,
            "grid.linestyle": "--",
            "font.size": 12,
        }
    )

    fig, ax_storage = plt.subplots(figsize=(13, 7.8), dpi=180)
    ax_cost = ax_storage.secondary_yaxis(
        "right",
        functions=(
            lambda tib_val: tib_val * tib_to_usd_factor,
            lambda usd_val: (usd_val / tib_to_usd_factor) if tib_to_usd_factor else usd_val,
        ),
    )

    bar_colors = [
        "#dbe9d8",
        "#cde2cf",
        "#bedac6",
        "#afd3be",
        "#9ecab6",
        "#8dc0ae",
        "#79b5a6",
        "#64a89f",
        "#519797",
        "#3d848d",
    ]
    if len(points) > len(bar_colors):
        bar_colors = [bar_colors[i % len(bar_colors)] for i in range(len(points))]
    else:
        bar_colors = bar_colors[: len(points)]

    bars = ax_storage.bar(
        years,
        tib,
        width=0.72 * (years[1] - years[0] if len(years) > 1 else 0.8),
        color=bar_colors,
        edgecolor="#2d4f4f",
        linewidth=0.8,
        zorder=3,
        label="Retained storage (TiB, billed)",
    )

    ax_storage.set_title(title, fontsize=17, pad=12)
    ax_storage.set_xlabel("Hypothetical AWS/Glacier retention policy (years)", fontsize=14, labelpad=12)
    ax_storage.set_ylabel("Retained storage (TiB, billed bytes)", fontsize=14, labelpad=10)
    ax_cost.set_ylabel("Estimated monthly storage cost (USD/month)", fontsize=14, labelpad=12)
    ax_storage.yaxis.set_major_formatter(FuncFormatter(fmt_tib))
    ax_cost.yaxis.set_major_formatter(FuncFormatter(fmt_usd))
    ax_storage.set_xticks(years)
    ax_storage.tick_params(axis="both", labelsize=12)
    ax_cost.tick_params(axis="y", labelsize=12)

    ax_storage.grid(axis="y")
    ax_storage.grid(axis="x", alpha=0.15)
    ax_cost.grid(False)

    ymax_storage = max(tib) if tib else 1.0
    ax_storage.set_ylim(0, ymax_storage * 1.33 if ymax_storage > 0 else 1)

    for b, p in zip(bars, points):
        ax_storage.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + (0.008 * ax_storage.get_ylim()[1]),
            f"${int(round(p.monthly_cost_usd))}/mo\n{p.retained_tib_binary:,.1f} TiB",
            ha="center",
            va="bottom",
            fontsize=8.8,
            color="#284a4a",
            linespacing=1.05,
        )

    if current_policy_point is not None:
        policy_x = current_policy_point.retention_years
        ax_storage.axvline(
            policy_x,
            color="#1d3557",
            linewidth=1.1,
            linestyle=":",
            alpha=0.7,
            zorder=4,
        )
        ax_storage.annotate(
            "Current retention policy",
            xy=(policy_x, ax_storage.get_ylim()[1] * 0.06),
            xytext=(-12, 0),
            textcoords="offset pixels",
            xycoords="data",
            ha="center",
            va="bottom",
            rotation=90,
            fontsize=9.2,
            color="#1d3557",
            alpha=0.9,
            bbox={"facecolor": "none", "edgecolor": "none", "pad": 0.2},
            zorder=5,
        )

    inv_ts_text = (
        inventory_last_modified.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        if inventory_last_modified is not None
        else "unknown"
    )
    classes_preview = ", ".join(
        f"{cls}:{summary.storage_class_counts[cls]:,}"
        for cls in sorted(summary.storage_class_counts)
    )
    if len(classes_preview) > 120:
        classes_preview = classes_preview[:117] + "..."

    subtitle = (
        f"As-of date: {as_of.isoformat()} | Inventory object: {inventory_label} "
        f"(LastModified {inv_ts_text})\n"
        f"Rows parsed: {summary.row_count:,} (skipped {summary.skipped_rows:,}) | "
        f"Format: {summary.detected_format or 'unknown'} | "
        f"Price: ${cost_per_gb_month:.5f}/GB-month | "
        f"Per-object overhead: {per_object_overhead_bytes:,} bytes | "
        f"Classes: {classes_preview or 'n/a'}"
    )
    fig.subplots_adjust(bottom=0.22, top=0.91, left=0.08, right=0.88)
    fig.text(0.01, 0.035, subtitle, ha="left", va="bottom", fontsize=8.6, color="#42534a")

    ax_storage.legend(
        [bars],
        ["Retained storage (TiB, billed)"],
        loc="upper left",
        frameon=True,
        facecolor="#fbfbf6",
        fontsize=11,
    )

    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, bbox_inches="tight")
    plt.close(fig)


def coerce_as_of_date(text: str | None) -> date:
    if not text:
        return datetime.now(timezone.utc).date()
    return datetime.strptime(text, "%Y-%m-%d").date()


def main() -> int:
    args = parse_args()

    if args.min_years <= 0 or args.max_years <= 0 or args.year_step <= 0:
        raise SystemExit("min/max/year-step must be positive integers")
    if args.min_years > args.max_years:
        raise SystemExit("--min-years cannot be greater than --max-years")

    years = list(range(args.min_years, args.max_years + 1, args.year_step))
    as_of = coerce_as_of_date(args.as_of_date)

    temp_download_path: Path | None = None
    inventory_label: str
    inventory_last_modified: datetime | None = None

    try:
        if args.inventory_file:
            inventory_path = Path(args.inventory_file)
            if not inventory_path.exists():
                raise FileNotFoundError(f"Inventory file does not exist: {inventory_path}")
            inventory_label = str(inventory_path)
        else:
            resolved_endpoint = resolve_nrp_endpoint(args.s3_endpoint)
            # Keep endpoint env vars aligned with repo conventions for libraries/tools that read them.
            os.environ["NRP_ENDPOINT"] = resolved_endpoint
            os.environ["ENDPOINT"] = resolved_endpoint
            s3_client = make_s3_client(
                region=args.aws_region,
                profile=args.aws_profile,
                endpoint_url=resolved_endpoint,
            )
            inventory_path, inventory_label, inventory_last_modified = download_inventory_from_s3(
                s3_client, args.inventory_s3_uri
            )
            temp_download_path = inventory_path

        summary = parse_inventory_summary(inventory_path)
        if summary.row_count == 0 or not summary.bytes_by_day:
            raise RuntimeError(f"No usable inventory rows found in {inventory_label}")

        points = build_retention_points(
            summary=summary,
            as_of=as_of,
            years=years,
            cost_per_gb_month=args.cost_per_gb_month,
            per_object_overhead_bytes=args.per_object_overhead_bytes,
        )

        current_policy_days = load_cold_storage_expire_days(Path(args.policy_config))
        current_policy_point = None
        if current_policy_days is not None and current_policy_days > 0:
            current_policy_point = compute_single_retention_point(
                summary=summary,
                as_of=as_of,
                retention_days=current_policy_days,
                cost_per_gb_month=args.cost_per_gb_month,
                per_object_overhead_bytes=args.per_object_overhead_bytes,
            )

        output_png = Path(args.output)
        output_csv = Path(args.output_csv)
        write_summary_csv(points, output_csv)
        plot_retention_analysis(
            points=points,
            output_png=output_png,
            title=args.title,
            cost_per_gb_month=args.cost_per_gb_month,
            per_object_overhead_bytes=args.per_object_overhead_bytes,
            as_of=as_of,
            inventory_label=inventory_label,
            inventory_last_modified=inventory_last_modified,
            summary=summary,
            current_policy_point=current_policy_point,
        )

        first = points[0]
        last = points[-1]
        print(f"Saved plot: {output_png}")
        print(f"Saved summary CSV: {output_csv}")
        print(
            "Retention sweep summary: "
            f"{first.retention_years:.0f}y={first.retained_tib_binary:,.2f} TiB "
            f"(${first.monthly_cost_usd:,.2f}/mo), "
            f"{last.retention_years:.0f}y={last.retained_tib_binary:,.2f} TiB "
            f"(${last.monthly_cost_usd:,.2f}/mo)"
        )
        if current_policy_point is not None:
            print(
                "Current YAML policy "
                f"({current_policy_point.retention_days} days = {current_policy_point.retention_years:.2f} years): "
                f"{current_policy_point.retained_tib_binary:,.2f} TiB, "
                f"${current_policy_point.monthly_cost_usd:,.2f}/mo"
            )
        return 0
    finally:
        if temp_download_path and temp_download_path.exists():
            try:
                temp_download_path.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())

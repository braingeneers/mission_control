#!/usr/bin/env python3
"""Generate the monthly data-retention report bundle."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

from generate_puts_deletes import (
    apply_last_modified_updates,
    build_cleanup_window_entries,
    load_config_file,
    load_inventories,
)
from glacier_cost_analysis_plot import (
    DEFAULT_COST_PER_GB_MONTH,
    DEFAULT_PER_OBJECT_OVERHEAD_BYTES,
    build_retention_points,
    parse_inventory_summary,
)


SOURCE_IDS = {
    ("braingeneers", "ephys"): "ephys",
    ("braingeneers", "imaging"): "imaging",
    ("braingeneers", "braindance"): "braindance",
    ("braingeneers", "integrated"): "integrated",
    ("braingeneers", "fluidics"): "fluidics",
    ("braingeneers", ""): "bucket-braingeneers",
    ("streamscope", ""): "bucket-streamscope",
    ("braingeneersdev", ""): "bucket-braingeneersdev",
    ("braingeneerscache", ""): "bucket-braingeneerscache",
}
MAX_SLACK_TEXT_CHARS = 3_500
MAX_PDF_CANDIDATES = 240
PDF_ROWS_PER_PAGE = 18
PDF_NAVY = "#123047"
PDF_TEAL = "#168C8C"
PDF_ORANGE = "#E08A32"
PDF_INK = "#18323F"
PDF_MUTED = "#5C7180"
PDF_RULE = "#D8E3E8"
PDF_PALE = "#F4F8FA"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--local-inventory", required=True)
    parser.add_argument("--glacier-inventory", required=True)
    parser.add_argument("--activity-log", required=True)
    parser.add_argument("--backup-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--report-uri", required=True)
    parser.add_argument("--report-url", help="Authenticated browser URL included in report summaries")
    parser.add_argument("--data-explorer-url", default="https://data-explorer.braingeneers.gi.ucsc.edu")
    parser.add_argument("--as-of", help="UTC date/time for reproducible reports")
    return parser.parse_args()


def candidate_identifier(row: dict[str, object]) -> str:
    payload = "|".join(
        str(row.get(key) or "")
        for key in ("phase", "target_type", "target", "effective_last_modified", "policy_eligible_at")
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def deep_link(base_url: str, phase: str, grouping_type: str, grouping_key: str, bucket_key: str, candidate_id: str) -> str:
    bucket, _, object_key = bucket_key.partition("/")
    first_segment = object_key.split("/", 1)[0] if object_key else ""
    structured_source = SOURCE_IDS.get((bucket, first_segment))
    if grouping_type == "atomic" and structured_source:
        dataset_id = grouping_key.rstrip("/").rsplit("/", 1)[-1]
        query = urlencode({"source": structured_source, "dataset": dataset_id})
        return f"{base_url.rstrip('/')}/?{query}"

    bucket_source = SOURCE_IDS.get((bucket, ""))
    if phase == "s3" and bucket_source:
        relative_key = object_key
        folder = relative_key.rsplit("/", 1)[0] if "/" in relative_key else ""
        parameters = {"source": bucket_source, "file": relative_key}
        if folder:
            parameters["prefix"] = folder
        return f"{base_url.rstrip('/')}/?{urlencode(parameters)}"

    # A Glacier-only object cannot be resolved by browsing current Ceph data.
    # Data Explorer validates this opaque id against the latest report pointer.
    return f"{base_url.rstrip('/')}/?{urlencode({'candidate': candidate_id})}"


def build_candidates(cleanup: pd.DataFrame, base_url: str) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    atomic_rows = cleanup[cleanup["GroupingType"] == "atomic"]
    for (phase, grouping_key), rows in atomic_rows.groupby(["CleanupPhase", "GroupingKey"]):
        effective = rows["SourceLastModified"].max()
        eligible = rows["ScheduledCleanupDate"].max()
        item: dict[str, object] = {
            "phase": phase,
            "target_type": "atomic_dataset",
            "target": grouping_key,
            "representative_key": rows.iloc[0]["BucketKey"],
            "object_count": int(len(rows)),
            "effective_last_modified": pd.Timestamp(effective).isoformat(),
            "policy_eligible_at": pd.Timestamp(eligible).isoformat(),
            "deletion_enabled": False,
        }
        item["candidate_id"] = candidate_identifier(item)
        item["data_explorer_url"] = deep_link(
            base_url,
            str(phase),
            "atomic",
            str(grouping_key),
            str(item["representative_key"]),
            str(item["candidate_id"]),
        )
        candidates.append(item)

    for row in cleanup[cleanup["GroupingType"] != "atomic"].itertuples(index=False):
        item = {
            "phase": row.CleanupPhase,
            "target_type": "file",
            "target": row.BucketKey,
            "representative_key": row.BucketKey,
            "object_count": 1,
            "effective_last_modified": pd.Timestamp(row.SourceLastModified).isoformat(),
            "policy_eligible_at": pd.Timestamp(row.ScheduledCleanupDate).isoformat(),
            "deletion_enabled": False,
        }
        item["candidate_id"] = candidate_identifier(item)
        item["data_explorer_url"] = deep_link(
            base_url,
            str(row.CleanupPhase),
            "file",
            str(row.BucketKey),
            str(row.BucketKey),
            str(item["candidate_id"]),
        )
        candidates.append(item)

    candidates.sort(key=lambda item: (str(item["policy_eligible_at"]), str(item["target"])))
    return candidates


def write_candidates_csv(path: Path, candidates: list[dict[str, object]]) -> None:
    fields = [
        "candidate_id",
        "phase",
        "target_type",
        "target",
        "representative_key",
        "object_count",
        "effective_last_modified",
        "policy_eligible_at",
        "deletion_enabled",
        "data_explorer_url",
    ]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(candidates)


def cost_appendix(glacier_inventory: Path, output: Path, as_of: datetime, current_days: int) -> list[dict[str, object]]:
    summary = parse_inventory_summary(glacier_inventory)
    points = build_retention_points(
        summary,
        as_of.date(),
        range(1, 11),
        DEFAULT_COST_PER_GB_MONTH,
        DEFAULT_PER_OBJECT_OVERHEAD_BYTES,
    )
    rows = [
        {
            "retention_years": point.retention_years,
            "retention_days": point.retention_days,
            "retained_objects": point.retained_objects,
            "retained_bytes": point.retained_bytes,
            "retained_tib": point.retained_tib_binary,
            "estimated_monthly_cost_usd": point.monthly_cost_usd,
            "current_policy": abs(point.retention_days - current_days) <= 183,
        }
        for point in points
    ]
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ["retention_years"])
        writer.writeheader()
        writer.writerows(rows)
    return rows


def render_html(
    path: Path,
    run_id: str,
    generated_at: datetime,
    candidates: list[dict[str, object]],
    cost_rows: list[dict[str, object]],
) -> None:
    candidate_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item['phase']).upper())}</td>"
        f"<td><a href=\"{html.escape(str(item['data_explorer_url']))}\">{html.escape(str(item['target']))}</a></td>"
        f"<td>{int(item['object_count']):,}</td>"
        f"<td>{html.escape(str(item['policy_eligible_at'])[:10])}</td>"
        "</tr>"
        for item in candidates
    ) or '<tr><td colspan="4">No deletions are scheduled in this reporting window.</td></tr>'
    cost_table = "".join(
        "<tr>"
        f"<td>{row['retention_years']}</td><td>{int(row['retained_objects']):,}</td>"
        f"<td>{float(row['retained_tib']):,.2f}</td><td>${float(row['estimated_monthly_cost_usd']):,.2f}</td>"
        "</tr>"
        for row in cost_rows
    )
    path.write_text(
        f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Data retention report</title>
<style>body{{font:16px system-ui;max-width:1200px;margin:40px auto;padding:0 24px;color:#172028}}h1{{margin-bottom:4px}}table{{border-collapse:collapse;width:100%;margin:18px 0 32px}}th,td{{padding:9px;border-bottom:1px solid #d9e1e7;text-align:left}}th{{background:#eef4f7}}code{{font-size:.85em}}</style></head>
<body><h1>Data retention policy report</h1><p>Run <code>{html.escape(run_id)}</code> · {generated_at:%Y-%m-%d %H:%M UTC}</p>
<h2>Scheduled deletions ({len(candidates):,})</h2><table><thead><tr><th>Source</th><th>Dataset or file</th><th>Objects</th><th>Delete on</th></tr></thead><tbody>{candidate_rows}</tbody></table>
<h2>Appendix: Glacier retention and estimated storage cost</h2><p>Estimates use the inventory snapshot and configurable Deep Archive storage assumptions. They exclude retrieval, request, transfer, and early-deletion charges.</p>
<table><thead><tr><th>Retention years</th><th>Objects</th><th>Retained TiB</th><th>Estimated monthly cost</th></tr></thead><tbody>{cost_table}</tbody></table></body></html>""",
        encoding="utf-8",
    )


def _candidate_path_parts(candidate: dict[str, object]) -> list[str]:
    return [part for part in str(candidate.get("target") or "").strip("/").split("/") if part]


def compact_candidate_names(candidates: list[dict[str, object]]) -> list[str]:
    """Return the shortest unique trailing path for each candidate."""
    path_parts = [_candidate_path_parts(candidate) or ["unnamed item"] for candidate in candidates]
    names: list[str] = []
    for index, parts in enumerate(path_parts):
        depth = 1
        while depth < len(parts):
            suffix = tuple(parts[-depth:])
            if sum(tuple(other[-depth:]) == suffix for other in path_parts) == 1:
                break
            depth += 1
        name = "/".join(parts[-depth:])
        if sum(tuple(other) == tuple(parts) for other in path_parts) > 1:
            phase = str(candidates[index].get("phase") or "source").upper()
            name = f"{phase}: {name}"
        names.append(name)
    return names


def _display_date(value: object) -> str:
    timestamp = pd.Timestamp(value)
    return timestamp.strftime("%b %d, %Y").replace(" 0", " ")


def _candidate_source(candidate: dict[str, object]) -> str:
    return "Glacier" if str(candidate.get("phase")) == "glacier" else "Ceph/S3"


def _shorten_middle(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    side = max(1, (limit - 3) // 2)
    return f"{value[:side]}...{value[-side:]}"


def _object_count_label(value: object) -> str:
    count = int(value or 0)
    return f"{count:,} object" if count == 1 else f"{count:,} objects"


def _pdf_footer(figure, page_number: int, page_count: int) -> None:
    figure.add_artist(
        Rectangle((0.055, 0.055), 0.89, 0.002, transform=figure.transFigure, color=PDF_RULE, linewidth=0)
    )
    figure.text(0.06, 0.028, "Data retention policy report", fontsize=8, color=PDF_MUTED)
    figure.text(
        0.94,
        0.028,
        f"Page {page_number} of {page_count}",
        fontsize=8,
        color=PDF_MUTED,
        ha="right",
    )


def render_pdf(
    path: Path,
    generated_at: datetime,
    candidates: list[dict[str, object]],
    cost_rows: list[dict[str, object]],
) -> None:
    displayed_candidates = candidates[:MAX_PDF_CANDIDATES]
    candidate_page_count = max(
        0,
        (len(displayed_candidates) + PDF_ROWS_PER_PAGE - 1) // PDF_ROWS_PER_PAGE,
    )
    page_count = 1 + candidate_page_count + (1 if cost_rows else 0)
    phase_counts = Counter(str(item.get("phase")) for item in candidates)
    dataset_count = sum(item.get("target_type") == "atomic_dataset" for item in candidates)
    file_count = len(candidates) - dataset_count
    object_count = sum(int(item.get("object_count") or 0) for item in candidates)
    compact_names = compact_candidate_names(displayed_candidates)

    with PdfPages(path) as pdf:
        figure = plt.figure(figsize=(11, 8.5), facecolor="white")
        figure.add_artist(
            Rectangle((0, 0.825), 1, 0.175, transform=figure.transFigure, color=PDF_NAVY, linewidth=0)
        )
        figure.text(0.06, 0.925, "DATA LIFECYCLE", fontsize=9, weight="bold", color="#9FD6D5")
        figure.text(0.06, 0.865, "Data retention policy report", fontsize=24, weight="bold", color="white")
        figure.text(
            0.94,
            0.873,
            generated_at.strftime("Generated %Y-%m-%d\n%H:%M UTC"),
            fontsize=9,
            color="#D8E8EF",
            ha="right",
            linespacing=1.4,
        )

        card_values = [len(candidates), dataset_count, file_count, object_count]
        card_labels = ["Affected items", "Datasets", "Individual files", "Underlying objects"]
        card_colors = [PDF_TEAL, PDF_NAVY, PDF_NAVY, PDF_ORANGE]
        for index, (value, label, accent) in enumerate(zip(card_values, card_labels, card_colors)):
            x = 0.06 + index * 0.225
            figure.add_artist(
                FancyBboxPatch(
                    (x, 0.62),
                    0.195,
                    0.135,
                    boxstyle="round,pad=0.008,rounding_size=0.012",
                    transform=figure.transFigure,
                    facecolor="white",
                    edgecolor=PDF_RULE,
                    linewidth=1.1,
                )
            )
            figure.add_artist(
                Rectangle((x, 0.62), 0.008, 0.135, transform=figure.transFigure, color=accent, linewidth=0)
            )
            figure.text(x + 0.025, 0.692, f"{value:,}", fontsize=21, weight="bold", color=PDF_INK)
            figure.text(x + 0.025, 0.648, label.upper(), fontsize=8.5, weight="bold", color=PDF_MUTED)

        figure.text(0.06, 0.535, "SCHEDULE", fontsize=9, weight="bold", color=PDF_TEAL)
        if candidates:
            first_date = _display_date(candidates[0]["policy_eligible_at"])
            last_date = _display_date(candidates[-1]["policy_eligible_at"])
            date_window = first_date if first_date == last_date else f"{first_date} to {last_date}"
            figure.text(0.06, 0.49, date_window, fontsize=17, weight="bold", color=PDF_INK)
            figure.text(
                0.06,
                0.447,
                f"{phase_counts.get('s3', 0):,} Ceph/S3 item(s)  |  "
                f"{phase_counts.get('glacier', 0):,} Glacier-only item(s)",
                fontsize=10.5,
                color=PDF_MUTED,
            )
        else:
            figure.text(0.06, 0.49, "No deletions scheduled", fontsize=17, weight="bold", color=PDF_INK)
            figure.text(0.06, 0.447, "No datasets or files fall within this reporting window.", fontsize=10.5, color=PDF_MUTED)

        figure.add_artist(
            FancyBboxPatch(
                (0.06, 0.18),
                0.88,
                0.185,
                boxstyle="round,pad=0.012,rounding_size=0.012",
                transform=figure.transFigure,
                facecolor=PDF_PALE,
                edgecolor="none",
            )
        )
        figure.text(0.085, 0.315, "ABOUT THIS REPORT", fontsize=9, weight="bold", color=PDF_TEAL)
        figure.text(
            0.085,
            0.267,
            "- Atomic datasets are listed once, with their underlying object count.\n"
            "- Individual files are listed separately when they are outside a configured atomic dataset.\n"
            "- The CSV and JSON artifacts retain complete paths, evidence, and stable identifiers.",
            fontsize=10,
            color=PDF_INK,
            linespacing=1.65,
            va="top",
        )
        _pdf_footer(figure, 1, page_count)
        pdf.savefig(figure)
        plt.close(figure)

        for page_index, offset in enumerate(range(0, len(displayed_candidates), PDF_ROWS_PER_PAGE), start=2):
            page_rows = displayed_candidates[offset : offset + PDF_ROWS_PER_PAGE]
            page_names = compact_names[offset : offset + PDF_ROWS_PER_PAGE]
            figure, axis = plt.subplots(figsize=(11, 8.5), facecolor="white")
            axis.axis("off")
            figure.text(0.06, 0.925, "SCHEDULED DELETIONS", fontsize=9, weight="bold", color=PDF_TEAL)
            figure.text(
                0.06,
                0.875,
                f"Items {offset + 1:,}-{offset + len(page_rows):,} of {len(candidates):,}",
                fontsize=19,
                weight="bold",
                color=PDF_INK,
            )
            figure.text(0.06, 0.835, "Compact names are shown here; complete paths remain in the HTML, CSV, and JSON artifacts.", fontsize=9.5, color=PDF_MUTED)
            table_rows = [
                [
                    _display_date(item["policy_eligible_at"]),
                    _candidate_source(item),
                    _shorten_middle(name, 74),
                    f"{int(item['object_count']):,}",
                ]
                for item, name in zip(page_rows, page_names)
            ]
            table_height = 0.68 * (len(page_rows) + 1) / (PDF_ROWS_PER_PAGE + 1)
            table = axis.table(
                cellText=table_rows,
                colLabels=["Delete on", "Source", "Dataset or file", "Objects"],
                colWidths=[0.17, 0.13, 0.59, 0.11],
                cellLoc="left",
                colLoc="left",
                loc="center",
                bbox=[0.055, 0.80 - table_height, 0.89, table_height],
            )
            table.auto_set_font_size(False)
            table.set_fontsize(8.6)
            for (row_index, column_index), cell in table.get_celld().items():
                cell.set_edgecolor(PDF_RULE)
                cell.set_linewidth(0.7)
                cell.PAD = 0.045
                if row_index == 0:
                    cell.set_facecolor(PDF_NAVY)
                    cell.get_text().set_color("white")
                    cell.get_text().set_weight("bold")
                    cell.set_height(0.052)
                else:
                    cell.set_facecolor("white" if row_index % 2 else PDF_PALE)
                    cell.get_text().set_color(PDF_INK)
                    cell.set_height(0.047)
                if column_index == 3:
                    cell.get_text().set_ha("right")
            if len(candidates) > len(displayed_candidates) and offset + len(page_rows) == len(displayed_candidates):
                figure.text(
                    0.06,
                    0.085,
                    f"Showing the first {len(displayed_candidates):,} candidates; CSV and JSON contain all {len(candidates):,}.",
                    fontsize=8.5,
                    color=PDF_MUTED,
                )
            _pdf_footer(figure, page_index, page_count)
            pdf.savefig(figure)
            plt.close(figure)

        if cost_rows:
            appendix_page = 2 + candidate_page_count
            figure = plt.figure(figsize=(11, 8.5), facecolor="white")
            figure.text(0.06, 0.925, "COST APPENDIX", fontsize=9, weight="bold", color=PDF_TEAL)
            figure.text(0.06, 0.875, "Glacier retention and estimated storage cost", fontsize=19, weight="bold", color=PDF_INK)
            figure.text(0.06, 0.835, "Storage-only estimates based on the inventory snapshot and Deep Archive storage assumptions.", fontsize=9.5, color=PDF_MUTED)

            cost_axis = figure.add_axes([0.09, 0.46, 0.83, 0.30])
            years = [int(row["retention_years"]) for row in cost_rows]
            costs = [float(row["estimated_monthly_cost_usd"]) for row in cost_rows]
            cost_axis.plot(years, costs, marker="o", linewidth=2.4, color=PDF_TEAL)
            cost_axis.fill_between(years, costs, min(costs), color=PDF_TEAL, alpha=0.08)
            cost_axis.set_xlabel("Retention window (years)", color=PDF_MUTED, labelpad=8)
            cost_axis.set_ylabel("Estimated monthly cost (USD)", color=PDF_MUTED, labelpad=8)
            cost_axis.set_xticks(years)
            cost_axis.grid(axis="y", color=PDF_RULE, linewidth=0.8)
            cost_axis.spines[["top", "right"]].set_visible(False)
            cost_axis.spines[["left", "bottom"]].set_color(PDF_RULE)
            cost_axis.tick_params(colors=PDF_MUTED)
            current_rows = [row for row in cost_rows if row.get("current_policy")]
            if current_rows:
                current = current_rows[-1]
                current_year = int(current["retention_years"])
                current_cost = float(current["estimated_monthly_cost_usd"])
                cost_axis.scatter([current_year], [current_cost], s=90, color=PDF_ORANGE, zorder=4)
                cost_axis.annotate(
                    "Current policy",
                    (current_year, current_cost),
                    xytext=(-8, 13),
                    textcoords="offset points",
                    ha="right",
                    fontsize=8.5,
                    color=PDF_ORANGE,
                    weight="bold",
                )

            selected_years = {1, 3, 5, 7, 10}
            selected_rows = [row for row in cost_rows if int(row["retention_years"]) in selected_years or row.get("current_policy")]
            selected_rows.sort(key=lambda row: int(row["retention_years"]))
            table_axis = figure.add_axes([0.09, 0.14, 0.83, 0.23])
            table_axis.axis("off")
            table = table_axis.table(
                cellText=[
                    [
                        f"{int(row['retention_years'])}",
                        f"{int(row['retained_objects']):,}",
                        f"{float(row['retained_tib']):,.2f}",
                        f"${float(row['estimated_monthly_cost_usd']):,.2f}",
                        "Current" if row.get("current_policy") else "",
                    ]
                    for row in selected_rows
                ],
                colLabels=["Years", "Retained objects", "Retained TiB", "Monthly cost", "Policy"],
                colWidths=[0.10, 0.25, 0.20, 0.22, 0.15],
                cellLoc="right",
                colLoc="right",
                bbox=[0, 0, 1, 1],
            )
            table.auto_set_font_size(False)
            table.set_fontsize(8.5)
            for (row_index, column_index), cell in table.get_celld().items():
                cell.set_edgecolor(PDF_RULE)
                cell.set_linewidth(0.7)
                if row_index == 0:
                    cell.set_facecolor(PDF_NAVY)
                    cell.get_text().set_color("white")
                    cell.get_text().set_weight("bold")
                else:
                    source_row = selected_rows[row_index - 1]
                    cell.set_facecolor("#FFF2E3" if source_row.get("current_policy") else ("white" if row_index % 2 else PDF_PALE))
                    cell.get_text().set_color(PDF_INK)
            figure.text(
                0.09,
                0.095,
                "Storage-only estimate; retrieval, requests, transfer, and early-deletion charges are excluded.",
                fontsize=8.5,
                color=PDF_MUTED,
            )
            _pdf_footer(figure, appendix_page, page_count)
            pdf.savefig(figure)
            plt.close(figure)


def _slack_text(value: object) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _slack_link(url: str, label: str) -> str:
    safe_label = _slack_text(label).replace("|", "¦")
    return f"<{_slack_text(url)}|{safe_label}>"


def render_slack_summary(
    path: Path,
    generated_at: datetime,
    candidates: list[dict[str, object]],
    report_url: str,
) -> None:
    dataset_count = sum(item.get("target_type") == "atomic_dataset" for item in candidates)
    file_count = len(candidates) - dataset_count
    object_count = sum(int(item.get("object_count") or 0) for item in candidates)
    lines = [
        "*Data retention policy report*",
        generated_at.strftime("Generated %Y-%m-%d %H:%M UTC"),
        (
            f"Affected items: {len(candidates):,} "
            f"(datasets: {dataset_count:,}; files: {file_count:,}; objects: {object_count:,})"
        ),
    ]
    report_line = f"*Full PDF report:* {_slack_link(report_url, 'Open in Data Explorer')}"
    if not candidates:
        lines.append("No deletions are scheduled in this reporting window.")
    else:
        first_date = _display_date(candidates[0]["policy_eligible_at"])
        last_date = _display_date(candidates[-1]["policy_eligible_at"])
        date_window = first_date if first_date == last_date else f"{first_date} to {last_date}"
        lines.extend([f"Scheduled deletion window: {date_window}", "*Scheduled deletions*"])
        compact_names = compact_candidate_names(candidates)
        included = 0
        current_date = ""
        for item, compact_name in zip(candidates, compact_names):
            deletion_date = _display_date(item["policy_eligible_at"])
            safe_name = _slack_text(compact_name).replace("`", "'")
            detail = (
                f" · {_object_count_label(item['object_count'])}"
                if item.get("target_type") == "atomic_dataset"
                else ""
            )
            if str(item.get("phase")) == "glacier":
                detail += " · Glacier"
            candidate_line = f"• `{safe_name}`{detail}"
            new_lines = ([f"*{deletion_date}*"] if deletion_date != current_date else []) + [candidate_line]
            remaining = len(candidates) - included - 1
            suffix = [f"...and {remaining:,} more item(s) in the full PDF."] if remaining else []
            if len("\n".join(lines + new_lines + suffix + [report_line])) > MAX_SLACK_TEXT_CHARS:
                break
            lines.extend(new_lines)
            current_date = deletion_date
            included += 1
        if included < len(candidates):
            lines.append(f"...and {len(candidates) - included:,} more item(s) in the full PDF.")
    lines.append(report_line)
    rendered = "\n".join(lines)
    if len(rendered) > MAX_SLACK_TEXT_CHARS:
        raise ValueError("Slack-ready report summary exceeds its safe text limit.")
    path.write_text(rendered + "\n", encoding="utf-8")


def main(args: argparse.Namespace) -> None:
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    config = load_config_file(args.config)
    backup_manifest = json.loads(Path(args.backup_manifest).read_text(encoding="utf-8"))
    if backup_manifest.get("schema_version") != 1 or backup_manifest.get("status") != "complete":
        raise ValueError("Backup-state manifest is incomplete or unsupported.")
    if not args.report_uri.startswith("s3://") or not args.report_uri.endswith("/"):
        raise ValueError("Report URI must be an s3:// prefix ending in '/'.")
    if not Path(args.activity_log).is_file():
        raise FileNotFoundError(f"Activity log does not exist: {args.activity_log}")
    generated_at = (
        datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
        if args.as_of
        else datetime.now(timezone.utc)
    )
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)

    local, glacier, _bad_keys = load_inventories(args.local_inventory, args.glacier_inventory)
    local = apply_last_modified_updates(local, config)
    glacier = apply_last_modified_updates(
        glacier,
        config,
        authoritative_markers=local,
    )
    deletion = config.get("deletion") or {}
    cleanup = build_cleanup_window_entries(
        local,
        glacier,
        s3_expire_days=int(deletion["s3_expire_days"]),
        cold_storage_expire_days=int(deletion["cold_storage_expire_days"]),
        notification_days=int(deletion["notification_days"]),
        atomic_directories=(config.get("backup") or {}).get("atomic_directories") or [],
        now_utc=generated_at,
    )
    candidates = build_candidates(cleanup, args.data_explorer_url)
    cost_rows = cost_appendix(
        Path(args.glacier_inventory),
        output / "glacier-retention-cost.csv",
        generated_at,
        int(deletion["cold_storage_expire_days"]),
    )
    write_candidates_csv(output / "cleanup-candidates.csv", candidates)
    report = {
        "schema_version": 1,
        "run_id": args.run_id,
        "generated_at_utc": generated_at.isoformat(),
        "status": "complete",
        "deletion_enabled": False,
        "backup_state": backup_manifest,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    (output / "cleanup-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render_html(output / "cleanup-report.html", args.run_id, generated_at, candidates, cost_rows)
    render_pdf(output / "cleanup-report.pdf", generated_at, candidates, cost_rows)

    report_url = args.report_url or f"{args.report_uri.rstrip('/')}/cleanup-report.pdf"
    render_slack_summary(
        output / "cleanup-report-slack.txt",
        generated_at,
        candidates,
        report_url,
    )
    completion = {
        "schema_version": 1,
        "run_id": args.run_id,
        "status": "complete",
        "completed_at_utc": _iso(generated_at),
        "report_uri": args.report_uri,
        "artifacts": {
            name: f"{args.report_uri.rstrip('/')}/{name}"
            for name in (
                "cleanup-report.html",
                "cleanup-report.pdf",
                "cleanup-report-slack.txt",
                "cleanup-report.json",
                "cleanup-candidates.csv",
                "glacier-retention-cost.csv",
            )
        },
    }
    (output / "completion-manifest.json").write_text(
        json.dumps(completion, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


if __name__ == "__main__":
    main(parse_args())

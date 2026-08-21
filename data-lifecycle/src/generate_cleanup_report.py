#!/usr/bin/env python3
"""Generate the advisory monthly data-retention report bundle."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

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
MAX_SLACK_HIGHLIGHTS = 5


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
    ) or '<tr><td colspan="4">No new policy candidates in this reporting window.</td></tr>'
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
<style>body{{font:16px system-ui;max-width:1200px;margin:40px auto;padding:0 24px;color:#172028}}h1{{margin-bottom:4px}}.notice{{padding:14px 18px;background:#fff4df;border-left:4px solid #d88218}}table{{border-collapse:collapse;width:100%;margin:18px 0 32px}}th,td{{padding:9px;border-bottom:1px solid #d9e1e7;text-align:left}}th{{background:#eef4f7}}code{{font-size:.85em}}</style></head>
<body><h1>Data retention policy report</h1><p>Run <code>{html.escape(run_id)}</code> · {generated_at:%Y-%m-%d %H:%M UTC}</p>
<p class="notice"><strong>Advisory only.</strong> Automatic deletion is disabled. Dates below indicate policy eligibility, not a scheduled destructive operation.</p>
<h2>Policy candidates ({len(candidates):,})</h2><table><thead><tr><th>Phase</th><th>Dataset or file</th><th>Objects</th><th>Policy eligible</th></tr></thead><tbody>{candidate_rows}</tbody></table>
<h2>Appendix: Glacier retention and estimated storage cost</h2><p>Estimates use the inventory snapshot and configurable Deep Archive storage assumptions. They exclude retrieval, request, transfer, and early-deletion charges.</p>
<table><thead><tr><th>Retention years</th><th>Objects</th><th>Retained TiB</th><th>Estimated monthly cost</th></tr></thead><tbody>{cost_table}</tbody></table></body></html>""",
        encoding="utf-8",
    )


def render_pdf(
    path: Path,
    generated_at: datetime,
    candidates: list[dict[str, object]],
    cost_rows: list[dict[str, object]],
) -> None:
    with PdfPages(path) as pdf:
        figure = plt.figure(figsize=(11, 8.5))
        figure.text(0.07, 0.92, "Data retention policy report", fontsize=22, weight="bold")
        figure.text(0.07, 0.87, generated_at.strftime("Generated %Y-%m-%d %H:%M UTC"), fontsize=11)
        figure.text(
            0.07,
            0.79,
            "ADVISORY ONLY — automatic deletion is disabled. Eligibility dates are policy signals,\nnot scheduled destructive operations.",
            fontsize=13,
            color="#9a5b12",
        )
        figure.text(0.07, 0.67, f"Candidate entities: {len(candidates):,}", fontsize=16)
        phase_counts = pd.Series([item["phase"] for item in candidates]).value_counts().to_dict()
        figure.text(0.07, 0.61, f"Ceph/S3: {phase_counts.get('s3', 0):,}    Glacier-only: {phase_counts.get('glacier', 0):,}", fontsize=12)
        figure.text(0.07, 0.48, "Open the HTML or CSV artifact for complete candidate links and identifiers.", fontsize=11)
        plt.axis("off")
        pdf.savefig(figure, bbox_inches="tight")
        plt.close(figure)

        rows_per_page = 24
        displayed_candidates = candidates[:240]
        for offset in range(0, len(displayed_candidates), rows_per_page):
            page_rows = displayed_candidates[offset : offset + rows_per_page]
            figure, axis = plt.subplots(figsize=(11, 8.5))
            axis.axis("off")
            axis.set_title(
                f"Advisory candidates {offset + 1}–{offset + len(page_rows)} of {len(candidates):,}",
                loc="left",
                fontsize=15,
                pad=18,
            )
            table_rows = [
                [
                    str(item["phase"]).upper(),
                    str(item["target"])[:92],
                    f"{int(item['object_count']):,}",
                    str(item["policy_eligible_at"])[:10],
                ]
                for item in page_rows
            ]
            table = axis.table(
                cellText=table_rows,
                colLabels=["Phase", "Dataset or file", "Objects", "Policy eligible"],
                colWidths=[0.08, 0.68, 0.1, 0.14],
                cellLoc="left",
                colLoc="left",
                loc="upper left",
                bbox=[0, 0.05, 1, 0.9],
            )
            table.auto_set_font_size(False)
            table.set_fontsize(7.5)
            table.scale(1, 1.25)
            if len(candidates) > len(displayed_candidates) and offset + len(page_rows) == len(displayed_candidates):
                figure.text(
                    0.08,
                    0.025,
                    f"Showing the first {len(displayed_candidates):,} candidates; CSV and JSON contain all {len(candidates):,}.",
                    fontsize=9,
                )
            pdf.savefig(figure, bbox_inches="tight")
            plt.close(figure)

        if cost_rows:
            figure, storage_axis = plt.subplots(figsize=(11, 8.5))
            storage_axis.plot(
                [row["retention_years"] for row in cost_rows],
                [row["retained_tib"] for row in cost_rows],
                marker="o",
                color="#277da1",
                label="Retained storage",
            )
            storage_axis.set_title("Appendix: Glacier retention and estimated storage cost")
            storage_axis.set_xlabel("Retention window (years)")
            storage_axis.set_ylabel("Retained storage (TiB)", color="#277da1")
            storage_axis.tick_params(axis="y", labelcolor="#277da1")
            storage_axis.grid(alpha=0.25)
            cost_axis = storage_axis.twinx()
            cost_axis.plot(
                [row["retention_years"] for row in cost_rows],
                [row["estimated_monthly_cost_usd"] for row in cost_rows],
                marker="s",
                color="#d88218",
                label="Estimated monthly storage cost",
            )
            cost_axis.set_ylabel("Estimated monthly storage cost (USD)", color="#d88218")
            cost_axis.tick_params(axis="y", labelcolor="#d88218")
            figure.text(
                0.08,
                0.03,
                "Storage-only estimate; retrieval, requests, transfer, and early-deletion charges are excluded.",
                fontsize=9,
            )
            pdf.savefig(figure, bbox_inches="tight")
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
    phase_counts = pd.Series([item["phase"] for item in candidates]).value_counts().to_dict()
    lines = [
        "*Monthly data retention policy report*",
        generated_at.strftime("Generated %Y-%m-%d %H:%M UTC"),
        "_Advisory only:_ Automatic deletion is disabled. Eligibility dates are policy signals, not scheduled destructive operations.",
        (
            f"Candidate entities: {len(candidates):,} "
            f"(Ceph/S3: {phase_counts.get('s3', 0):,}; "
            f"Glacier-only: {phase_counts.get('glacier', 0):,})"
        ),
    ]
    report_line = f"Full report: {_slack_link(report_url, 'Open the interactive HTML report')}"
    if not candidates:
        lines.append("No policy candidates were found in this reporting window.")
    else:
        lines.append("*Earliest policy candidates*")
        included = 0
        highlighted = candidates[:MAX_SLACK_HIGHLIGHTS]
        for item in highlighted:
            target = str(item["target"])
            if len(target) > 160:
                target = f"{target[:78]}…{target[-79:]}"
            candidate_url = str(item["data_explorer_url"])
            target_text = (
                _slack_link(candidate_url, target)
                if len(candidate_url) <= 500
                else f"{_slack_text(target)} (open from the full report)"
            )
            candidate_line = (
                f"• {str(item['phase']).upper()} · {target_text} · "
                f"eligible {str(item['policy_eligible_at'])[:10]}"
            )
            suffix = [
                f"…and {len(candidates) - included - 1:,} more candidate(s) in the full report."
            ] if len(candidates) > included + 1 else []
            if len("\n".join(lines + [candidate_line] + suffix + [report_line])) > MAX_SLACK_TEXT_CHARS:
                break
            lines.append(candidate_line)
            included += 1
        if included < len(candidates):
            lines.append(f"…and {len(candidates) - included:,} more candidate(s) in the full report.")
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
        "advisory": "Automatic deletion is disabled; policy dates are advisory eligibility signals.",
        "backup_state": backup_manifest,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    (output / "cleanup-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render_html(output / "cleanup-report.html", args.run_id, generated_at, candidates, cost_rows)
    render_pdf(output / "cleanup-report.pdf", generated_at, candidates, cost_rows)

    report_url = args.report_url or f"{args.report_uri.rstrip('/')}/cleanup-report.html"
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

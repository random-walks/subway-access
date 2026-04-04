from __future__ import annotations

import argparse
import csv
from pathlib import Path

from subway_access import analysis, models, pipeline

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"
ARTIFACTS_DIR = ROOT / "artifacts"
REPORTS_DIR = ROOT / "reports"


def cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / name


def artifact_path(name: str) -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACTS_DIR / name


def report_path(name: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR / name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a station reliability report from official availability history.",
    )
    parser.add_argument("--geography", default="borough")
    parser.add_argument("--value", default="Manhattan")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=cache_path("manhattan-snapshot"),
    )
    parser.add_argument("--availability-months", type=int, default=12)
    parser.add_argument("--window-days", type=int, default=365)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--publish-report", action="store_true")
    return parser


def write_report(
    query: models.AccessibilityQuery,
    reliability: models.ReliabilityDataset,
    output_csv: Path,
) -> Path:
    top_fragile = min(
        reliability.records,
        key=lambda record: (record.reliability_score, record.station_id),
    )
    report = f"""# Outage Reliability Report Tearsheet

## Query

- Geography: `{query.geography}`
- Value: `{query.value}`

## Reliability Snapshot

- Stations scored: {len(reliability.records)}
- Lowest reliability station: `{top_fragile.station_id}`
- Lowest reliability label: {top_fragile.reliability_label}
- Outage minutes in window: {top_fragile.outage_minutes}

## Artifact

- Reliability CSV: `{output_csv.name}`
"""
    tearsheet_path = report_path("outage-reliability-report-tearsheet.md")
    tearsheet_path.write_text(report, encoding="utf-8")
    return tearsheet_path


def main() -> None:
    args = build_parser().parse_args()
    query = models.AccessibilityQuery(geography=args.geography, value=args.value)
    snapshot = pipeline.fetch_study_area_snapshot(
        query,
        cache_dir=args.cache_dir,
        refresh=args.refresh,
        availability_months=args.availability_months,
    )
    reliability = analysis.compute_reliability(
        snapshot.stations,
        snapshot.outages,
        models.TimeWindow(days=args.window_days),
    )

    output_csv = artifact_path("station-reliability.csv")
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "station_id",
                "station_name",
                "borough",
                "ada_status",
                "outage_count",
                "outage_minutes",
                "window_days",
                "reliability_score",
                "reliability_label",
            ],
        )
        writer.writeheader()
        for record in reliability.records:
            writer.writerow(
                {
                    "station_id": record.station_id,
                    "station_name": record.station_name or "",
                    "borough": record.borough or "",
                    "ada_status": record.ada_status,
                    "outage_count": record.outage_count,
                    "outage_minutes": record.outage_minutes,
                    "window_days": record.window_days,
                    "reliability_score": f"{record.reliability_score:.4f}",
                    "reliability_label": record.reliability_label,
                }
            )

    report_file: Path | None = None
    if args.publish_report:
        report_file = write_report(query, reliability, output_csv)

    print("Outage Reliability Report")
    print("------------------------")
    print(f"Study area: {query.geography}={query.value}")
    print(f"Wrote {output_csv}")
    if report_file is None:
        print(
            "Skipped tracked report generation. Re-run with --publish-report to update reports/."
        )
    else:
        print(f"Wrote tracked report: {report_file}")


if __name__ == "__main__":
    main()

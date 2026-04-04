from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt

from subway_access import analysis, models, pipeline

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"
ARTIFACTS_DIR = ROOT / "artifacts"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"


def cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / name


def artifact_path(name: str) -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACTS_DIR / name


def report_path(name: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR / name


def figure_path(name: str) -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    return FIGURES_DIR / name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a station reliability report from official availability history.",
    )
    parser.add_argument("--geography", default="borough")
    parser.add_argument("--value", default="Queens")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=cache_path("queens-snapshot"),
    )
    parser.add_argument("--availability-months", type=int, default=12)
    parser.add_argument("--window-days", type=int, default=365)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--publish-report", action="store_true")
    return parser


def _accessible_records(
    reliability: models.ReliabilityDataset,
) -> list[models.ReliabilityRecord]:
    return [record for record in reliability.records if record.ada_status == "accessible"]


def _plot_lowest_reliability(records: list[models.ReliabilityRecord]) -> Path:
    path = figure_path("lowest-reliability-stations.png")
    ranked = sorted(records, key=lambda record: (record.reliability_score, record.station_id))[
        :15
    ]
    labels = [record.station_name or record.station_id for record in ranked]
    values = [record.reliability_score for record in ranked]

    figure, axes = plt.subplots(figsize=(11, 6))
    axes.barh(labels, values, color="#e45756")
    axes.invert_yaxis()
    axes.set_xlabel("Reliability score")
    axes.set_title("Lowest reliability accessible stations")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def _plot_scheduled_vs_unscheduled(records: list[models.ReliabilityRecord]) -> Path:
    path = figure_path("scheduled-vs-unscheduled.png")
    ranked = sorted(
        records,
        key=lambda record: (
            record.unscheduled_outages + record.scheduled_outages,
            record.station_id,
        ),
        reverse=True,
    )[:12]
    labels = [record.station_name or record.station_id for record in ranked]
    scheduled = [record.scheduled_outages for record in ranked]
    unscheduled = [record.unscheduled_outages for record in ranked]

    figure, axes = plt.subplots(figsize=(11, 6))
    axes.bar(labels, scheduled, label="Scheduled", color="#72b7b2")
    axes.bar(labels, unscheduled, bottom=scheduled, label="Unscheduled", color="#f58518")
    axes.set_ylabel("Outage counts in window")
    axes.set_title("Scheduled vs unscheduled outages")
    axes.tick_params(axis="x", rotation=35)
    axes.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def _plot_availability_distribution(records: list[models.ReliabilityRecord]) -> Path:
    path = figure_path("availability-distribution.png")
    values = [
        record.mean_availability_ratio
        for record in records
        if record.mean_availability_ratio is not None
    ]
    figure, axes = plt.subplots(figsize=(8, 5))
    axes.hist(values, bins=20, color="#4c78a8", edgecolor="white")
    axes.set_xlabel("Mean monthly availability ratio")
    axes.set_ylabel("Station count")
    axes.set_title("Distribution of monthly availability")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def write_report(
    query: models.AccessibilityQuery,
    reliability: models.ReliabilityDataset,
    output_csv: Path,
) -> Path:
    accessible_records = _accessible_records(reliability)
    ranked = sorted(
        accessible_records,
        key=lambda record: (record.reliability_score, record.station_id),
    )
    top_fragile = ranked[0]
    fragile_count = sum(1 for record in accessible_records if record.reliability_label == "fragile")
    at_risk_count = sum(1 for record in accessible_records if record.reliability_label == "at_risk")
    low_chart = _plot_lowest_reliability(accessible_records)
    outage_chart = _plot_scheduled_vs_unscheduled(accessible_records)
    availability_chart = _plot_availability_distribution(accessible_records)

    report = f"""# Outage Reliability Report Tearsheet

## Query

- Geography: `{query.geography}`
- Value: `{query.value}`

## Reliability Snapshot

- Stations scored: {len(reliability.records)}
- Accessible stations scored: {len(accessible_records)}
- Fragile accessible stations: {fragile_count}
- At-risk accessible stations: {at_risk_count}
- Lowest reliability station: `{top_fragile.station_id}` ({top_fragile.station_name})
- Lowest reliability score: {top_fragile.reliability_score:.4f}
- Outage minutes in window: {top_fragile.outage_minutes}

## Figures

### Lowest reliability accessible stations

![Lowest reliability stations](./figures/{low_chart.name})

### Scheduled vs unscheduled outages

![Scheduled vs unscheduled](./figures/{outage_chart.name})

### Distribution of mean availability

![Availability distribution](./figures/{availability_chart.name})

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
                "total_outages",
                "scheduled_outages",
                "unscheduled_outages",
                "mean_availability_ratio",
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
                    "total_outages": record.total_outages,
                    "scheduled_outages": record.scheduled_outages,
                    "unscheduled_outages": record.unscheduled_outages,
                    "mean_availability_ratio": ""
                    if record.mean_availability_ratio is None
                    else f"{record.mean_availability_ratio:.4f}",
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

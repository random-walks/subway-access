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
BOROUGHS = ("Manhattan", "Brooklyn", "Queens")


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
        description="Compare borough-wide accessibility profiles across multiple real snapshots.",
    )
    parser.add_argument("--availability-months", type=int, default=12)
    parser.add_argument("--minutes", type=int, default=10)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument(
        "--no-publish-report",
        action="store_true",
        help="Skip updating tracked reports/ and figures/ (faster local iteration).",
    )
    return parser


def _snapshot_for_borough(
    borough: str,
    *,
    availability_months: int,
    refresh: bool,
) -> models.StudyAreaSnapshot:
    return pipeline.fetch_study_area_snapshot(
        models.AccessibilityQuery(geography="borough", value=borough),
        cache_dir=cache_path(borough.lower()),
        refresh=refresh,
        availability_months=availability_months,
    )


def _profile_rows(
    *,
    minutes: int,
    availability_months: int,
    refresh: bool,
) -> list[dict[str, object]]:
    rows = []
    for borough in BOROUGHS:
        snapshot = _snapshot_for_borough(
            borough,
            availability_months=availability_months,
            refresh=refresh,
        )
        catchments = analysis.generate_catchments(
            snapshot.stations,
            models.CatchmentRequest(minutes=minutes),
        )
        scores = analysis.score_accessibility(
            snapshot.stations,
            catchments,
            snapshot.demographics,
        )
        reliability = analysis.compute_reliability(
            snapshot.stations,
            snapshot.outages,
            models.TimeWindow(days=365),
        )
        summary = analysis.summarize_accessibility_by_group(scores).records[0]
        accessible_station_rows = [
            station
            for station in snapshot.stations.stations
            if station.ada_status == "accessible"
        ]
        accessible_share = (
            0.0
            if not snapshot.stations.stations
            else len(accessible_station_rows) / len(snapshot.stations.stations)
        )
        accessible_reliability = [
            record.reliability_score
            for record in reliability.records
            if record.ada_status == "accessible"
        ]
        rows.append(
            {
                "borough": borough,
                "station_rows": len(snapshot.stations.stations),
                "tract_count": summary.tract_count,
                "coverage_rate": summary.coverage_rate,
                "uncovered_population": summary.uncovered_population,
                "mean_need_score": summary.mean_need_score,
                "mean_nearest_travel_minutes": summary.mean_nearest_travel_minutes
                or 0.0,
                "accessible_station_share": accessible_share,
                "mean_accessible_reliability": 0.0
                if not accessible_reliability
                else sum(accessible_reliability) / len(accessible_reliability),
            }
        )
    return rows


def _plot_metric(
    rows: list[dict[str, object]], *, key: str, title: str, ylabel: str, filename: str
) -> Path:
    path = figure_path(filename)
    labels = [str(row["borough"]) for row in rows]
    values = [float(row[key]) for row in rows]
    figure, axes = plt.subplots(figsize=(8, 5))
    axes.bar(labels, values, color="#4c78a8")
    axes.set_ylabel(ylabel)
    axes.set_title(title)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def write_report(rows: list[dict[str, object]], output_csv: Path) -> Path:
    coverage_chart = _plot_metric(
        rows,
        key="coverage_rate",
        title="Tract coverage rate by borough",
        ylabel="Coverage rate",
        filename="coverage-rate-by-borough.png",
    )
    population_chart = _plot_metric(
        rows,
        key="uncovered_population",
        title="Uncovered population by borough",
        ylabel="Population",
        filename="uncovered-population-by-borough.png",
    )
    station_chart = _plot_metric(
        rows,
        key="accessible_station_share",
        title="Accessible station share by borough",
        ylabel="Share",
        filename="accessible-station-share-by-borough.png",
    )
    reliability_chart = _plot_metric(
        rows,
        key="mean_accessible_reliability",
        title="Mean accessible-station reliability by borough",
        ylabel="Reliability score",
        filename="mean-reliability-by-borough.png",
    )

    report = f"""# Multi-Borough Access Profile Tearsheet

## Summary

- Boroughs compared: {len(rows)}
- Highest coverage borough: `{max(rows, key=lambda row: row[
            "coverage_rate"
        ])["borough"]}`
- Highest uncovered population borough: `{max(rows, key=lambda row: row[
            "uncovered_population"
        ])["borough"]}`

## Figures

### Coverage rate by borough

![Coverage rate](./figures/{coverage_chart.name})

### Uncovered population by borough

![Uncovered population](./figures/{population_chart.name})

### Accessible station share by borough

![Accessible station share](./figures/{station_chart.name})

### Mean accessible-station reliability by borough

![Reliability by borough](./figures/{reliability_chart.name})

## Artifact

- Borough profile CSV: `{output_csv.name}`
"""
    output_path = report_path("multi-borough-access-profile-tearsheet.md")
    output_path.write_text(report, encoding="utf-8")
    return output_path


def main() -> None:
    args = build_parser().parse_args()
    rows = _profile_rows(
        minutes=args.minutes,
        availability_months=args.availability_months,
        refresh=args.refresh,
    )
    output_csv = artifact_path("borough-profile.csv")
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    report_file: Path | None = None
    if not args.no_publish_report:
        report_file = write_report(rows, output_csv)

    print("Multi-Borough Access Profile")
    print("----------------------------")
    print(f"Wrote {output_csv}")
    if report_file is None:
        print(
            "Skipped tracked report generation (--no-publish-report). Default is to refresh reports/."
        )
    else:
        print(f"Wrote tracked report: {report_file}")


if __name__ == "__main__":
    main()

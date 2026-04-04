from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from subway_access import analysis, export, models, pipeline

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
        description="Run borough-scale accessibility gap analysis on official cached data.",
    )
    parser.add_argument("--geography", default="borough")
    parser.add_argument("--value", default="Brooklyn")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=cache_path("brooklyn-snapshot"),
    )
    parser.add_argument("--availability-months", type=int, default=12)
    parser.add_argument("--minutes", type=int, default=10)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--publish-report", action="store_true")
    return parser


def _plot_top_gap_tracts(gaps: models.GapAnalysis) -> Path:
    top_rows = [record for record in gaps.records if record.gap_label == "gap"][:15]
    path = figure_path("top-gap-tracts.png")

    labels = [record.tract_id for record in top_rows]
    values = [record.gap_score for record in top_rows]
    figure, axes = plt.subplots(figsize=(11, 6))
    axes.barh(labels, values, color="#e45756")
    axes.invert_yaxis()
    axes.set_xlabel("Gap score")
    axes.set_title("Highest-need uncovered tracts")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def _plot_need_vs_travel(scores: models.AccessibilityScoreDataset) -> Path:
    path = figure_path("need-vs-travel.png")
    covered = [
        record
        for record in scores.records
        if record.nearest_accessible_travel_minutes is not None
    ]
    figure, axes = plt.subplots(figsize=(8, 6))
    axes.scatter(
        [record.nearest_accessible_travel_minutes for record in covered],
        [record.need_score for record in covered],
        c=[
            "#4c78a8" if record.has_accessible_station else "#e45756"
            for record in covered
        ],
        alpha=0.8,
    )
    axes.set_xlabel("Nearest accessible travel minutes (Euclidean baseline)")
    axes.set_ylabel("Need score")
    axes.set_title("Need vs nearest-access travel time")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def _plot_travel_histogram(scores: models.AccessibilityScoreDataset) -> Path:
    path = figure_path("travel-minutes-histogram.png")
    values = [
        record.nearest_accessible_travel_minutes
        for record in scores.records
        if record.nearest_accessible_travel_minutes is not None
    ]
    figure, axes = plt.subplots(figsize=(8, 5))
    axes.hist(values, bins=18, color="#72b7b2", edgecolor="white")
    axes.set_xlabel("Nearest accessible travel minutes")
    axes.set_ylabel("Tract count")
    axes.set_title("Distribution of nearest accessible travel time")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def write_report(
    query: models.AccessibilityQuery,
    scores: models.AccessibilityScoreDataset,
    gaps: models.GapAnalysis,
    output_csv: Path,
) -> Path:
    summary = analysis.summarize_accessibility_by_group(scores).records[0]
    uncovered = [record for record in gaps.records if record.gap_label == "gap"]
    top_gap = uncovered[0]
    top_gap_chart = _plot_top_gap_tracts(gaps)
    need_chart = _plot_need_vs_travel(scores)
    travel_chart = _plot_travel_histogram(scores)

    report = f"""# Borough Gap Analysis Tearsheet

## Query

- Geography: `{query.geography}`
- Value: `{query.value}`

## Snapshot

- Tracts scored: {summary.tract_count}
- Uncovered tracts: {summary.uncovered_tract_count}
- Coverage rate: {summary.coverage_rate:.1%}
- Uncovered population: {summary.uncovered_population:,}
- Highest gap tract: `{top_gap.tract_id}` ({top_gap.tract_name})
- Highest gap score: {top_gap.gap_score:.4f}
- Nearest accessible station for top gap: {top_gap.nearest_accessible_station_name}

## Figures

### Top gap tracts

![Top gap tracts](./figures/{top_gap_chart.name})

### Need vs nearest-access travel time

![Need vs travel](./figures/{need_chart.name})

### Distribution of nearest-access travel time

![Travel histogram](./figures/{travel_chart.name})

## Artifact

- Gap CSV: `{output_csv.name}`
"""
    tearsheet_path = report_path("borough-gap-analysis-tearsheet.md")
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
    catchments = analysis.generate_catchments(
        snapshot.stations,
        models.CatchmentRequest(minutes=args.minutes),
    )
    scores = analysis.score_accessibility(
        snapshot.stations,
        catchments,
        snapshot.demographics,
    )
    gaps = analysis.analyze_gaps(scores)

    catchments_path = export.export_catchments_geojson(
        catchments,
        models.ExportTarget("geojson", artifact_path("catchments.geojson")),
    )
    gaps_path = export.export_gap_table(
        gaps,
        models.ExportTarget("csv", artifact_path("borough-accessibility-gaps.csv")),
    )
    report_file: Path | None = None
    if args.publish_report:
        report_file = write_report(query, scores, gaps, gaps_path)

    print("Borough Gap Analysis")
    print("--------------------")
    print(f"Study area: {query.geography}={query.value}")
    print(f"Wrote {catchments_path}")
    print(f"Wrote {gaps_path}")
    if report_file is None:
        print(
            "Skipped tracked report generation. Re-run with --publish-report to update reports/."
        )
    else:
        print(f"Wrote tracked report: {report_file}")


if __name__ == "__main__":
    main()

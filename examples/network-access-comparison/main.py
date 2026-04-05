from __future__ import annotations

import argparse
import csv
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
        description="Compare Euclidean and OSM walk access for a real subway study area.",
    )
    parser.add_argument("--geography", default="community_district")
    parser.add_argument("--value", default="Manhattan 03")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=cache_path("manhattan-03-snapshot"),
    )
    parser.add_argument("--availability-months", type=int, default=12)
    parser.add_argument("--minutes", type=int, default=10)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--refresh-graph", action="store_true")
    parser.add_argument("--graph-buffer-meters", type=int, default=250)
    parser.add_argument("--publish-report", action="store_true")
    return parser


def _plot_coverage_change_counts(
    comparison: models.AccessibilityComparisonDataset,
) -> Path:
    counts = {}
    for record in comparison.records:
        counts[record.coverage_change_label] = (
            counts.get(record.coverage_change_label, 0) + 1
        )
    labels = ["both_covered", "euclidean_only", "network_only", "both_uncovered"]
    values = [counts.get(label, 0) for label in labels]
    path = figure_path("coverage-change-counts.png")

    figure, axes = plt.subplots(figsize=(8, 5))
    axes.bar(labels, values, color=["#4c78a8", "#f58518", "#54a24b", "#e45756"])
    axes.set_ylabel("Tract count")
    axes.set_title("Coverage change categories")
    axes.tick_params(axis="x", rotation=20)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def _plot_travel_time_scatter(
    comparison: models.AccessibilityComparisonDataset,
) -> Path:
    rows = [
        record
        for record in comparison.records
        if record.euclidean_travel_minutes is not None
        and record.network_travel_minutes is not None
    ]
    path = figure_path("travel-time-scatter.png")
    figure, axes = plt.subplots(figsize=(8, 6))
    axes.scatter(
        [record.euclidean_travel_minutes for record in rows],
        [record.network_travel_minutes for record in rows],
        c=[
            "#e45756" if record.coverage_change_label == "euclidean_only" else "#4c78a8"
            for record in rows
        ],
        alpha=0.75,
    )
    axes.set_xlabel("Euclidean nearest-access minutes")
    axes.set_ylabel("Network nearest-access minutes")
    axes.set_title("Euclidean vs network travel time")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def _plot_top_network_penalties(
    comparison: models.AccessibilityComparisonDataset,
) -> Path:
    rows = [
        (
            record,
            0.0
            if record.network_travel_minutes is None
            or record.euclidean_travel_minutes is None
            else record.network_travel_minutes - record.euclidean_travel_minutes,
        )
        for record in comparison.records
    ]
    ranked = sorted(rows, key=lambda item: (item[1], item[0].tract_id), reverse=True)[
        :15
    ]
    labels = [item[0].tract_id for item in ranked]
    values = [item[1] for item in ranked]
    path = figure_path("top-network-penalties.png")

    figure, axes = plt.subplots(figsize=(11, 6))
    axes.barh(labels, values, color="#e45756")
    axes.invert_yaxis()
    axes.set_xlabel("Network minus Euclidean minutes")
    axes.set_title("Largest network travel penalties")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def write_report(
    comparison: models.AccessibilityComparisonDataset,
    graph_snapshot: models.NetworkGraphSnapshot,
    output_csv: Path,
) -> Path:
    coverage_chart = _plot_coverage_change_counts(comparison)
    scatter_chart = _plot_travel_time_scatter(comparison)
    penalty_chart = _plot_top_network_penalties(comparison)
    euclidean_only = [
        record
        for record in comparison.records
        if record.coverage_change_label == "euclidean_only"
    ]
    network_only = [
        record
        for record in comparison.records
        if record.coverage_change_label == "network_only"
    ]

    report = f"""# Network Access Comparison Tearsheet

## Summary

- Tracts compared: {len(comparison.records)}
- Graph nodes: {graph_snapshot.node_count}
- Graph edges: {graph_snapshot.edge_count}
- Euclidean-only tracts: {len(euclidean_only)}
- Network-only tracts: {len(network_only)}

## Figures

### Coverage change categories

![Coverage change counts](./figures/{coverage_chart.name})

### Euclidean vs network travel time

![Travel time scatter](./figures/{scatter_chart.name})

### Largest network penalties

![Top network penalties](./figures/{penalty_chart.name})

## Artifact

- Comparison CSV: `{output_csv.name}`
"""
    output_path = report_path("network-access-comparison-tearsheet.md")
    output_path.write_text(report, encoding="utf-8")
    return output_path


def main() -> None:
    args = build_parser().parse_args()
    query = models.AccessibilityQuery(geography=args.geography, value=args.value)
    snapshot = pipeline.fetch_study_area_snapshot(
        query,
        cache_dir=args.cache_dir,
        refresh=args.refresh,
        availability_months=args.availability_months,
    )
    euclidean_catchments = analysis.generate_catchments(
        snapshot.stations,
        models.CatchmentRequest(minutes=args.minutes),
    )
    euclidean_scores = analysis.score_accessibility(
        snapshot.stations,
        euclidean_catchments,
        snapshot.demographics,
    )
    graph_snapshot = pipeline.fetch_walk_graph(
        query,
        cache_dir=args.cache_dir,
        refresh=args.refresh_graph,
        buffer_meters=args.graph_buffer_meters,
    )
    graph, _ = pipeline.load_cached_walk_graph(args.cache_dir)
    network_catchments = analysis.generate_network_isochrones(
        snapshot.stations,
        graph,
        models.CatchmentRequest(minutes=args.minutes),
    )
    network_scores = analysis.score_accessibility_network(
        snapshot.stations,
        graph,
        snapshot.demographics,
        models.CatchmentRequest(minutes=args.minutes),
    )
    comparison = analysis.compare_accessibility_models(
        euclidean_scores,
        network_scores,
    )

    euclidean_path = export.export_catchments_geojson(
        euclidean_catchments,
        models.ExportTarget("geojson", artifact_path("euclidean-catchments.geojson")),
    )
    network_path = export.export_catchments_geojson(
        network_catchments,
        models.ExportTarget("geojson", artifact_path("network-catchments.geojson")),
    )

    output_csv = artifact_path("network-access-comparison.csv")
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "tract_id",
                "tract_name",
                "borough",
                "need_score",
                "euclidean_has_access",
                "network_has_access",
                "euclidean_station_count",
                "network_station_count",
                "euclidean_station_id",
                "network_station_id",
                "euclidean_travel_minutes",
                "network_travel_minutes",
                "euclidean_path_meters",
                "network_path_meters",
                "coverage_change_label",
            ],
        )
        writer.writeheader()
        for record in comparison.records:
            writer.writerow(
                {
                    "tract_id": record.tract_id,
                    "tract_name": record.tract_name,
                    "borough": record.borough,
                    "need_score": f"{record.need_score:.4f}",
                    "euclidean_has_access": str(record.euclidean_has_access).lower(),
                    "network_has_access": str(record.network_has_access).lower(),
                    "euclidean_station_count": record.euclidean_station_count,
                    "network_station_count": record.network_station_count,
                    "euclidean_station_id": record.euclidean_station_id or "",
                    "network_station_id": record.network_station_id or "",
                    "euclidean_travel_minutes": ""
                    if record.euclidean_travel_minutes is None
                    else f"{record.euclidean_travel_minutes:.2f}",
                    "network_travel_minutes": ""
                    if record.network_travel_minutes is None
                    else f"{record.network_travel_minutes:.2f}",
                    "euclidean_path_meters": ""
                    if record.euclidean_path_meters is None
                    else f"{record.euclidean_path_meters:.2f}",
                    "network_path_meters": ""
                    if record.network_path_meters is None
                    else f"{record.network_path_meters:.2f}",
                    "coverage_change_label": record.coverage_change_label,
                }
            )

    report_file: Path | None = None
    if args.publish_report:
        report_file = write_report(comparison, graph_snapshot, output_csv)

    print("Network Access Comparison")
    print("-------------------------")
    print(f"Study area: {query.geography}={query.value}")
    print(f"Graph nodes: {graph_snapshot.node_count}")
    print(f"Graph edges: {graph_snapshot.edge_count}")
    print(f"Wrote {euclidean_path}")
    print(f"Wrote {network_path}")
    print(f"Wrote {output_csv}")
    if report_file is None:
        print(
            "Skipped tracked report generation. Re-run with --publish-report to update reports/."
        )
    else:
        print(f"Wrote tracked report: {report_file}")


if __name__ == "__main__":
    main()

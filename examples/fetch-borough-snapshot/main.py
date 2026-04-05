from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt

from subway_access import models, pipeline

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
        description="Fetch a real official-data subway snapshot into this example cache.",
    )
    parser.add_argument(
        "--geography",
        default="borough",
        choices=("borough", "community_district", "council_district"),
    )
    parser.add_argument("--value", default="Manhattan")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=cache_path("manhattan-snapshot"),
    )
    parser.add_argument("--availability-months", type=int, default=12)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument(
        "--no-publish-report",
        action="store_true",
        help="Skip updating tracked reports/ and figures/ (faster local iteration).",
    )
    parser.add_argument("--skip-gtfs-archive", action="store_true")
    return parser


def write_metadata_json(snapshot: models.StudyAreaSnapshot) -> Path:
    metadata_path = artifact_path("fetch-metadata.json")
    payload = {
        "query": asdict(snapshot.query),
        "generated_at": None
        if snapshot.generated_at is None
        else snapshot.generated_at.isoformat(),
        "cache_dir": None if snapshot.cache_dir is None else str(snapshot.cache_dir),
        "stations": len(snapshot.stations.stations),
        "tracts": len(snapshot.demographics.tracts),
        "availability_rows": len(snapshot.outages.records),
        "sources": [
            {
                "name": item.name,
                "source_url": item.source_url,
                "cache_path": str(item.cache_path),
                "refreshed_at": item.refreshed_at.isoformat(),
                "record_count": item.record_count,
                "notes": item.notes,
            }
            for item in snapshot.metadata
        ],
    }
    metadata_path.write_text(
        f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )
    return metadata_path


def _route_counts(snapshot: models.StudyAreaSnapshot) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for station in snapshot.stations.stations:
        counter.update(station.daytime_routes)
    return counter.most_common(10)


def _status_counts(snapshot: models.StudyAreaSnapshot) -> Counter[str]:
    counter: Counter[str] = Counter()
    for station in snapshot.stations.stations:
        counter[station.ada_status] += 1
    return counter


def _structure_counts(snapshot: models.StudyAreaSnapshot) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for station in snapshot.stations.stations:
        counter[station.structure or "Unknown"] += 1
    return counter.most_common()


def _plot_accessibility_status(snapshot: models.StudyAreaSnapshot) -> Path:
    counts = _status_counts(snapshot)
    labels = ["accessible", "partially_accessible", "not_accessible", "unknown"]
    values = [counts.get(label, 0) for label in labels]
    path = figure_path("accessibility-status.png")

    figure, axes = plt.subplots(figsize=(8, 5))
    axes.bar(labels, values, color=["#4c78a8", "#f58518", "#e45756", "#bab0ab"])
    axes.set_title("Station accessibility status mix")
    axes.set_ylabel("Station rows")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def _plot_top_routes(snapshot: models.StudyAreaSnapshot) -> Path:
    route_rows = _route_counts(snapshot)
    path = figure_path("top-routes.png")
    labels = [route for route, _ in route_rows]
    values = [count for _, count in route_rows]

    figure, axes = plt.subplots(figsize=(9, 5))
    axes.bar(labels, values, color="#4c78a8")
    axes.set_title("Most common daytime routes in the snapshot")
    axes.set_ylabel("Station rows")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def _plot_station_structures(snapshot: models.StudyAreaSnapshot) -> Path:
    structure_rows = _structure_counts(snapshot)
    path = figure_path("station-structures.png")
    labels = [label for label, _ in structure_rows]
    values = [count for _, count in structure_rows]

    figure, axes = plt.subplots(figsize=(8, 5))
    axes.bar(labels, values, color="#72b7b2")
    axes.set_title("Station structure mix")
    axes.set_ylabel("Station rows")
    axes.tick_params(axis="x", rotation=20)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def write_summary_markdown(snapshot: models.StudyAreaSnapshot) -> Path:
    summary_path = artifact_path("fetch-summary.md")
    route_rows = _route_counts(snapshot)
    status_counts = _status_counts(snapshot)
    lines = [
        "# Fetch Summary",
        "",
        "## Snapshot",
        "",
        f"- Study area: `{snapshot.query.geography} = {snapshot.query.value}`",
        f"- Stations in memory: `{len(snapshot.stations.stations)}`",
        f"- Tracts in memory: `{len(snapshot.demographics.tracts)}`",
        f"- Availability rows in memory: `{len(snapshot.outages.records)}`",
        "",
        "## Accessibility mix",
        "",
        f"- Accessible: `{status_counts.get('accessible', 0)}`",
        f"- Partially accessible: `{status_counts.get('partially_accessible', 0)}`",
        f"- Not accessible: `{status_counts.get('not_accessible', 0)}`",
        "",
        "## Sources",
        "",
    ]
    lines.extend(
        f"- `{item.name}`: `{item.record_count}` rows from `{item.source_url}`"
        for item in snapshot.metadata
    )
    lines.extend(
        [
            "",
            "## Top routes",
            "",
            "| Route | Station rows |",
            "| --- | --- |",
        ]
    )
    for route, count in route_rows:
        lines.append(f"| {route} | {count} |")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def write_report(snapshot: models.StudyAreaSnapshot) -> Path:
    status_chart = _plot_accessibility_status(snapshot)
    routes_chart = _plot_top_routes(snapshot)
    structures_chart = _plot_station_structures(snapshot)
    route_rows = _route_counts(snapshot)
    status_counts = _status_counts(snapshot)

    report_file = report_path("fetch-borough-snapshot-tearsheet.md")
    lines = [
        "# Fetch Borough Snapshot Tearsheet",
        "",
        "This tearsheet documents the current pinned real-data snapshot for the",
        "`subway-access` beginner workflow.",
        "",
        "## Executive Summary",
        "",
        f"- Study area: `{snapshot.query.geography} = {snapshot.query.value}`.",
        f"- Loaded `{len(snapshot.stations.stations)}` station rows and `{len(snapshot.demographics.tracts)}` tracts.",
        f"- Availability history rows: `{len(snapshot.outages.records)}`.",
        f"- Accessible station rows: `{status_counts.get('accessible', 0)}`.",
        f"- Partial accessibility rows: `{status_counts.get('partially_accessible', 0)}`.",
        f"- Largest route family in the snapshot: `{route_rows[0][0]}` with `{route_rows[0][1]}` station rows.",
        "",
        "## Source Cadence",
        "",
    ]
    lines.extend(
        f"- `{item.name}` refreshed at `{item.refreshed_at.isoformat()}` with `{item.record_count}` records."
        for item in snapshot.metadata
    )
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "### Accessibility status mix",
            "",
            f"![Accessibility status mix](./figures/{status_chart.name})",
            "",
            "### Top routes in the snapshot",
            "",
            f"![Top routes](./figures/{routes_chart.name})",
            "",
            "### Station structure mix",
            "",
            f"![Station structures](./figures/{structures_chart.name})",
        ]
    )
    report_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_file


def main() -> None:
    args = build_parser().parse_args()
    snapshot = pipeline.fetch_study_area_snapshot(
        models.AccessibilityQuery(geography=args.geography, value=args.value),
        cache_dir=args.cache_dir,
        refresh=args.refresh,
        availability_months=args.availability_months,
        include_gtfs_archive=not args.skip_gtfs_archive,
    )
    metadata_path = write_metadata_json(snapshot)
    summary_path = write_summary_markdown(snapshot)
    report_file: Path | None = None
    if not args.no_publish_report:
        report_file = write_report(snapshot)

    print("Fetch Borough Snapshot")
    print("----------------------")
    print(f"Study area: {snapshot.query.geography}={snapshot.query.value}")
    print(f"Stations in memory: {len(snapshot.stations.stations)}")
    print(f"Tracts in memory: {len(snapshot.demographics.tracts)}")
    print(f"Availability rows in memory: {len(snapshot.outages.records)}")
    print(f"Wrote fetch metadata: {metadata_path}")
    print(f"Wrote fetch summary: {summary_path}")
    if report_file is None:
        print(
            "Skipped tracked report generation (--no-publish-report). Default is to refresh reports/."
        )
    else:
        print(f"Wrote tracked report: {report_file}")


if __name__ == "__main__":
    main()

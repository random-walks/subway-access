from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from subway_access import models, pipeline

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
    parser.add_argument("--publish-report", action="store_true")
    parser.add_argument("--skip-gtfs-archive", action="store_true")
    return parser


def write_metadata_json(snapshot: models.StudyAreaSnapshot) -> Path:
    metadata_path = artifact_path("fetch-metadata.json")
    payload = {
        "query": asdict(snapshot.query),
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


def write_summary_markdown(snapshot: models.StudyAreaSnapshot) -> Path:
    summary_path = artifact_path("fetch-summary.md")
    top_routes = {}
    for station in snapshot.stations.stations:
        for route in station.daytime_routes:
            top_routes[route] = top_routes.get(route, 0) + 1
    sorted_routes = sorted(top_routes.items(), key=lambda item: (-item[1], item[0]))
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
        "## Sources",
        "",
    ]
    for item in snapshot.metadata:
        lines.append(
            f"- `{item.name}`: `{item.record_count}` rows from `{item.source_url}`"
        )
    lines.extend(
        [
            "",
            "## Top Routes",
            "",
            "| Route | Station rows |",
            "| --- | --- |",
        ]
    )
    for route, count in sorted_routes[:10]:
        lines.append(f"| {route} | {count} |")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def write_report(snapshot: models.StudyAreaSnapshot) -> Path:
    report_file = report_path("fetch-borough-snapshot-tearsheet.md")
    lines = [
        "# Fetch Borough Snapshot Tearsheet",
        "",
        "This tearsheet documents the current pinned real-data snapshot for the",
        "`subway-access` borough workflow.",
        "",
        "## Executive Summary",
        "",
        f"- Study area: `{snapshot.query.geography} = {snapshot.query.value}`.",
        f"- Loaded `{len(snapshot.stations.stations)}` stations and `{len(snapshot.demographics.tracts)}` tracts.",
        f"- Availability history rows: `{len(snapshot.outages.records)}`.",
        "",
        "## Source Cadence",
        "",
    ]
    for item in snapshot.metadata:
        lines.append(
            f"- `{item.name}` refreshed at `{item.refreshed_at.isoformat()}` with `{item.record_count}` records."
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
    if args.publish_report:
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
        print("Skipped tracked report generation. Re-run with --publish-report to update reports/.")  # noqa: T201
    else:
        print(f"Wrote tracked report: {report_file}")


if __name__ == "__main__":
    main()

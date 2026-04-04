"""Command-line entry points for the real-data ``subway-access`` workflows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ..analysis import (
    analyze_gaps,
    build_station_metrics,
    compute_reliability,
    generate_catchments,
    score_accessibility,
)
from ..export import (
    export_catchments_geojson,
    export_gap_table,
    export_station_metrics,
)
from ..models import AccessibilityQuery, CatchmentRequest, ExportTarget, TimeWindow
from ..pipeline import fetch_study_area_snapshot, load_cached_snapshot

if TYPE_CHECKING:
    from collections.abc import Sequence

try:
    from .._version import version as _VERSION
except ImportError:  # pragma: no cover - fallback for editable installs
    _VERSION = "0+unknown"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="subway-access",
        description=(
            "Fetch real official subway accessibility data, cache it locally, "
            "and analyze it with the subway-access workflow."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_VERSION}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser(
        "fetch-snapshot",
        help="Fetch and cache a real-data study-area snapshot.",
    )
    fetch_parser.add_argument(
        "--geography",
        required=True,
        help="Boundary layer to select, such as borough or community_district.",
    )
    fetch_parser.add_argument(
        "--value",
        required=True,
        help="Boundary value to load from nyc-geo-toolkit.",
    )
    fetch_parser.add_argument(
        "--cache-dir",
        type=Path,
        required=True,
        help="Directory where the real-data snapshot cache will be written.",
    )
    fetch_parser.add_argument(
        "--availability-months",
        type=int,
        default=12,
        help="Number of months of public availability history to fetch.",
    )
    fetch_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh the cache even if the expected files already exist.",
    )
    fetch_parser.add_argument(
        "--skip-gtfs-archive",
        action="store_true",
        help="Do not cache the raw GTFS subway archive alongside the snapshot.",
    )

    analyze_parser = subparsers.add_parser(
        "analyze-snapshot",
        help="Analyze a cached real-data snapshot and write outputs.",
    )
    analyze_parser.add_argument(
        "--cache-dir",
        type=Path,
        required=True,
        help="Directory containing a fetched real-data snapshot cache.",
    )
    analyze_parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where the analysis GeoJSON and CSV outputs will be written.",
    )
    analyze_parser.add_argument(
        "--minutes",
        type=int,
        default=10,
        help="Walking threshold in minutes for the first-pass catchment.",
    )
    analyze_parser.add_argument(
        "--reliability-window-days",
        type=int,
        default=30,
        help="Rolling outage window used for station reliability scoring.",
    )
    return parser


def run_fetch_snapshot(
    cache_dir: Path,
    *,
    geography: str,
    value: str,
    availability_months: int,
    refresh: bool,
    skip_gtfs_archive: bool,
) -> int:
    """Fetch and cache a real-data snapshot for one study area."""

    snapshot = fetch_study_area_snapshot(
        AccessibilityQuery(geography=geography, value=value),
        cache_dir=cache_dir,
        refresh=refresh,
        availability_months=availability_months,
        include_gtfs_archive=not skip_gtfs_archive,
    )
    sys.stdout.write("Fetched subway-access real-data snapshot:\n")
    sys.stdout.write(
        f"- Study area: {snapshot.query.geography}={snapshot.query.value}\n"
    )
    sys.stdout.write(f"- Cache directory: {cache_dir}\n")
    sys.stdout.write(f"- Stations: {len(snapshot.stations.stations)}\n")
    sys.stdout.write(f"- Tracts: {len(snapshot.demographics.tracts)}\n")
    sys.stdout.write(f"- Availability rows: {len(snapshot.outages.records)}\n")
    return 0


def run_analyze_snapshot(
    cache_dir: Path,
    output_dir: Path,
    *,
    minutes: int,
    reliability_window_days: int,
) -> int:
    """Analyze a cached snapshot and export real-data outputs."""

    snapshot = load_cached_snapshot(cache_dir)
    if minutes <= 0:
        message = "Catchment minutes must be greater than zero."
        raise ValueError(message)

    catchments = generate_catchments(
        snapshot.stations, CatchmentRequest(minutes=minutes)
    )
    scores = score_accessibility(snapshot.stations, catchments, snapshot.demographics)
    gaps = analyze_gaps(scores)
    reliability = compute_reliability(
        snapshot.stations,
        snapshot.outages,
        TimeWindow(days=reliability_window_days),
    )
    station_metrics = build_station_metrics(
        snapshot.stations,
        catchments,
        scores,
        reliability=reliability,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    catchments_path = output_dir / "catchments.geojson"
    gaps_path = output_dir / "accessibility-gaps.csv"
    station_metrics_path = output_dir / "station-metrics.csv"

    export_catchments_geojson(
        catchments,
        ExportTarget(format="geojson", output_path=catchments_path),
    )
    export_gap_table(gaps, ExportTarget(format="csv", output_path=gaps_path))
    export_station_metrics(
        station_metrics,
        ExportTarget(format="csv", output_path=station_metrics_path),
    )

    sys.stdout.write("Generated subway-access snapshot outputs:\n")
    sys.stdout.write(
        f"- Study area: {snapshot.query.geography}={snapshot.query.value}\n"
    )
    sys.stdout.write(f"- Catchment GeoJSON: {catchments_path}\n")
    sys.stdout.write(f"- Accessibility gap CSV: {gaps_path}\n")
    sys.stdout.write(f"- Station metrics CSV: {station_metrics_path}\n")
    return 0


def run_demo(
    output_dir: Path,
    *,
    minutes: int,
    reliability_window_days: int,
) -> int:
    """Compatibility wrapper for the old demo command."""

    del output_dir, minutes, reliability_window_days
    message = (
        "`subway-access demo` has been replaced by `fetch-snapshot` and "
        "`analyze-snapshot` for real-data workflows."
    )
    raise ValueError(message)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the installed CLI."""

    parser = _build_parser()
    command_line = list(argv) if argv is not None else None
    args = parser.parse_args(command_line)

    try:
        if args.command == "fetch-snapshot":
            return run_fetch_snapshot(
                args.cache_dir,
                geography=args.geography,
                value=args.value,
                availability_months=args.availability_months,
                refresh=args.refresh,
                skip_gtfs_archive=args.skip_gtfs_archive,
            )
        if args.command == "analyze-snapshot":
            return run_analyze_snapshot(
                args.cache_dir,
                args.output_dir,
                minutes=args.minutes,
                reliability_window_days=args.reliability_window_days,
            )
        if args.command == "demo":
            return run_demo(
                args.output_dir,
                minutes=args.minutes,
                reliability_window_days=args.reliability_window_days,
            )
        message = f"Unsupported command: {args.command}"
        raise RuntimeError(message)
    except ValueError as exc:
        sys.stderr.write(f"{parser.prog}: error: {exc}\n")
        raise SystemExit(2) from exc

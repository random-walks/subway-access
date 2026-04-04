"""Command-line entry points for the ``subway-access`` demo workflow."""

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
from ..io import (
    load_accessibility_status,
    load_census_data,
    load_gtfs,
    load_outages,
    load_pedestrian_network,
)
from ..models import CatchmentRequest, ExportTarget, TimeWindow

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
            "Run the packaged subway accessibility demo workflow with reliability "
            "and station metrics outputs."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_VERSION}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo_parser = subparsers.add_parser(
        "demo",
        help="Run the packaged fixture workflow and write map/table outputs.",
    )
    demo_parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where the demo GeoJSON and CSV outputs will be written.",
    )
    demo_parser.add_argument(
        "--minutes",
        type=int,
        default=10,
        help="Walking threshold in minutes for the first-pass catchment.",
    )
    demo_parser.add_argument(
        "--reliability-window-days",
        type=int,
        default=30,
        help="Rolling outage window used for station reliability scoring.",
    )
    return parser


def run_demo(
    output_dir: Path,
    *,
    minutes: int,
    reliability_window_days: int,
) -> int:
    """Run the packaged demo analysis and export outputs."""

    if minutes <= 0:
        message = "Catchment minutes must be greater than zero."
        raise ValueError(message)

    stations = load_gtfs().with_accessibility(load_accessibility_status())
    demographics = load_census_data()
    outages = load_outages()
    pedestrian_network = load_pedestrian_network()
    catchments = generate_catchments(stations, CatchmentRequest(minutes=minutes))
    scores = score_accessibility(stations, catchments, demographics)
    gaps = analyze_gaps(scores)
    reliability = compute_reliability(
        stations,
        outages,
        TimeWindow(days=reliability_window_days),
    )
    station_metrics = build_station_metrics(
        stations,
        catchments,
        scores,
        reliability=reliability,
        pedestrian_network=pedestrian_network,
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

    sys.stdout.write("Generated subway-access demo outputs:\n")
    sys.stdout.write(f"- Catchment GeoJSON: {catchments_path}\n")
    sys.stdout.write(f"- Accessibility gap CSV: {gaps_path}\n")
    sys.stdout.write(f"- Station metrics CSV: {station_metrics_path}\n")
    sys.stdout.write(
        f"- Processed {len(stations.stations)} stations and {len(gaps.records)} tracts.\n"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the installed CLI."""

    parser = _build_parser()
    command_line = list(argv) if argv is not None else None
    args = parser.parse_args(command_line)

    if args.command != "demo":
        message = f"Unsupported command: {args.command}"
        raise RuntimeError(message)

    try:
        return run_demo(
            args.output_dir,
            minutes=args.minutes,
            reliability_window_days=args.reliability_window_days,
        )
    except ValueError as exc:
        sys.stderr.write(f"{parser.prog}: error: {exc}\n")
        raise SystemExit(2) from exc

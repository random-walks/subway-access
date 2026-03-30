"""Command line entry points for the implemented v0.1 demo workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
from collections.abc import Sequence

from .exporters import export_catchments_geojson, export_gap_table
from .loaders import load_accessibility_status, load_census_data, load_gtfs
from .models import CatchmentRequest, ExportTarget
from .processors import analyze_gaps, generate_catchments, score_accessibility


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="subway-access",
        description=(
            "Run the fixture-backed v0.1 subway accessibility demo workflow."
        ),
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

    return parser


def run_demo(output_dir: Path, *, minutes: int) -> int:
    """Run the packaged v0.1 demo analysis and export outputs."""

    stations = load_gtfs().with_accessibility(load_accessibility_status())
    demographics = load_census_data()
    catchments = generate_catchments(stations, CatchmentRequest(minutes=minutes))
    scores = score_accessibility(stations, catchments, demographics)
    gaps = analyze_gaps(scores)

    output_dir.mkdir(parents=True, exist_ok=True)
    catchments_path = output_dir / "catchments.geojson"
    gaps_path = output_dir / "accessibility_gaps.csv"

    export_catchments_geojson(
        catchments, ExportTarget(format="geojson", output_path=catchments_path)
    )
    export_gap_table(gaps, ExportTarget(format="csv", output_path=gaps_path))

    print(f"Wrote catchment GeoJSON to {catchments_path}")
    print(f"Wrote accessibility gap CSV to {gaps_path}")
    print(f"Processed {len(stations.stations)} stations and {len(gaps.records)} tracts.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the implemented CLI."""

    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "demo":
        return run_demo(args.output_dir, minutes=args.minutes)

    parser.error(f"Unsupported command: {args.command}")
    return 2

"""Command line entry points for the implemented v0.1 demo workflow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .exporters import export_catchments_geojson, export_gap_table
from .loaders import load_accessibility_status, load_census_data, load_gtfs
from .models import CatchmentRequest, ExportTarget
from .processors import analyze_gaps, generate_catchments, score_accessibility

if TYPE_CHECKING:
    from collections.abc import Sequence

try:
    from ._version import version as _VERSION
except ImportError:  # pragma: no cover - fallback for editable installs
    _VERSION = "0+unknown"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="subway-access",
        description=(
            "Run the fixture-backed v0.1 subway accessibility demo workflow."
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

    return parser


def run_demo(output_dir: Path, *, minutes: int) -> int:
    """Run the packaged v0.1 demo analysis and export outputs."""

    if minutes <= 0:
        message = "Catchment minutes must be greater than zero."
        raise ValueError(message)

    stations = load_gtfs().with_accessibility(load_accessibility_status())
    demographics = load_census_data()
    catchments = generate_catchments(stations, CatchmentRequest(minutes=minutes))
    scores = score_accessibility(stations, catchments, demographics)
    gaps = analyze_gaps(scores)

    output_dir.mkdir(parents=True, exist_ok=True)
    catchments_path = output_dir / "catchments.geojson"
    gaps_path = output_dir / "accessibility-gaps.csv"

    export_catchments_geojson(
        catchments, ExportTarget(format="geojson", output_path=catchments_path)
    )
    export_gap_table(gaps, ExportTarget(format="csv", output_path=gaps_path))

    sys.stdout.write("Generated subway-access v0.1 demo outputs:\n")
    sys.stdout.write(f"- Catchment GeoJSON: {catchments_path}\n")
    sys.stdout.write(f"- Accessibility gap CSV: {gaps_path}\n")
    sys.stdout.write(
        f"- Processed {len(stations.stations)} stations and {len(gaps.records)} tracts.\n"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the implemented CLI."""

    parser = _build_parser()
    command_line = list(argv) if argv is not None else None
    args = parser.parse_args(command_line)

    if args.command != "demo":
        message = f"Unsupported command: {args.command}"
        raise RuntimeError(message)

    try:
        return run_demo(args.output_dir, minutes=args.minutes)
    except ValueError as exc:
        parser._print_message(f"{parser.prog}: error: {exc}\n", sys.stderr)
        raise SystemExit(2) from exc

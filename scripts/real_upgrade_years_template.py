#!/usr/bin/env python3
"""Generate per-borough CSV templates for real ADA upgrade year research.

Fetches the live MTA station catalog (or reads from a cached snapshot),
filters to currently accessible stations, and writes one CSV per borough
with populated station metadata and empty columns for FOIA/research data
(upgrade year, capital program, project cost, etc.).

Output lands in ``seeds/enhanced/upgrade_templates/``.

Usage::

    # From live MTA API (default):
    python scripts/real_upgrade_years_template.py

    # From a cached snapshot directory:
    python scripts/real_upgrade_years_template.py --cache-dir cache/manhattan
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the library is importable when running from the repo root.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from subway_access.io._mta import (  # noqa: E402
    build_station_snapshot_rows,
    fetch_mta_station_catalog,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OUTPUT_DIR = _REPO_ROOT / "seeds" / "enhanced" / "upgrade_templates"

# Columns populated from the live MTA API.
_KNOWN_COLUMNS = [
    "station_id",
    "station_name",
    "borough",
    "latitude",
    "longitude",
    "complex_id",
    "gtfs_stop_id",
    "daytime_routes",
    "line",
    "division",
    "structure",
    "ada_status",
]

# Empty columns to be filled via FOIA requests, news scraping,
# MTA capital program reports, or AI-driven enhancement.
_FOIA_COLUMNS = [
    "upgrade_year",
    "upgrade_source",
    "capital_program",
    "project_id",
    "contract_number",
    "construction_start_date",
    "construction_end_date",
    "project_cost_millions",
    "contractor",
    "accessibility_features",
    "notes",
]

ALL_COLUMNS = _KNOWN_COLUMNS + _FOIA_COLUMNS

_BOROUGH_FILENAME = {
    "Manhattan": "manhattan.csv",
    "Brooklyn": "brooklyn.csv",
    "Bronx": "bronx.csv",
    "Queens": "queens.csv",
    "Staten Island": "staten_island.csv",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_from_cache(
    cache_dir: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Read stations.csv and accessibility.csv from a cached snapshot."""

    stations_path = cache_dir / "stations.csv"
    accessibility_path = cache_dir / "accessibility.csv"

    if not stations_path.exists():
        sys.exit(f"Error: {stations_path} not found.")
    if not accessibility_path.exists():
        sys.exit(f"Error: {accessibility_path} not found.")

    def _read_csv(path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    return _read_csv(stations_path), _read_csv(accessibility_path)


def _build_template_rows(
    station_rows: list[dict[str, str]],
    accessibility_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Merge station + accessibility rows, filter to accessible, add FOIA cols."""

    ada_by_id = {r["station_id"]: r for r in accessibility_rows}
    rows: list[dict[str, str]] = []

    for st in station_rows:
        ada_row = ada_by_id.get(st["station_id"], {})
        if ada_row.get("ada_status") != "accessible":
            continue

        row: dict[str, str] = {
            "station_id": st["station_id"],
            "station_name": st.get("name", st.get("station_name", "")),
            "borough": st["borough"],
            "latitude": st["latitude"],
            "longitude": st["longitude"],
            "complex_id": st.get("complex_id", ""),
            "gtfs_stop_id": st.get("gtfs_stop_id", ""),
            "daytime_routes": st.get("daytime_routes", ""),
            "line": st.get("line", ""),
            "division": st.get("division", ""),
            "structure": st.get("structure", ""),
            "ada_status": ada_row["ada_status"],
        }
        # Add empty FOIA columns.
        for col in _FOIA_COLUMNS:
            row[col] = ""
        rows.append(row)

    rows.sort(key=lambda r: int(r["station_id"]))
    return rows


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write rows to a CSV file with a fixed column order."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=ALL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _write_templates(template_rows: list[dict[str, str]]) -> None:
    """Group by borough and write per-borough + all-boroughs CSVs."""

    by_borough: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in template_rows:
        by_borough[row["borough"]].append(row)

    print(f"Writing templates to {OUTPUT_DIR}/")
    for borough in sorted(by_borough):
        filename = _BOROUGH_FILENAME.get(
            borough, f"{borough.lower().replace(' ', '_')}.csv"
        )
        path = OUTPUT_DIR / filename
        _write_csv(path, by_borough[borough])
        print(f"  {borough}: {len(by_borough[borough])} stations -> {path.name}")

    all_path = OUTPUT_DIR / "_all_boroughs.csv"
    _write_csv(all_path, template_rows)
    print(f"  All boroughs: {len(template_rows)} stations -> {all_path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate per-borough ADA upgrade year templates."
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help=(
            "Path to a cached snapshot directory containing stations.csv "
            "and accessibility.csv.  When omitted the script fetches live "
            "data from the MTA API."
        ),
    )
    args = parser.parse_args()

    if args.cache_dir is not None:
        print(f"Loading stations from cached snapshot: {args.cache_dir}")
        station_rows, accessibility_rows = _load_from_cache(args.cache_dir)
        print(f"  Loaded {len(station_rows)} stations from cache.")
    else:
        print("Fetching MTA station catalog ...")
        try:
            raw_rows = fetch_mta_station_catalog()
        except Exception as exc:
            sys.exit(
                f"Error: Could not reach the MTA API.\n"
                f"  {exc}\n\n"
                f"Tip: If you have a cached snapshot, re-run with:\n"
                f"  python scripts/real_upgrade_years_template.py "
                f"--cache-dir <path-to-snapshot>"
            )
        print(f"  Retrieved {len(raw_rows)} raw station rows from MTA API.")
        station_rows, accessibility_rows = build_station_snapshot_rows(raw_rows)
        print(f"  Normalized to {len(station_rows)} unique stations.")

    template_rows = _build_template_rows(station_rows, accessibility_rows)
    print(f"  {len(template_rows)} stations are currently ADA-accessible.\n")

    if not template_rows:
        sys.exit("No accessible stations found. Nothing to write.")

    _write_templates(template_rows)
    print("\nDone. Templates are ready for enhancement.")


if __name__ == "__main__":
    main()

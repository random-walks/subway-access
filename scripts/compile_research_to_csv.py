"""Compile per-station research data.json files into the upgrade template CSVs.

Reads station metadata from the existing template CSVs, merges in any
completed research from ``seeds/enhanced/research/*/data.json``, and
writes updated per-borough CSVs compatible with the pipeline's
``load_known_upgrades_from_dir()``.

Usage::

    # Compile all research into CSVs (overwrites templates)
    python scripts/compile_research_to_csv.py

    # Dry-run: show what would change without writing
    python scripts/compile_research_to_csv.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = _REPO_ROOT / "seeds" / "enhanced" / "upgrade_templates"
RESEARCH_DIR = _REPO_ROOT / "seeds" / "enhanced" / "research"

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


def load_all_stations() -> list[dict[str, str]]:
    """Read all stations from per-borough template CSVs."""
    stations: list[dict[str, str]] = []
    for path in sorted(TEMPLATES_DIR.glob("*.csv")):
        if path.name.startswith("_"):
            continue
        with path.open(newline="", encoding="utf-8") as fh:
            stations.extend(csv.DictReader(fh))
    stations.sort(key=lambda r: int(r["station_id"]))
    return stations


def load_research() -> dict[str, dict]:
    """Load all data.json files keyed by station_id."""
    research: dict[str, dict] = {}
    for data_path in sorted(RESEARCH_DIR.glob("*/data.json")):
        try:
            with data_path.open(encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue
        sid = data.get("station_id", "")
        if sid:
            research[str(sid)] = data
    return research


def merge(
    stations: list[dict[str, str]], research: dict[str, dict]
) -> list[dict[str, str]]:
    """Merge research data into station rows."""
    merged: list[dict[str, str]] = []
    for st in stations:
        row = {col: st.get(col, "") for col in _KNOWN_COLUMNS}
        sid = st["station_id"]
        data = research.get(sid, {})
        for col in _FOIA_COLUMNS:
            val = data.get(col)
            if val is None:
                row[col] = ""
            elif isinstance(val, (int, float)):
                row[col] = str(int(val)) if col == "upgrade_year" else str(val)
            else:
                row[col] = str(val)
        merged.append(row)
    return merged


def write_csvs(rows: list[dict[str, str]]) -> None:
    """Write per-borough + all-boroughs CSVs."""
    by_borough: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_borough[row["borough"]].append(row)

    for borough in sorted(by_borough):
        filename = _BOROUGH_FILENAME.get(
            borough, f"{borough.lower().replace(' ', '_')}.csv"
        )
        path = TEMPLATES_DIR / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=ALL_COLUMNS)
            writer.writeheader()
            writer.writerows(by_borough[borough])
        print(f"  {borough}: {len(by_borough[borough])} stations -> {path.name}")

    all_path = TEMPLATES_DIR / "_all_boroughs.csv"
    with all_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=ALL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  All boroughs: {len(rows)} stations -> _all_boroughs.csv")


def show_dry_run(
    stations: list[dict[str, str]], research: dict[str, dict]
) -> None:
    """Show what would change without writing."""
    found = 0
    for st in stations:
        sid = st["station_id"]
        data = research.get(sid)
        if data and data.get("upgrade_year") is not None:
            print(
                f"  {sid:>3s}  {st['station_name']:<40s}  "
                f"upgrade_year={data['upgrade_year']}"
            )
            found += 1
    print(f"\n  {found} stations with upgrade data out of {len(stations)} total.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile station research into upgrade template CSVs."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing files.",
    )
    args = parser.parse_args()

    stations = load_all_stations()
    if not stations:
        sys.exit("No stations found in template CSVs.")

    research = load_research()
    print(f"Found {len(research)} research files.\n")

    if args.dry_run:
        show_dry_run(stations, research)
        return

    merged = merge(stations, research)
    write_csvs(merged)
    print("\nDone. CSVs updated with research data.")


if __name__ == "__main__":
    main()

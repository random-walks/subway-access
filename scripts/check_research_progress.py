"""Track ADA upgrade research progress across all 157 stations.

Usage::

    # Show per-borough progress summary
    python scripts/check_research_progress.py

    # Show the next unresearched station as JSON (for automation)
    python scripts/check_research_progress.py --next

    # List all unresearched stations
    python scripts/check_research_progress.py --unresearched

    # Filter to a specific borough
    python scripts/check_research_progress.py --borough manhattan

    # Create research folders for any stations that don't have them yet
    python scripts/check_research_progress.py --scaffold
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = _REPO_ROOT / "seeds" / "enhanced" / "upgrade_templates"
RESEARCH_DIR = _REPO_ROOT / "seeds" / "enhanced" / "research"

_BOROUGH_ALIASES = {
    "manhattan": "Manhattan",
    "brooklyn": "Brooklyn",
    "bronx": "Bronx",
    "queens": "Queens",
    "staten_island": "Staten Island",
    "staten-island": "Staten Island",
    "statenisland": "Staten Island",
}

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


def slugify_station(station_id: str, station_name: str) -> str:
    """Create folder name: zero-padded station_id + slugified name."""
    slug = station_name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return f"{int(station_id):03d}-{slug}"


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


def is_researched(folder: Path) -> bool:
    """Check if a station's research is complete."""
    data_path = folder / "data.json"
    if not data_path.exists():
        return False
    try:
        with data_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return False
    # Researched = has a non-null upgrade_year OR a non-empty notes field
    if data.get("upgrade_year") is not None:
        return True
    return bool(data.get("notes", "").strip())


def scaffold(stations: list[dict[str, str]]) -> int:
    """Create research folders + starter files for any missing stations."""
    created = 0
    for st in stations:
        slug = slugify_station(st["station_id"], st["station_name"])
        folder = RESEARCH_DIR / slug

        data_path = folder / "data.json"
        md_path = folder / "research.md"

        if data_path.exists() and md_path.exists():
            continue

        folder.mkdir(parents=True, exist_ok=True)

        if not data_path.exists():
            data = {
                "station_id": st["station_id"],
                "upgrade_year": None,
                "upgrade_source": "",
                "capital_program": "",
                "project_id": "",
                "contract_number": "",
                "construction_start_date": "",
                "construction_end_date": "",
                "project_cost_millions": None,
                "contractor": "",
                "accessibility_features": "",
                "notes": "",
            }
            with data_path.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
                fh.write("\n")

        if not md_path.exists():
            routes = st.get("daytime_routes", "")
            line = st.get("line", "")
            division = st.get("division", "")
            md = (
                f"# {st['station_name']} (ID: {st['station_id']})\n"
                f"\n"
                f"**Borough**: {st['borough']}  \n"
                f"**Routes**: {routes}  \n"
                f"**Line**: {line}  \n"
                f"**Division**: {division}\n"
                f"\n"
                f"## Research Findings\n"
                f"\n"
                f"_Not yet researched._\n"
                f"\n"
                f"## Sources\n"
                f"\n"
                f"## Notes\n"
            )
            md_path.write_text(md, encoding="utf-8")

        created += 1

    return created


def show_progress(stations: list[dict[str, str]], borough_filter: str | None) -> None:
    """Print per-borough progress bars."""
    by_borough: dict[str, list[dict[str, str]]] = {}
    for st in stations:
        by_borough.setdefault(st["borough"], []).append(st)

    total_done = 0
    total_count = 0
    borough_order = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]

    for borough in borough_order:
        sts = by_borough.get(borough, [])
        if borough_filter and borough != borough_filter:
            continue
        done = sum(
            1
            for s in sts
            if is_researched(
                RESEARCH_DIR / slugify_station(s["station_id"], s["station_name"])
            )
        )
        count = len(sts)
        total_done += done
        total_count += count
        pct = done / count * 100 if count else 0
        bar_len = 20
        filled = int(bar_len * done / count) if count else 0
        bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
        pad = 14 - len(borough)
        print(f"  {borough}:{' ' * pad}{done:3d} / {count:<3d} ({pct:5.1f}%)  {bar}")

    if not borough_filter:
        pct = total_done / total_count * 100 if total_count else 0
        print(f"\n  Total: {total_done} / {total_count} ({pct:.1f}%)")


def show_next(stations: list[dict[str, str]], borough_filter: str | None) -> None:
    """Print JSON for the next unresearched station."""
    for st in stations:
        if borough_filter and st["borough"] != borough_filter:
            continue
        slug = slugify_station(st["station_id"], st["station_name"])
        if not is_researched(RESEARCH_DIR / slug):
            info = {
                "station_id": st["station_id"],
                "station_name": st["station_name"],
                "borough": st["borough"],
                "folder": slug,
                "daytime_routes": st.get("daytime_routes", ""),
                "line": st.get("line", ""),
            }
            print(json.dumps(info))
            return
    print("null")


def show_unresearched(
    stations: list[dict[str, str]], borough_filter: str | None
) -> None:
    """List all unresearched stations."""
    for st in stations:
        if borough_filter and st["borough"] != borough_filter:
            continue
        slug = slugify_station(st["station_id"], st["station_name"])
        if not is_researched(RESEARCH_DIR / slug):
            print(
                f"  {st['station_id']:>3s}  {st['station_name']:<45s}  {st['borough']}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Track ADA upgrade research progress.")
    parser.add_argument(
        "--next", action="store_true", help="Print next unresearched station as JSON."
    )
    parser.add_argument(
        "--unresearched", action="store_true", help="List all unresearched stations."
    )
    parser.add_argument(
        "--scaffold",
        action="store_true",
        help="Create research folders for stations that don't have them yet.",
    )
    parser.add_argument(
        "--borough",
        type=str,
        default=None,
        help="Filter to a specific borough (e.g., manhattan, brooklyn).",
    )
    args = parser.parse_args()

    stations = load_all_stations()
    if not stations:
        sys.exit("No stations found in template CSVs.")

    borough_filter = None
    if args.borough:
        key = args.borough.lower().replace(" ", "_")
        borough_filter = _BOROUGH_ALIASES.get(key)
        if not borough_filter:
            sys.exit(
                f"Unknown borough: {args.borough!r}. "
                f"Use: manhattan, brooklyn, queens, bronx, staten_island"
            )

    if args.scaffold:
        created = scaffold(stations)
        print(f"Scaffolded {created} new research folders.")
        if created == 0:
            print("All 157 folders already exist.")
        return

    if args.next:
        show_next(stations, borough_filter)
        return

    if args.unresearched:
        show_unresearched(stations, borough_filter)
        return

    print("Research Progress:\n")
    show_progress(stations, borough_filter)


if __name__ == "__main__":
    main()

"""Station ADA upgrade timeline construction."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from ._models import StationUpgradeRecord, UpgradeTimeline

if TYPE_CHECKING:
    from pathlib import Path

    from ..models import StationDataset

# Known ADA upgrade years for selected stations.
# Source: MTA Capital Program reports, NYC Council accessibility studies.
# This is a starter dataset; production use should supplement with
# the full MTA Capital Program database or Freedom of Information
# Law (FOIL) responses.
_KNOWN_UPGRADE_YEARS: dict[str, int] = {
    # Stations made accessible under 2015-2019 Capital Program
    # (Examples — the full list would come from MTA data)
}


def build_upgrade_timeline(
    station_data: StationDataset,
    *,
    known_upgrades: dict[str, int] | None = None,
    known_upgrade_sources: dict[str, str] | None = None,
    source: str = "mta_ada_status",
) -> UpgradeTimeline:
    """Build an upgrade timeline from station dataset and known upgrade years.

    For stations currently marked "accessible" but without a known upgrade
    year, they are treated as always-accessible (upgrade_year=None, which
    means they are in the treatment group for all periods).

    Args:
        station_data: Current station dataset with ADA status.
        known_upgrades: Optional mapping of station_id -> upgrade year.
            Overrides or supplements the built-in database.
        known_upgrade_sources: Optional mapping of station_id -> per-station
            provenance tag. When a station id appears here, the tag is used
            as the record's ``upgrade_source`` — letting callers distinguish
            e.g. ``"press_release_sourced"`` stations from
            ``"hash_fallback"`` stations in the same timeline. Stations
            without an explicit entry fall back to the ``source`` kwarg.
        source: Default label used for the data source when no per-station
            tag is supplied via ``known_upgrade_sources``.

    Returns:
        An UpgradeTimeline with one record per station.

    Example:
        >>> timeline = build_upgrade_timeline(stations)
        >>> timeline.stations_upgraded_by(2020)
        ('S1', 'S2')
    """

    upgrades = dict(_KNOWN_UPGRADE_YEARS)
    if known_upgrades:
        upgrades.update(known_upgrades)

    per_station_sources = known_upgrade_sources or {}

    records: list[StationUpgradeRecord] = []
    for station in station_data.stations:
        upgrade_year: int | None = upgrades.get(station.station_id)
        records.append(
            StationUpgradeRecord(
                station_id=station.station_id,
                station_name=station.name,
                borough=station.borough,
                latitude=station.latitude,
                longitude=station.longitude,
                upgrade_year=upgrade_year,
                upgrade_source=per_station_sources.get(station.station_id, source),
            )
        )

    return UpgradeTimeline(records=tuple(records))


def load_known_upgrades(csv_path: Path) -> dict[str, int]:
    """Read a seeds CSV and return ``{station_id: upgrade_year}`` for filled rows.

    Rows where ``upgrade_year`` is empty or non-numeric are silently skipped.
    """
    known: dict[str, int] = {}
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            year_str = row.get("upgrade_year", "").strip()
            station_id = row.get("station_id", "").strip()
            if year_str and station_id:
                try:
                    known[station_id] = int(year_str)
                except ValueError:
                    continue
    return known


def load_known_upgrades_from_dir(directory: Path) -> dict[str, int]:
    """Scan *directory* for per-borough CSVs and merge all filled upgrade years.

    ``_all_boroughs.csv`` is excluded to avoid double-counting.
    """
    known: dict[str, int] = {}
    for path in sorted(directory.glob("*.csv")):
        if path.name.startswith("_"):
            continue
        known.update(load_known_upgrades(path))
    return known

"""Station ADA upgrade timeline construction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._models import StationUpgradeRecord, UpgradeTimeline

if TYPE_CHECKING:
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
        source: Label for the data source.

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
                upgrade_source=source,
            )
        )

    return UpgradeTimeline(records=tuple(records))

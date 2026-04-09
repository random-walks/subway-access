"""Station and accessibility status models."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._common import AccessibilityLabel


@dataclass(frozen=True, slots=True)
class Station:
    """Station record used by the current accessibility workflow."""

    station_id: str
    name: str
    borough: str
    latitude: float
    longitude: float
    complex_id: str | None = None
    gtfs_stop_id: str | None = None
    daytime_routes: tuple[str, ...] = ()
    division: str | None = None
    line: str | None = None
    structure: str | None = None
    north_direction_label: str | None = None
    south_direction_label: str | None = None
    accessibility_notes: str = ""
    source: str = ""
    ada_status: AccessibilityLabel = "unknown"

    @property
    def is_accessible(self) -> bool:
        """Return whether the station counts as accessible in the current model."""

        return self.ada_status == "accessible"

    @property
    def is_partially_accessible(self) -> bool:
        """Return whether the station has partial accessibility coverage."""

        return self.ada_status == "partially_accessible"


@dataclass(frozen=True, slots=True)
class AccessibilityStatus:
    """ADA accessibility status keyed by station identifier."""

    station_id: str
    ada_status: AccessibilityLabel
    notes: str = ""
    source: str = ""


@dataclass(frozen=True, slots=True)
class StationDataset:
    """Loaded station rows for an analysis run."""

    stations: tuple[Station, ...]

    def as_mapping(self) -> dict[str, Station]:
        return {station.station_id: station for station in self.stations}

    @property
    def accessible_stations(self) -> tuple[Station, ...]:
        return tuple(station for station in self.stations if station.is_accessible)

    def with_accessibility(self, accessibility: AccessibilityDataset) -> StationDataset:
        """Merge ADA status into the station dataset."""

        status_by_station = accessibility.as_mapping()
        station_ids = {station.station_id for station in self.stations}
        unknown_ids = sorted(set(status_by_station).difference(station_ids))
        if unknown_ids:
            joined_ids = ", ".join(unknown_ids)
            message = (
                f"Accessibility data references unknown station IDs: {joined_ids}."
            )
            raise ValueError(message)

        merged = tuple(
            replace(
                station,
                ada_status=status_by_station.get(
                    station.station_id,
                    AccessibilityStatus(
                        station_id=station.station_id,
                        ada_status="unknown",
                    ),
                ).ada_status,
            )
            for station in self.stations
        )
        return StationDataset(stations=merged)


@dataclass(frozen=True, slots=True)
class AccessibilityDataset:
    """Loaded ADA status rows."""

    statuses: tuple[AccessibilityStatus, ...]

    def as_mapping(self) -> dict[str, AccessibilityStatus]:
        return {status.station_id: status for status in self.statuses}

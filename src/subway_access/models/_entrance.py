"""Entrance and GTFS-Pathways models."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Entrance:
    """A street-level subway entrance or exit from MTA Open Data (entrances / exits layer)."""

    entrance_id: str
    station_id: str
    latitude: float
    longitude: float
    stop_name: str
    constituent_station_name: str
    complex_id: str | None
    gtfs_stop_id: str | None
    borough_code: str
    entrance_type: str
    entry_allowed: bool
    exit_allowed: bool
    division: str | None = None
    line: str | None = None
    daytime_routes: tuple[str, ...] = ()
    source: str = ""


@dataclass(frozen=True, slots=True)
class EntranceDataset:
    """Loaded entrance / exit point rows for a study area."""

    entrances: tuple[Entrance, ...]

    def count_by_gtfs_stop_id(self) -> dict[str, int]:
        """Count entrances per GTFS parent stop id."""

        counts: dict[str, int] = defaultdict(int)
        for entrance in self.entrances:
            if entrance.gtfs_stop_id:
                counts[entrance.gtfs_stop_id] += 1
        return dict(counts)

    def count_by_complex_id(self) -> dict[str, int]:
        """Count entrances per station complex id."""

        counts: dict[str, int] = defaultdict(int)
        for entrance in self.entrances:
            if entrance.complex_id:
                counts[entrance.complex_id] += 1
        return dict(counts)

    def for_station_id(self, station_id: str) -> tuple[Entrance, ...]:
        """Return entrances whose MTA station id matches."""

        return tuple(e for e in self.entrances if e.station_id == station_id)


@dataclass(frozen=True, slots=True)
class GtfsPathway:
    """One row from GTFS ``pathways.txt`` (GTFS-Pathways extension)."""

    pathway_id: str
    from_stop_id: str
    to_stop_id: str
    pathway_mode: str = ""
    is_bidirectional: str = ""
    length: str | None = None
    traversal_time: str | None = None
    stair_count: str | None = None
    max_slope: str | None = None
    min_width: str | None = None
    signposted_as: str | None = None


@dataclass(frozen=True, slots=True)
class GtfsLocation:
    """One row from GTFS ``locations.txt`` (GTFS-Pathways extension)."""

    location_id: str
    location_type: str = ""
    parent_station: str | None = None
    latitude: str | None = None
    longitude: str | None = None


@dataclass(frozen=True, slots=True)
class GtfsPathwaysSnapshot:
    """Optional pathways + locations parsed from a static GTFS zip."""

    pathways: tuple[GtfsPathway, ...]
    locations: tuple[GtfsLocation, ...]

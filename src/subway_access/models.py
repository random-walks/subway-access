"""Typed models for the real and planned ``subway-access`` API surface."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

AccessibilityLabel = Literal["accessible", "not_accessible", "unknown"]


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """Rolling time window used for reliability calculations."""

    days: int


@dataclass(frozen=True, slots=True)
class CatchmentRequest:
    """Request parameters for station catchment generation."""

    minutes: int
    mode: str = "walk"

    def __post_init__(self) -> None:
        """Validate the supported v0.1 request shape."""

        if self.minutes <= 0:
            message = "Catchment minutes must be greater than zero."
            raise ValueError(message)
        if self.mode != "walk":
            message = "Only walk catchments are implemented in subway-access v0.1."
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class AccessibilityQuery:
    """High-level filter for a borough or district analysis pass."""

    geography: str
    value: str


@dataclass(frozen=True, slots=True)
class ExportTarget:
    """Destination metadata for an eventual export command."""

    format: str
    output_path: Path


@dataclass(frozen=True, slots=True)
class Station:
    """Station record used by the first v0.1 analysis slice."""

    station_id: str
    name: str
    borough: str
    latitude: float
    longitude: float
    ada_status: AccessibilityLabel = "unknown"

    @property
    def is_accessible(self) -> bool:
        """Return whether the station counts as accessible in v0.1."""

        return self.ada_status == "accessible"


@dataclass(frozen=True, slots=True)
class AccessibilityStatus:
    """ADA accessibility status keyed by station identifier."""

    station_id: str
    ada_status: AccessibilityLabel


@dataclass(frozen=True, slots=True)
class TractDemographics:
    """Demographic summary for a tract centroid."""

    tract_id: str
    tract_name: str
    borough: str
    centroid_latitude: float
    centroid_longitude: float
    disability_rate: float
    senior_rate: float
    poverty_rate: float
    total_population: int


@dataclass(frozen=True, slots=True)
class CatchmentFeature:
    """Map-friendly catchment geometry for a station."""

    station_id: str
    station_name: str
    borough: str
    ada_status: AccessibilityLabel
    center_latitude: float
    center_longitude: float
    radius_meters: float
    minutes: int
    method: str
    polygon: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class TractAccessibilityRecord:
    """Joined tract-level accessibility score for the v0.1 workflow."""

    tract_id: str
    tract_name: str
    borough: str
    centroid_latitude: float
    centroid_longitude: float
    disability_rate: float
    senior_rate: float
    poverty_rate: float
    total_population: int
    need_score: float
    has_accessible_station: bool
    accessible_station_count: int
    covering_station_ids: tuple[str, ...]
    nearest_accessible_station_id: str | None
    nearest_accessible_station_name: str | None
    nearest_accessible_distance_meters: float | None


@dataclass(frozen=True, slots=True)
class GapRecord:
    """Final tract-level accessibility gap output."""

    tract_id: str
    tract_name: str
    borough: str
    disability_rate: float
    senior_rate: float
    poverty_rate: float
    total_population: int
    need_score: float
    has_accessible_station: bool
    accessible_station_count: int
    nearest_accessible_station_id: str | None
    nearest_accessible_station_name: str | None
    nearest_accessible_distance_meters: float | None
    gap_score: float
    gap_label: str


@dataclass(frozen=True, slots=True)
class StationDataset:
    """Loaded station rows for a v0.1 analysis run."""

    stations: tuple[Station, ...]

    def as_mapping(self) -> dict[str, Station]:
        """Return the dataset keyed by station identifier."""

        return {station.station_id: station for station in self.stations}

    @property
    def accessible_stations(self) -> tuple[Station, ...]:
        """Return only stations marked accessible."""

        return tuple(station for station in self.stations if station.is_accessible)

    def with_accessibility(self, accessibility: AccessibilityDataset) -> StationDataset:
        """Merge ADA status into the station dataset.

        Missing status rows become ``unknown``. Status rows referencing station
        identifiers which are not present in the station dataset raise a
        ``ValueError``.
        """

        status_by_station = accessibility.as_mapping()
        station_ids = {station.station_id for station in self.stations}
        unknown_ids = sorted(set(status_by_station).difference(station_ids))
        if unknown_ids:
            joined_ids = ", ".join(unknown_ids)
            message = f"Accessibility data references unknown station IDs: {joined_ids}."
            raise ValueError(message)

        merged = tuple(
            replace(
                station,
                ada_status=status_by_station.get(
                    station.station_id,
                    AccessibilityStatus(
                        station_id=station.station_id, ada_status="unknown"
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
        """Return the dataset keyed by station identifier."""

        return {status.station_id: status for status in self.statuses}


@dataclass(frozen=True, slots=True)
class DemographicDataset:
    """Loaded tract-level demographic rows."""

    tracts: tuple[TractDemographics, ...]


@dataclass(frozen=True, slots=True)
class CatchmentDataset:
    """Generated catchment geometries."""

    features: tuple[CatchmentFeature, ...]

    def radius_by_station_id(self) -> dict[str, float]:
        """Return catchment radius values keyed by station identifier."""

        return {
            feature.station_id: feature.radius_meters for feature in self.features
        }


@dataclass(frozen=True, slots=True)
class AccessibilityScoreDataset:
    """Joined tract accessibility scoring results."""

    records: tuple[TractAccessibilityRecord, ...]


@dataclass(frozen=True, slots=True)
class GapAnalysis:
    """Ranked tract accessibility gap results."""

    records: tuple[GapRecord, ...]

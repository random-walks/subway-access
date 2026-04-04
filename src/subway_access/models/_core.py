"""Typed models for the refactored ``subway-access`` package."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

AccessibilityLabel = Literal["accessible", "not_accessible", "unknown"]
EquipmentType = Literal["elevator", "escalator", "station", "platform", "unknown"]
OutageStatus = Literal["active", "resolved", "scheduled", "unknown"]


def _coerce_utc(value: datetime) -> datetime:
    """Return a timezone-aware UTC datetime for reliable window math."""

    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """Rolling time window used for reliability calculations."""

    days: int

    def __post_init__(self) -> None:
        if self.days <= 0:
            message = "TimeWindow.days must be greater than zero."
            raise ValueError(message)

    @property
    def total_minutes(self) -> int:
        """Return the total minutes in the window."""

        return self.days * 24 * 60


@dataclass(frozen=True, slots=True)
class CatchmentRequest:
    """Request parameters for station catchment generation."""

    minutes: int
    mode: str = "walk"

    def __post_init__(self) -> None:
        if self.minutes <= 0:
            message = "Catchment minutes must be greater than zero."
            raise ValueError(message)
        if self.mode != "walk":
            message = "Only walk catchments are implemented in subway-access."
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class AccessibilityQuery:
    """High-level filter for a borough or district analysis pass."""

    geography: str
    value: str


@dataclass(frozen=True, slots=True)
class ExportTarget:
    """Destination metadata for export commands."""

    format: str
    output_path: Path


@dataclass(frozen=True, slots=True)
class Station:
    """Station record used by the current accessibility workflow."""

    station_id: str
    name: str
    borough: str
    latitude: float
    longitude: float
    ada_status: AccessibilityLabel = "unknown"

    @property
    def is_accessible(self) -> bool:
        """Return whether the station counts as accessible in the current model."""

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
    """Joined tract-level accessibility score for the current workflow."""

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
class OutageRecord:
    """Single elevator or escalator outage event."""

    station_id: str
    equipment_id: str
    equipment_type: EquipmentType
    status: OutageStatus
    started_at: datetime
    ended_at: datetime | None
    description: str = ""
    source: str = ""

    def overlap_minutes(
        self, window: TimeWindow, *, as_of: datetime | None = None
    ) -> int:
        """Return outage minutes that fall inside the supplied rolling window."""

        window_end = _coerce_utc(as_of or self.ended_at or self.started_at)
        event_start = _coerce_utc(self.started_at)
        event_end = _coerce_utc(self.ended_at or window_end)
        window_start = window_end - timedelta(days=window.days)
        overlap_start = max(event_start, window_start)
        overlap_end = min(event_end, window_end)
        if overlap_end <= overlap_start:
            return 0
        return int((overlap_end - overlap_start).total_seconds() // 60)


@dataclass(frozen=True, slots=True)
class PedestrianConnection:
    """A simplified pedestrian connection between two stations or nodes."""

    connection_id: str
    from_station_id: str
    to_station_id: str
    walk_minutes: float
    distance_meters: float
    geometry: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True, slots=True)
class ReliabilityRecord:
    """Rolling reliability summary for a station."""

    station_id: str
    station_name: str | None
    borough: str | None
    ada_status: AccessibilityLabel
    outage_count: int
    outage_minutes: int
    window_days: int
    reliability_score: float
    reliability_label: str


@dataclass(frozen=True, slots=True)
class StationMetricRecord:
    """Station-level metrics derived from coverage and reliability outputs."""

    station_id: str
    station_name: str
    borough: str
    latitude: float
    longitude: float
    ada_status: AccessibilityLabel
    catchment_minutes: int
    catchment_radius_meters: float
    covered_tract_count: int
    covered_population: int
    nearby_gap_tract_count: int
    nearby_gap_population: int
    mean_need_score: float
    reliability_score: float | None
    reliability_label: str | None
    outage_minutes: int | None
    network_connection_count: int


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


@dataclass(frozen=True, slots=True)
class DemographicDataset:
    """Loaded tract-level demographic rows."""

    tracts: tuple[TractDemographics, ...]


@dataclass(frozen=True, slots=True)
class CatchmentDataset:
    """Generated catchment geometries."""

    features: tuple[CatchmentFeature, ...]

    def radius_by_station_id(self) -> dict[str, float]:
        return {feature.station_id: feature.radius_meters for feature in self.features}


@dataclass(frozen=True, slots=True)
class AccessibilityScoreDataset:
    """Joined tract accessibility scoring results."""

    records: tuple[TractAccessibilityRecord, ...]


@dataclass(frozen=True, slots=True)
class GapAnalysis:
    """Ranked tract accessibility gap results."""

    records: tuple[GapRecord, ...]


@dataclass(frozen=True, slots=True)
class OutageDataset:
    """Loaded outage events."""

    records: tuple[OutageRecord, ...]

    def outage_minutes_by_station(
        self, window: TimeWindow, *, as_of: datetime | None = None
    ) -> dict[str, int]:
        minutes_by_station: dict[str, int] = defaultdict(int)
        for record in self.records:
            minutes_by_station[record.station_id] += record.overlap_minutes(
                window,
                as_of=as_of,
            )
        return dict(minutes_by_station)

    def outage_count_by_station(
        self, window: TimeWindow, *, as_of: datetime | None = None
    ) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for record in self.records:
            if record.overlap_minutes(window, as_of=as_of) > 0:
                counts[record.station_id] += 1
        return dict(counts)

    def recommended_as_of(self) -> datetime | None:
        """Return the latest timestamp represented in the dataset."""

        timestamps = [
            _coerce_utc(timestamp)
            for record in self.records
            for timestamp in (record.started_at, record.ended_at)
            if timestamp is not None
        ]
        return max(timestamps) if timestamps else None


@dataclass(frozen=True, slots=True)
class PedestrianNetworkDataset:
    """Loaded pedestrian connections used for richer examples and metrics."""

    connections: tuple[PedestrianConnection, ...]

    def connection_count_by_station(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for connection in self.connections:
            counts[connection.from_station_id] += 1
            counts[connection.to_station_id] += 1
        return dict(counts)


@dataclass(frozen=True, slots=True)
class ReliabilityDataset:
    """Rolling reliability results for stations."""

    records: tuple[ReliabilityRecord, ...]

    def as_mapping(self) -> dict[str, ReliabilityRecord]:
        return {record.station_id: record for record in self.records}


@dataclass(frozen=True, slots=True)
class StationMetricDataset:
    """Export-ready station metrics."""

    records: tuple[StationMetricRecord, ...]

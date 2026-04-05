"""Typed models for the real-data ``subway-access`` package."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

AccessibilityLabel = Literal[
    "accessible",
    "partially_accessible",
    "not_accessible",
    "unknown",
]
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
    nearest_accessible_path_meters: float | None = None
    nearest_accessible_travel_minutes: float | None = None
    analysis_method: str = "euclidean"


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
    station_complex_id: str | None = None
    total_outages: int | None = None
    scheduled_outages: int | None = None
    unscheduled_outages: int | None = None
    availability_ratio: float | None = None
    outage_minutes_override: int | None = None

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
        if self.outage_minutes_override is not None:
            total_duration_minutes = max(
                int((event_end - event_start).total_seconds() // 60),
                1,
            )
            overlap_duration_minutes = int(
                (overlap_end - overlap_start).total_seconds() // 60
            )
            return int(
                self.outage_minutes_override
                * (overlap_duration_minutes / total_duration_minutes)
            )
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
    from_kind: str = "station"
    to_kind: str = "station"
    travel_mode: str = "walk"


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
    total_outages: int = 0
    scheduled_outages: int = 0
    unscheduled_outages: int = 0
    mean_availability_ratio: float | None = None


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
    daytime_routes: tuple[str, ...] = ()
    structure: str | None = None
    analysis_method: str = "euclidean"


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

    def outage_total_by_station(
        self,
        window: TimeWindow,
        *,
        as_of: datetime | None = None,
    ) -> dict[str, int]:
        totals: dict[str, int] = defaultdict(int)
        for record in self.records:
            if record.overlap_minutes(window, as_of=as_of) > 0 and record.total_outages:
                totals[record.station_id] += record.total_outages
        return dict(totals)

    def scheduled_outage_total_by_station(
        self,
        window: TimeWindow,
        *,
        as_of: datetime | None = None,
    ) -> dict[str, int]:
        totals: dict[str, int] = defaultdict(int)
        for record in self.records:
            if (
                record.overlap_minutes(window, as_of=as_of) > 0
                and record.scheduled_outages
            ):
                totals[record.station_id] += record.scheduled_outages
        return dict(totals)

    def unscheduled_outage_total_by_station(
        self,
        window: TimeWindow,
        *,
        as_of: datetime | None = None,
    ) -> dict[str, int]:
        totals: dict[str, int] = defaultdict(int)
        for record in self.records:
            if (
                record.overlap_minutes(window, as_of=as_of) > 0
                and record.unscheduled_outages
            ):
                totals[record.station_id] += record.unscheduled_outages
        return dict(totals)

    def mean_availability_ratio_by_station(
        self,
        window: TimeWindow,
        *,
        as_of: datetime | None = None,
    ) -> dict[str, float]:
        sums: dict[str, float] = defaultdict(float)
        counts: dict[str, int] = defaultdict(int)
        for record in self.records:
            if (
                record.overlap_minutes(window, as_of=as_of) > 0
                and record.availability_ratio is not None
            ):
                sums[record.station_id] += record.availability_ratio
                counts[record.station_id] += 1
        return {
            station_id: sums[station_id] / counts[station_id]
            for station_id in sums
            if counts[station_id] > 0
        }


@dataclass(frozen=True, slots=True)
class DataSourceMetadata:
    """Metadata describing one cached or fetched public dataset."""

    name: str
    source_url: str
    cache_path: Path
    refreshed_at: datetime
    record_count: int
    notes: str = ""


@dataclass(frozen=True, slots=True)
class NetworkGraphSnapshot:
    """Cached OSM walking graph metadata for one study area."""

    query: AccessibilityQuery
    graph_path: Path
    metadata_path: Path
    refreshed_at: datetime
    network_type: str
    node_count: int
    edge_count: int
    source_url: str
    buffer_meters: int


@dataclass(frozen=True, slots=True)
class AccessibilitySummaryRecord:
    """Rollup summary for accessibility metrics at a group level."""

    group_by: str
    group_value: str
    tract_count: int
    covered_tract_count: int
    uncovered_tract_count: int
    total_population: int
    covered_population: int
    uncovered_population: int
    mean_need_score: float
    mean_nearest_travel_minutes: float | None
    coverage_rate: float


@dataclass(frozen=True, slots=True)
class AccessibilitySummaryDataset:
    """Grouped rollup summaries for accessibility results."""

    records: tuple[AccessibilitySummaryRecord, ...]


@dataclass(frozen=True, slots=True)
class AccessibilityComparisonRecord:
    """Per-tract comparison between Euclidean and network accessibility models."""

    tract_id: str
    tract_name: str
    borough: str
    need_score: float
    euclidean_has_access: bool
    network_has_access: bool
    euclidean_station_count: int
    network_station_count: int
    euclidean_station_id: str | None
    network_station_id: str | None
    euclidean_travel_minutes: float | None
    network_travel_minutes: float | None
    euclidean_path_meters: float | None
    network_path_meters: float | None
    coverage_change_label: str


@dataclass(frozen=True, slots=True)
class AccessibilityComparisonDataset:
    """Collection of tract-level Euclidean vs network comparison results."""

    records: tuple[AccessibilityComparisonRecord, ...]


@dataclass(frozen=True, slots=True)
class PedestrianNetworkDataset:
    """Loaded pedestrian connections used for richer examples and metrics."""

    connections: tuple[PedestrianConnection, ...]
    source: str = ""

    def connection_count_by_station(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for connection in self.connections:
            if connection.from_kind == "station":
                counts[connection.from_station_id] += 1
            if connection.to_kind == "station":
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


@dataclass(frozen=True, slots=True)
class StudyAreaSnapshot:
    """In-memory snapshot of one real-data accessibility study area."""

    query: AccessibilityQuery
    stations: StationDataset
    accessibility: AccessibilityDataset
    demographics: DemographicDataset
    outages: OutageDataset
    metadata: tuple[DataSourceMetadata, ...]
    entrances: EntranceDataset
    gtfs_pathways: GtfsPathwaysSnapshot | None = None
    pedestrian_network: PedestrianNetworkDataset | None = None
    generated_at: datetime | None = None
    cache_dir: Path | None = None

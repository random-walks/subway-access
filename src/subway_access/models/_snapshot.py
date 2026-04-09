"""Snapshot, query, and summary models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from ._common import AccessibilityQuery
    from ._entrance import EntranceDataset, GtfsPathwaysSnapshot
    from ._network import PedestrianNetworkDataset
    from ._outage import OutageDataset
    from ._station import AccessibilityDataset, StationDataset
    from ._tract import DemographicDataset


@dataclass(frozen=True, slots=True)
class ExportTarget:
    """Destination metadata for export commands."""

    format: str
    output_path: Path


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

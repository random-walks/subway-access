"""Tract-level demographic and accessibility score models."""

from __future__ import annotations

from dataclasses import dataclass


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
class DemographicDataset:
    """Loaded tract-level demographic rows."""

    tracts: tuple[TractDemographics, ...]


@dataclass(frozen=True, slots=True)
class AccessibilityScoreDataset:
    """Joined tract accessibility scoring results."""

    records: tuple[TractAccessibilityRecord, ...]

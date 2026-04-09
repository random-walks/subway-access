"""Catchment and station metric models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._common import AccessibilityLabel


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
class CatchmentDataset:
    """Generated catchment geometries."""

    features: tuple[CatchmentFeature, ...]

    def radius_by_station_id(self) -> dict[str, float]:
        return {feature.station_id: feature.radius_meters for feature in self.features}


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
class StationMetricDataset:
    """Export-ready station metrics."""

    records: tuple[StationMetricRecord, ...]

"""Gap analysis models."""

from __future__ import annotations

from dataclasses import dataclass


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
class GapAnalysis:
    """Ranked tract accessibility gap results."""

    records: tuple[GapRecord, ...]

"""Processing steps for the real v0.1 subway accessibility workflow."""

from __future__ import annotations

from statistics import fmean

from ._geo import approximate_circle_polygon, haversine_distance_meters, walk_radius_meters
from ._not_implemented import planned_surface
from .models import (
    AccessibilityScoreDataset,
    CatchmentDataset,
    CatchmentFeature,
    CatchmentRequest,
    DemographicDataset,
    GapAnalysis,
    GapRecord,
    StationDataset,
    TimeWindow,
    TractAccessibilityRecord,
)

WALKING_SPEED_METERS_PER_MINUTE = 80.0


def generate_catchments(
    station_data: StationDataset, request: CatchmentRequest
) -> CatchmentDataset:
    """Generate first-pass Euclidean catchments for a walk threshold."""

    if request.minutes <= 0:
        raise ValueError("Catchment minutes must be greater than zero.")
    if request.mode != "walk":
        raise ValueError("Only walk catchments are implemented in v0.1.")

    radius_meters = walk_radius_meters(request.minutes)
    features = tuple(
        CatchmentFeature(
            station_id=station.station_id,
            station_name=station.name,
            borough=station.borough,
            ada_status=station.ada_status,
            center_latitude=station.latitude,
            center_longitude=station.longitude,
            radius_meters=radius_meters,
            minutes=request.minutes,
            method="euclidean-buffer-v0.1",
            polygon=approximate_circle_polygon(
                latitude=station.latitude,
                longitude=station.longitude,
                radius_meters=radius_meters,
            ),
        )
        for station in station_data.stations
    )
    return CatchmentDataset(features=features)


def compute_reliability(
    accessibility_data: object, outage_data: object, window: TimeWindow
) -> object:
    """Compute accessibility reliability over a rolling outage window."""
    del accessibility_data, outage_data, window
    planned_surface("compute_reliability()")


def score_accessibility(
    station_data: StationDataset,
    catchments: CatchmentDataset,
    demographics: DemographicDataset,
) -> AccessibilityScoreDataset:
    """Score tract accessibility using station, catchment, and demographic inputs."""

    radius_by_station_id = catchments.radius_by_station_id()
    station_name_by_id = {
        station.station_id: station.name for station in station_data.accessible_stations
    }
    accessible_stations = station_data.accessible_stations

    records: list[TractAccessibilityRecord] = []
    for tract in demographics.tracts:
        covering_station_ids: list[str] = []
        nearest_station_id: str | None = None
        nearest_station_name: str | None = None
        nearest_distance: float | None = None

        for station in accessible_stations:
            distance = haversine_distance_meters(
                latitude_a=tract.centroid_latitude,
                longitude_a=tract.centroid_longitude,
                latitude_b=station.latitude,
                longitude_b=station.longitude,
            )
            if nearest_distance is None or distance < nearest_distance:
                nearest_distance = distance
                nearest_station_id = station.station_id
                nearest_station_name = station.name

            radius = radius_by_station_id[station.station_id]
            if distance <= radius:
                covering_station_ids.append(station.station_id)

        need_score = fmean((tract.disability_rate, tract.senior_rate, tract.poverty_rate))
        records.append(
            TractAccessibilityRecord(
                tract_id=tract.tract_id,
                tract_name=tract.tract_name,
                borough=tract.borough,
                centroid_latitude=tract.centroid_latitude,
                centroid_longitude=tract.centroid_longitude,
                disability_rate=tract.disability_rate,
                senior_rate=tract.senior_rate,
                poverty_rate=tract.poverty_rate,
                total_population=tract.total_population,
                need_score=need_score,
                has_accessible_station=bool(covering_station_ids),
                accessible_station_count=len(covering_station_ids),
                covering_station_ids=tuple(covering_station_ids),
                nearest_accessible_station_id=nearest_station_id,
                nearest_accessible_station_name=nearest_station_name,
                nearest_accessible_distance_meters=nearest_distance,
            )
        )

    return AccessibilityScoreDataset(records=tuple(records))


def analyze_gaps(scored_data: AccessibilityScoreDataset) -> GapAnalysis:
    """Identify tracts with high need and weak accessible station coverage."""

    records = tuple(
        sorted(
            (
                GapRecord(
                    tract_id=record.tract_id,
                    tract_name=record.tract_name,
                    borough=record.borough,
                    disability_rate=record.disability_rate,
                    senior_rate=record.senior_rate,
                    poverty_rate=record.poverty_rate,
                    total_population=record.total_population,
                    need_score=record.need_score,
                    has_accessible_station=record.has_accessible_station,
                    accessible_station_count=record.accessible_station_count,
                    nearest_accessible_station_id=record.nearest_accessible_station_id,
                    nearest_accessible_station_name=record.nearest_accessible_station_name,
                    nearest_accessible_distance_meters=record.nearest_accessible_distance_meters,
                    gap_score=0.0 if record.has_accessible_station else record.need_score,
                    gap_label="covered" if record.has_accessible_station else "gap",
                )
                for record in scored_data.records
            ),
            key=lambda record: (-record.gap_score, record.tract_id),
        )
    )
    return GapAnalysis(records=records)

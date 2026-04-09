"""Compatibility bridge between the factor pipeline and the functional API.

These helpers let ``analysis._core`` functions internally delegate to the
factor system while preserving their exact return types and signatures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..analysis._geo import haversine_distance_meters
from ._base import FactorContext, Pipeline
from ._builtin import (
    CoverageFactor,
    NearestStationDistanceFactor,
    NeedScoreFactor,
    StationCountFactor,
)

if TYPE_CHECKING:
    from ..models import (
        CatchmentDataset,
        DemographicDataset,
        StationDataset,
        TractAccessibilityRecord,
    )

_METERS_PER_MINUTE = 80.0


def score_tracts_via_factors(
    station_data: StationDataset,
    catchments: CatchmentDataset,
    demographics: DemographicDataset,
) -> tuple[TractAccessibilityRecord, ...]:
    """Run the default factor pipeline and convert results to TractAccessibilityRecords.

    This bridges the new factor system with the existing functional API,
    preserving the exact return type of ``score_accessibility``.
    """

    from ..models import TractAccessibilityRecord

    pipe = (
        Pipeline()
        .add(NeedScoreFactor())
        .add(CoverageFactor())
        .add(StationCountFactor())
        .add(NearestStationDistanceFactor())
    )

    accessible_stations = station_data.accessible_stations
    radius_map = catchments.radius_by_station_id()

    contexts = [
        FactorContext(
            tract=tract,
            stations=station_data,
            catchments=catchments,
        )
        for tract in demographics.tracts
    ]

    result = pipe.run(contexts)

    records: list[TractAccessibilityRecord] = []
    for i, tract in enumerate(demographics.tracts):
        # Get factor results for this tract.
        need_score = result.columns["need_score"][i]
        has_accessible = result.columns["has_accessible_station"][i]
        station_count = result.columns["accessible_station_count"][i]

        # Compute covering station IDs (not a factor, needs full enumeration).
        covering_ids: list[str] = []
        nearest_id: str | None = None
        nearest_name: str | None = None
        best_distance: float | None = None

        for station in accessible_stations:
            distance = haversine_distance_meters(
                latitude_a=tract.centroid_latitude,
                longitude_a=tract.centroid_longitude,
                latitude_b=station.latitude,
                longitude_b=station.longitude,
            )
            if best_distance is None or distance < best_distance:
                best_distance = distance
                nearest_id = station.station_id
                nearest_name = station.name

            if distance <= radius_map.get(station.station_id, 0.0):
                covering_ids.append(station.station_id)

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
                has_accessible_station=has_accessible,
                accessible_station_count=station_count,
                covering_station_ids=tuple(covering_ids),
                nearest_accessible_station_id=nearest_id,
                nearest_accessible_station_name=nearest_name,
                nearest_accessible_distance_meters=best_distance,
                nearest_accessible_path_meters=best_distance,
                nearest_accessible_travel_minutes=None
                if best_distance is None
                else best_distance / _METERS_PER_MINUTE,
                analysis_method="euclidean",
            )
        )

    return tuple(records)

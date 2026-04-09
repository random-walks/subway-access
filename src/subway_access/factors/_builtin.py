"""Built-in literature-backed factors for the accessibility pipeline."""

from __future__ import annotations

from statistics import fmean
from typing import TYPE_CHECKING

from ..analysis._geo import haversine_distance_meters
from ._base import Factor

if TYPE_CHECKING:
    from ._base import FactorContext

_METERS_PER_MINUTE = 80.0


class NeedScoreFactor(Factor):
    """Composite need score from demographic vulnerability indicators.

    By default, computes the unweighted mean of disability_rate,
    senior_rate, and poverty_rate.  Pass ``weights`` to override.

    Args:
        weights: Optional mapping of indicator name to weight.
            Keys must be a subset of ``{"disability", "senior", "poverty"}``.
            Weights are normalized to sum to 1.0.

    Example:
        >>> factor = NeedScoreFactor()
        >>> factor.compute(ctx)
        0.15
        >>> weighted = NeedScoreFactor(weights={"disability": 0.5, "senior": 0.3, "poverty": 0.2})
    """

    name = "need_score"
    dtype = "float"

    _VALID_KEYS = frozenset({"disability", "senior", "poverty"})

    def __init__(
        self,
        weights: dict[str, float] | None = None,
    ) -> None:
        if weights is not None:
            invalid = set(weights) - self._VALID_KEYS
            if invalid:
                message = f"Invalid weight keys: {sorted(invalid)}"
                raise ValueError(message)
            total = sum(weights.values())
            self._weights: dict[str, float] | None = {
                k: v / total for k, v in weights.items()
            }
        else:
            self._weights = None

    def compute(self, context: FactorContext) -> float:
        tract = context.tract
        if self._weights is None:
            return fmean((tract.disability_rate, tract.senior_rate, tract.poverty_rate))
        result = 0.0
        rates = {
            "disability": tract.disability_rate,
            "senior": tract.senior_rate,
            "poverty": tract.poverty_rate,
        }
        for key, weight in self._weights.items():
            result += rates[key] * weight
        return result


class CoverageFactor(Factor):
    """Whether a tract is covered by at least one accessible station's catchment.

    Example:
        >>> CoverageFactor().compute(ctx)
        True
    """

    name = "has_accessible_station"
    dtype = "bool"

    def compute(self, context: FactorContext) -> bool:
        radius_map = context.catchments.radius_by_station_id()
        for station in context.stations.accessible_stations:
            distance = haversine_distance_meters(
                latitude_a=context.tract.centroid_latitude,
                longitude_a=context.tract.centroid_longitude,
                latitude_b=station.latitude,
                longitude_b=station.longitude,
            )
            if distance <= radius_map.get(station.station_id, 0.0):
                return True
        return False


class GapScoreFactor(Factor):
    """Gap score: 0.0 if covered, need_score otherwise.

    Depends on coverage and need score computations.
    Uses a ``NeedScoreFactor`` and ``CoverageFactor`` internally.

    Args:
        need_weights: Optional weights forwarded to the internal NeedScoreFactor.

    Example:
        >>> GapScoreFactor().compute(ctx)
        0.0
    """

    name = "gap_score"
    dtype = "float"

    def __init__(self, need_weights: dict[str, float] | None = None) -> None:
        self._need = NeedScoreFactor(weights=need_weights)
        self._coverage = CoverageFactor()

    def compute(self, context: FactorContext) -> float:
        if self._coverage.compute(context):
            return 0.0
        return self._need.compute(context)


class NearestStationDistanceFactor(Factor):
    """Haversine distance in meters to the nearest accessible station.

    Returns -1.0 if no accessible stations exist.

    Example:
        >>> NearestStationDistanceFactor().compute(ctx)
        423.7
    """

    name = "nearest_accessible_distance_meters"
    dtype = "float"

    def compute(self, context: FactorContext) -> float:
        nearest: float | None = None
        for station in context.stations.accessible_stations:
            distance = haversine_distance_meters(
                latitude_a=context.tract.centroid_latitude,
                longitude_a=context.tract.centroid_longitude,
                latitude_b=station.latitude,
                longitude_b=station.longitude,
            )
            if nearest is None or distance < nearest:
                nearest = distance
        return nearest if nearest is not None else -1.0


class NearestStationTravelMinutesFactor(Factor):
    """Estimated walking time in minutes to the nearest accessible station.

    Uses a fixed walking speed of 80 m/min.  Returns -1.0 if no accessible
    stations exist.

    Example:
        >>> NearestStationTravelMinutesFactor().compute(ctx)
        5.3
    """

    name = "nearest_accessible_travel_minutes"
    dtype = "float"

    def compute(self, context: FactorContext) -> float:
        distance = NearestStationDistanceFactor().compute(context)
        if distance < 0:
            return -1.0
        return distance / _METERS_PER_MINUTE


class StationCountFactor(Factor):
    """Number of accessible stations whose catchment covers this tract.

    Example:
        >>> StationCountFactor().compute(ctx)
        2
    """

    name = "accessible_station_count"
    dtype = "int"

    def compute(self, context: FactorContext) -> int:
        radius_map = context.catchments.radius_by_station_id()
        count = 0
        for station in context.stations.accessible_stations:
            distance = haversine_distance_meters(
                latitude_a=context.tract.centroid_latitude,
                longitude_a=context.tract.centroid_longitude,
                latitude_b=station.latitude,
                longitude_b=station.longitude,
            )
            if distance <= radius_map.get(station.station_id, 0.0):
                count += 1
        return count


class ReliabilityWeightedCoverageFactor(Factor):
    """Coverage weighted by the best-covering station's reliability score.

    Returns the highest reliability score among accessible stations whose
    catchment covers this tract, or 0.0 if the tract is uncovered.

    Args:
        reliability_scores: Mapping of station_id to reliability score (0-1).

    Example:
        >>> scores = {"station_1": 0.99, "station_2": 0.85}
        >>> ReliabilityWeightedCoverageFactor(scores).compute(ctx)
        0.99
    """

    name = "reliability_weighted_coverage"
    dtype = "float"

    def __init__(self, reliability_scores: dict[str, float]) -> None:
        self._scores = reliability_scores

    def compute(self, context: FactorContext) -> float:
        radius_map = context.catchments.radius_by_station_id()
        best_score = 0.0
        for station in context.stations.accessible_stations:
            distance = haversine_distance_meters(
                latitude_a=context.tract.centroid_latitude,
                longitude_a=context.tract.centroid_longitude,
                latitude_b=station.latitude,
                longitude_b=station.longitude,
            )
            if distance <= radius_map.get(station.station_id, 0.0):
                score = self._scores.get(station.station_id, 0.0)
                best_score = max(best_score, score)
        return best_score

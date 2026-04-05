"""Network-based accessibility helpers for ``subway-access``."""

from __future__ import annotations

import importlib
from statistics import fmean
from typing import Any

from shapely.geometry import MultiPoint

from ..models import (
    AccessibilityComparisonDataset,
    AccessibilityComparisonRecord,
    AccessibilityScoreDataset,
    CatchmentDataset,
    CatchmentFeature,
    CatchmentRequest,
    DemographicDataset,
    StationDataset,
    TractAccessibilityRecord,
)
from ._geo import build_circle_polygon

nx_module: Any = None
ox_module: Any = None

try:  # pragma: no cover - dependency guard
    nx_module = importlib.import_module("networkx")
    ox_module = importlib.import_module("osmnx")
except ImportError:  # pragma: no cover - dependency guard
    nx_module = None
    ox_module = None

_METERS_PER_MINUTE = 80.0


def _require_network_stack() -> tuple[Any, Any]:
    if nx_module is None or ox_module is None:  # pragma: no cover - dependency guard
        message = (
            "Network accessibility support requires `subway-access[network]` or "
            "`pip install osmnx scikit-learn`."
        )
        raise ImportError(message)
    return nx_module, ox_module


def _station_nodes(
    graph: Any,
    station_data: StationDataset,
) -> dict[str, int]:
    _, ox = _require_network_stack()
    return {
        station.station_id: int(
            ox.distance.nearest_nodes(
                graph,
                X=station.longitude,
                Y=station.latitude,
            )
        )
        for station in station_data.stations
    }


def _node_coordinates(graph: Any, nodes: list[int]) -> list[tuple[float, float]]:
    coordinates = []
    for node in nodes:
        node_data = graph.nodes[node]
        if "x" in node_data and "y" in node_data:
            coordinates.append((float(node_data["x"]), float(node_data["y"])))
    return coordinates


def generate_network_isochrones(
    station_data: StationDataset,
    graph: Any,
    request: CatchmentRequest,
) -> CatchmentDataset:
    """Generate walking-network catchments from a cached OSM graph."""

    nx, _ = _require_network_stack()
    radius_meters = request.minutes * _METERS_PER_MINUTE
    station_nodes = _station_nodes(graph, station_data)
    features = []

    for station in station_data.stations:
        station_node = station_nodes[station.station_id]
        reachable = nx.ego_graph(
            graph,
            station_node,
            radius=radius_meters,
            distance="length",
        )
        coordinates = _node_coordinates(graph, list(reachable.nodes))
        if len(coordinates) >= 3:
            hull = MultiPoint(coordinates).convex_hull
            if hull.geom_type == "Polygon":
                polygon = tuple(
                    (float(lon), float(lat)) for lon, lat in hull.exterior.coords
                )
            else:
                polygon = build_circle_polygon(
                    latitude=station.latitude,
                    longitude=station.longitude,
                    radius_meters=radius_meters,
                )
        else:
            polygon = build_circle_polygon(
                latitude=station.latitude,
                longitude=station.longitude,
                radius_meters=radius_meters,
            )
        features.append(
            CatchmentFeature(
                station_id=station.station_id,
                station_name=station.name,
                borough=station.borough,
                ada_status=station.ada_status,
                center_latitude=station.latitude,
                center_longitude=station.longitude,
                radius_meters=radius_meters,
                minutes=request.minutes,
                method="walk-network-convex-hull-v0.3",
                polygon=polygon,
            )
        )
    return CatchmentDataset(features=tuple(features))


def score_accessibility_network(
    station_data: StationDataset,
    graph: Any,
    demographics: DemographicDataset,
    request: CatchmentRequest,
) -> AccessibilityScoreDataset:
    """Score tract accessibility using walking-network travel rather than circles."""

    nx, ox = _require_network_stack()
    threshold_meters = request.minutes * _METERS_PER_MINUTE
    accessible_stations = station_data.accessible_stations
    station_nodes = _station_nodes(graph, StationDataset(accessible_stations))

    records: list[TractAccessibilityRecord] = []
    for tract in demographics.tracts:
        tract_node = int(
            ox.distance.nearest_nodes(
                graph,
                X=tract.centroid_longitude,
                Y=tract.centroid_latitude,
            )
        )
        covering_station_ids: list[str] = []
        nearest_station_id: str | None = None
        nearest_station_name: str | None = None
        nearest_distance: float | None = None
        nearest_minutes: float | None = None

        for station in accessible_stations:
            try:
                path_meters = float(
                    nx.shortest_path_length(
                        graph,
                        tract_node,
                        station_nodes[station.station_id],
                        weight="length",
                    )
                )
            except (nx.NetworkXNoPath, KeyError):
                continue
            if nearest_distance is None or path_meters < nearest_distance:
                nearest_distance = path_meters
                nearest_minutes = path_meters / _METERS_PER_MINUTE
                nearest_station_id = station.station_id
                nearest_station_name = station.name
            if path_meters <= threshold_meters:
                covering_station_ids.append(station.station_id)

        need_score = fmean(
            (tract.disability_rate, tract.senior_rate, tract.poverty_rate)
        )
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
                nearest_accessible_path_meters=nearest_distance,
                nearest_accessible_travel_minutes=nearest_minutes,
                analysis_method="network-isochrone",
            )
        )

    return AccessibilityScoreDataset(records=tuple(records))


def _coverage_change_label(
    *,
    euclidean_has_access: bool,
    network_has_access: bool,
) -> str:
    if euclidean_has_access and network_has_access:
        return "both_covered"
    if euclidean_has_access and not network_has_access:
        return "euclidean_only"
    if not euclidean_has_access and network_has_access:
        return "network_only"
    return "both_uncovered"


def compare_accessibility_models(
    euclidean_scores: AccessibilityScoreDataset,
    network_scores: AccessibilityScoreDataset,
) -> AccessibilityComparisonDataset:
    """Compare tract accessibility results between Euclidean and network models."""

    euclidean_by_tract = {
        record.tract_id: record for record in euclidean_scores.records
    }
    network_by_tract = {record.tract_id: record for record in network_scores.records}
    tract_ids = sorted(set(euclidean_by_tract) | set(network_by_tract))
    records = []
    for tract_id in tract_ids:
        euclidean = euclidean_by_tract[tract_id]
        network = network_by_tract[tract_id]
        records.append(
            AccessibilityComparisonRecord(
                tract_id=tract_id,
                tract_name=euclidean.tract_name,
                borough=euclidean.borough,
                need_score=euclidean.need_score,
                euclidean_has_access=euclidean.has_accessible_station,
                network_has_access=network.has_accessible_station,
                euclidean_station_count=euclidean.accessible_station_count,
                network_station_count=network.accessible_station_count,
                euclidean_station_id=euclidean.nearest_accessible_station_id,
                network_station_id=network.nearest_accessible_station_id,
                euclidean_travel_minutes=euclidean.nearest_accessible_travel_minutes,
                network_travel_minutes=network.nearest_accessible_travel_minutes,
                euclidean_path_meters=euclidean.nearest_accessible_path_meters,
                network_path_meters=network.nearest_accessible_path_meters,
                coverage_change_label=_coverage_change_label(
                    euclidean_has_access=euclidean.has_accessible_station,
                    network_has_access=network.has_accessible_station,
                ),
            )
        )
    return AccessibilityComparisonDataset(records=tuple(records))

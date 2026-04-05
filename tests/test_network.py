from __future__ import annotations

import os
from pathlib import Path

import networkx as nx
import pytest
from shapely.geometry import Polygon

from subway_access import analysis, models, pipeline
from subway_access.io import _osm


def _build_graph() -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    graph.graph["crs"] = "EPSG:4326"
    graph.add_node(1, x=-74.0000, y=40.7000)
    graph.add_node(2, x=-73.9990, y=40.7000)
    graph.add_node(3, x=-73.9990, y=40.7010)
    graph.add_node(4, x=-74.0000, y=40.7010)
    for start, end, length in (
        (1, 2, 100.0),
        (2, 3, 100.0),
        (3, 4, 100.0),
        (4, 1, 100.0),
        (2, 1, 100.0),
        (3, 2, 100.0),
        (4, 3, 100.0),
        (1, 4, 100.0),
    ):
        graph.add_edge(start, end, length=length)
    return graph


def _stations() -> models.StationDataset:
    return models.StationDataset(
        stations=(
            models.Station(
                station_id="A",
                name="Accessible Station",
                borough="Manhattan",
                latitude=40.7000,
                longitude=-74.0000,
                ada_status="accessible",
            ),
            models.Station(
                station_id="B",
                name="Inaccessible Station",
                borough="Manhattan",
                latitude=40.7010,
                longitude=-74.0000,
                ada_status="not_accessible",
            ),
        )
    )


def _demographics() -> models.DemographicDataset:
    return models.DemographicDataset(
        tracts=(
            models.TractDemographics(
                tract_id="T1",
                tract_name="Tract One",
                borough="Manhattan",
                centroid_latitude=40.7010,
                centroid_longitude=-73.9990,
                disability_rate=0.10,
                senior_rate=0.10,
                poverty_rate=0.10,
                total_population=1000,
            ),
        )
    )


def test_network_accessibility_can_disagree_with_euclidean_baseline() -> None:
    graph = _build_graph()
    stations = _stations()
    demographics = _demographics()
    request = models.CatchmentRequest(minutes=2)

    euclidean_scores = analysis.score_accessibility(
        stations,
        analysis.generate_catchments(stations, request),
        demographics,
    )
    network_scores = analysis.score_accessibility_network(
        stations,
        graph,
        demographics,
        request,
    )
    comparison = analysis.compare_accessibility_models(
        euclidean_scores,
        network_scores,
    )

    assert euclidean_scores.records[0].has_accessible_station is True
    assert network_scores.records[0].has_accessible_station is False
    assert comparison.records[0].coverage_change_label == "euclidean_only"


def test_network_isochrones_return_network_method() -> None:
    graph = _build_graph()
    catchments = analysis.generate_network_isochrones(
        _stations(),
        graph,
        models.CatchmentRequest(minutes=5),
    )

    assert len(catchments.features) == 2
    assert catchments.features[0].method == "walk-network-convex-hull-v0.3"


def test_summarize_accessibility_by_group_rolls_up_scores() -> None:
    scores = analysis.score_accessibility(
        _stations(),
        analysis.generate_catchments(_stations(), models.CatchmentRequest(minutes=1)),
        _demographics(),
    )

    summary = analysis.summarize_accessibility_by_group(scores)

    assert len(summary.records) == 1
    assert summary.records[0].group_value == "Manhattan"


def test_fetch_walk_graph_writes_cache_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = _build_graph()

    class FakeOsmnx:
        """Minimal stand-in for the OSMnx graph I/O surface."""

        @staticmethod
        def graph_from_polygon(*_args, **_kwargs):
            return graph

        @staticmethod
        def save_graphml(graph_to_save, graph_path):
            nx.write_graphml(graph_to_save, graph_path)

        @staticmethod
        def load_graphml(graph_path):
            return nx.read_graphml(graph_path)

    monkeypatch.setattr(_osm, "_require_osm_stack", lambda: (FakeOsmnx, nx))
    monkeypatch.setattr(
        _osm,
        "_selected_polygon",
        lambda _query, **_kwargs: Polygon(
            [
                (-74.001, 40.699),
                (-73.998, 40.699),
                (-73.998, 40.702),
                (-74.001, 40.702),
            ]
        ),
    )

    snapshot = _osm.fetch_walk_graph(
        models.AccessibilityQuery(geography="borough", value="Manhattan"),
        cache_dir=tmp_path,
        refresh=True,
    )
    loaded_graph, loaded_snapshot = _osm.load_cached_walk_graph(tmp_path)

    assert snapshot.node_count == 4
    assert snapshot.edge_count == 8
    assert snapshot.graph_path.exists()
    assert loaded_snapshot.query.value == "Manhattan"
    assert loaded_graph.number_of_nodes() == 4


@pytest.mark.skipif(
    os.getenv("SUBWAY_ACCESS_RUN_LIVE") != "1",
    reason="live walk graph fetch is skipped unless SUBWAY_ACCESS_RUN_LIVE=1",
)
def test_fetch_walk_graph_live(tmp_path: Path) -> None:
    snapshot = pipeline.fetch_walk_graph(
        models.AccessibilityQuery(geography="community_district", value="Manhattan 03"),
        cache_dir=tmp_path,
        refresh=True,
        buffer_meters=100,
    )
    graph, loaded_snapshot = pipeline.load_cached_walk_graph(tmp_path)

    assert snapshot.node_count > 0
    assert loaded_snapshot.edge_count > 0
    assert graph.number_of_nodes() > 0

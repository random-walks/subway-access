"""OpenStreetMap walking-graph cache helpers for ``subway-access``."""

from __future__ import annotations

import importlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from nyc_geo_toolkit import load_nyc_boundaries
from shapely.geometry import shape
from shapely.ops import unary_union

from ..models import AccessibilityQuery, NetworkGraphSnapshot
from ._cache import cache_timestamp, ensure_directory, write_json

nx_module: Any = None
ox_module: Any = None

try:  # pragma: no cover - dependency guard
    nx_module = importlib.import_module("networkx")
    ox_module = importlib.import_module("osmnx")
except ImportError:  # pragma: no cover - dependency guard
    nx_module = None
    ox_module = None

OSM_SOURCE_URL = "https://www.openstreetmap.org"


def _require_osm_stack() -> tuple[Any, Any]:
    if nx_module is None or ox_module is None:  # pragma: no cover - dependency guard
        message = (
            "OSM network support requires `subway-access[network]` or "
            "`pip install osmnx scikit-learn`."
        )
        raise ImportError(message)
    return ox_module, nx_module


def _graph_paths(cache_dir: Path) -> tuple[Path, Path]:
    return (cache_dir / "walk.graphml", cache_dir / "walk-graph-metadata.json")


def _buffer_polygon_degrees(polygon: Any, *, buffer_meters: int) -> Any:
    if buffer_meters <= 0:
        return polygon
    return polygon.buffer(buffer_meters / 111_320.0)


def _selected_polygon(query: AccessibilityQuery, *, buffer_meters: int) -> Any:
    boundaries = load_nyc_boundaries(query.geography, values=query.value)
    polygon = unary_union([shape(feature.geometry) for feature in boundaries.features])
    return _buffer_polygon_degrees(polygon, buffer_meters=buffer_meters)


def _snapshot_payload(snapshot: NetworkGraphSnapshot) -> dict[str, object]:
    return {
        "query": {
            "geography": snapshot.query.geography,
            "value": snapshot.query.value,
        },
        "graph_path": str(snapshot.graph_path),
        "metadata_path": str(snapshot.metadata_path),
        "refreshed_at": snapshot.refreshed_at.isoformat(),
        "network_type": snapshot.network_type,
        "node_count": snapshot.node_count,
        "edge_count": snapshot.edge_count,
        "source_url": snapshot.source_url,
        "buffer_meters": snapshot.buffer_meters,
    }


def fetch_walk_graph(
    query: AccessibilityQuery,
    *,
    cache_dir: str | Path,
    refresh: bool = False,
    network_type: str = "walk",
    buffer_meters: int = 0,
) -> NetworkGraphSnapshot:
    """Fetch and cache an OSM walking graph for the selected study area."""

    ox, _ = _require_osm_stack()
    cache_root = ensure_directory(Path(cache_dir).expanduser().resolve())
    graph_path, metadata_path = _graph_paths(cache_root)
    if graph_path.exists() and metadata_path.exists() and not refresh:
        return load_cached_walk_graph(cache_root)[1]

    polygon = _selected_polygon(query, buffer_meters=buffer_meters)
    graph = ox.graph_from_polygon(polygon, network_type=network_type, simplify=True)
    ox.save_graphml(graph, graph_path)
    snapshot = NetworkGraphSnapshot(
        query=query,
        graph_path=graph_path,
        metadata_path=metadata_path,
        refreshed_at=datetime.fromisoformat(cache_timestamp()),
        network_type=network_type,
        node_count=graph.number_of_nodes(),
        edge_count=graph.number_of_edges(),
        source_url=OSM_SOURCE_URL,
        buffer_meters=buffer_meters,
    )
    write_json(metadata_path, _snapshot_payload(snapshot))
    return snapshot


def load_cached_walk_graph(
    cache_dir: str | Path,
) -> tuple[Any, NetworkGraphSnapshot]:
    """Load a previously cached OSM walking graph and its metadata."""

    ox, _ = _require_osm_stack()
    cache_root = Path(cache_dir).expanduser().resolve()
    graph_path, metadata_path = _graph_paths(cache_root)
    if not graph_path.exists() or not metadata_path.exists():
        message = (
            f"Missing cached walk graph in {cache_root}. "
            "Run fetch_walk_graph() first."
        )
        raise FileNotFoundError(message)
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    graph = ox.load_graphml(graph_path)
    snapshot = NetworkGraphSnapshot(
        query=AccessibilityQuery(
            geography=payload["query"]["geography"],
            value=payload["query"]["value"],
        ),
        graph_path=graph_path,
        metadata_path=metadata_path,
        refreshed_at=datetime.fromisoformat(payload["refreshed_at"]),
        network_type=str(payload["network_type"]),
        node_count=int(payload["node_count"]),
        edge_count=int(payload["edge_count"]),
        source_url=str(payload["source_url"]),
        buffer_meters=int(payload["buffer_meters"]),
    )
    return graph, snapshot

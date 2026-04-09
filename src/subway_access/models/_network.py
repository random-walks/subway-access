"""Network, pedestrian connection, and model comparison models."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from ._common import AccessibilityQuery


@dataclass(frozen=True, slots=True)
class PedestrianConnection:
    """A simplified pedestrian connection between two stations or nodes."""

    connection_id: str
    from_station_id: str
    to_station_id: str
    walk_minutes: float
    distance_meters: float
    geometry: tuple[tuple[float, float], ...] = ()
    from_kind: str = "station"
    to_kind: str = "station"
    travel_mode: str = "walk"


@dataclass(frozen=True, slots=True)
class PedestrianNetworkDataset:
    """Loaded pedestrian connections used for richer examples and metrics."""

    connections: tuple[PedestrianConnection, ...]
    source: str = ""

    def connection_count_by_station(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for connection in self.connections:
            if connection.from_kind == "station":
                counts[connection.from_station_id] += 1
            if connection.to_kind == "station":
                counts[connection.to_station_id] += 1
        return dict(counts)


@dataclass(frozen=True, slots=True)
class NetworkGraphSnapshot:
    """Cached OSM walking graph metadata for one study area."""

    query: AccessibilityQuery
    graph_path: Path
    metadata_path: Path
    refreshed_at: datetime
    network_type: str
    node_count: int
    edge_count: int
    source_url: str
    buffer_meters: int


@dataclass(frozen=True, slots=True)
class AccessibilityComparisonRecord:
    """Per-tract comparison between Euclidean and network accessibility models."""

    tract_id: str
    tract_name: str
    borough: str
    need_score: float
    euclidean_has_access: bool
    network_has_access: bool
    euclidean_station_count: int
    network_station_count: int
    euclidean_station_id: str | None
    network_station_id: str | None
    euclidean_travel_minutes: float | None
    network_travel_minutes: float | None
    euclidean_path_meters: float | None
    network_path_meters: float | None
    coverage_change_label: str


@dataclass(frozen=True, slots=True)
class AccessibilityComparisonDataset:
    """Collection of tract-level Euclidean vs network comparison results."""

    records: tuple[AccessibilityComparisonRecord, ...]

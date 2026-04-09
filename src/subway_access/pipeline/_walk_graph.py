"""Walk graph fetching and loading for ``subway-access``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..io import (
    fetch_walk_graph as io_fetch_walk_graph,
)
from ..io import (
    load_cached_walk_graph as io_load_cached_walk_graph,
)

if TYPE_CHECKING:
    from pathlib import Path

    from ..models import (
        AccessibilityQuery,
        NetworkGraphSnapshot,
    )


def fetch_walk_graph(
    query: AccessibilityQuery,
    *,
    cache_dir: str | Path,
    refresh: bool = False,
    buffer_meters: int = 0,
) -> NetworkGraphSnapshot:
    """Fetch and cache an OSM walking graph for a study area."""

    return io_fetch_walk_graph(
        query,
        cache_dir=cache_dir,
        refresh=refresh,
        buffer_meters=buffer_meters,
    )


def load_cached_walk_graph(
    cache_dir: str | Path,
) -> tuple[Any, NetworkGraphSnapshot]:
    """Load a cached OSM walking graph and its typed metadata."""

    return io_load_cached_walk_graph(cache_dir)

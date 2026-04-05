"""Public analysis helpers for ``subway-access``."""

from __future__ import annotations

from ._core import (
    analyze_gaps,
    build_station_metrics,
    compute_reliability,
    generate_catchments,
    score_accessibility,
)
from ._entrances import (
    entrances_per_complex_id,
    entrances_per_gtfs_stop_id,
    pathways_and_locations_counts,
)
from ._network import (
    compare_accessibility_models,
    generate_network_isochrones,
    score_accessibility_network,
)
from ._summaries import summarize_accessibility_by_group

__all__ = [
    "analyze_gaps",
    "build_station_metrics",
    "compare_accessibility_models",
    "compute_reliability",
    "entrances_per_complex_id",
    "entrances_per_gtfs_stop_id",
    "generate_catchments",
    "generate_network_isochrones",
    "pathways_and_locations_counts",
    "score_accessibility",
    "score_accessibility_network",
    "summarize_accessibility_by_group",
]

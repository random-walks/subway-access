"""Top-level package for the planned ``subway-access`` API surface.

The repository is intentionally seeded with typed placeholders so contributors
can see the target shape of the library before the implementation lands.
"""

from __future__ import annotations

from ._version import version as __version__
from .cli import main
from .exporters import export_catchments_geojson, export_gap_table, export_station_metrics
from .loaders import load_accessibility_status, load_census_data, load_gtfs, load_outages, load_pedestrian_network
from .models import AccessibilityQuery, CatchmentRequest, ExportTarget, TimeWindow
from .processors import analyze_gaps, compute_reliability, generate_catchments, score_accessibility

__all__ = [
    "AccessibilityQuery",
    "CatchmentRequest",
    "ExportTarget",
    "TimeWindow",
    "__version__",
    "analyze_gaps",
    "compute_reliability",
    "export_catchments_geojson",
    "export_gap_table",
    "export_station_metrics",
    "generate_catchments",
    "load_accessibility_status",
    "load_census_data",
    "load_gtfs",
    "load_outages",
    "load_pedestrian_network",
    "main",
    "score_accessibility",
]

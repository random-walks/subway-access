"""Top-level package for the real and planned ``subway-access`` API surface."""

from __future__ import annotations

from ._version import version as __version__
from .cli import main
from .exporters import export_catchments_geojson, export_gap_table, export_station_metrics
from .loaders import load_accessibility_status, load_census_data, load_gtfs, load_outages, load_pedestrian_network
from .models import (
    AccessibilityDataset,
    AccessibilityQuery,
    AccessibilityScoreDataset,
    AccessibilityStatus,
    CatchmentDataset,
    CatchmentFeature,
    CatchmentRequest,
    DemographicDataset,
    ExportTarget,
    GapAnalysis,
    GapRecord,
    Station,
    StationDataset,
    TimeWindow,
    TractAccessibilityRecord,
    TractDemographics,
)
from .processors import analyze_gaps, compute_reliability, generate_catchments, score_accessibility

__all__ = [
    "AccessibilityDataset",
    "AccessibilityQuery",
    "AccessibilityScoreDataset",
    "AccessibilityStatus",
    "CatchmentDataset",
    "CatchmentFeature",
    "CatchmentRequest",
    "DemographicDataset",
    "ExportTarget",
    "GapAnalysis",
    "GapRecord",
    "Station",
    "StationDataset",
    "TimeWindow",
    "TractAccessibilityRecord",
    "TractDemographics",
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

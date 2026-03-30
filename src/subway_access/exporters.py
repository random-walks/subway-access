"""Planned exporters for map-ready and analysis-ready outputs."""

from __future__ import annotations

from typing import Any

from ._not_implemented import planned_surface
from .models import ExportTarget


def export_catchments_geojson(data: Any, target: ExportTarget) -> Any:
    """Export station catchments to GeoJSON for mapping workflows."""
    planned_surface("export_catchments_geojson()")


def export_station_metrics(data: Any, target: ExportTarget) -> Any:
    """Export station-level accessibility and reliability metrics."""
    planned_surface("export_station_metrics()")


def export_gap_table(data: Any, target: ExportTarget) -> Any:
    """Export tract- or district-level accessibility gap tables."""
    planned_surface("export_gap_table()")

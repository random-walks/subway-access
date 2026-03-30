"""Planned processing steps for subway accessibility analysis."""

from __future__ import annotations

from typing import Any

from ._not_implemented import planned_surface
from .models import CatchmentRequest, TimeWindow


def generate_catchments(station_data: Any, request: CatchmentRequest) -> Any:
    """Generate station catchments for a chosen walk-time threshold."""
    planned_surface("generate_catchments()")


def compute_reliability(accessibility_data: Any, outage_data: Any, window: TimeWindow) -> Any:
    """Compute accessibility reliability over a rolling outage window."""
    planned_surface("compute_reliability()")


def score_accessibility(station_data: Any, catchments: Any, demographics: Any) -> Any:
    """Score accessibility using station, catchment, and demographic inputs."""
    planned_surface("score_accessibility()")


def analyze_gaps(scored_data: Any) -> Any:
    """Identify geographies with high need and weak reliable access."""
    planned_surface("analyze_gaps()")

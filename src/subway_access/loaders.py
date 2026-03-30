"""Planned loader entry points for accessibility-related source data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ._not_implemented import planned_surface


def load_gtfs(source: str | Path) -> Any:
    """Load MTA GTFS static data for stations, routes, and stop metadata."""
    planned_surface("load_gtfs()")


def load_accessibility_status(source: str | Path) -> Any:
    """Load official station accessibility status and directionality data."""
    planned_surface("load_accessibility_status()")


def load_outages(source: str | Path) -> Any:
    """Load current or historical elevator and escalator outage data."""
    planned_surface("load_outages()")


def load_census_data(source: str | Path) -> Any:
    """Load tract-level demographic variables used in need scoring."""
    planned_surface("load_census_data()")


def load_pedestrian_network(source: str | Path | None = None) -> Any:
    """Load or build the pedestrian network used for catchment analysis."""
    del source
    planned_surface("load_pedestrian_network()")

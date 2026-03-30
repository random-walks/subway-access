"""Helpers for accessing packaged fixture data."""

from __future__ import annotations

from pathlib import Path

_FIXTURES_DIRECTORY = Path(__file__).resolve().parent / "data" / "fixtures"

DEFAULT_STATIONS_FIXTURE = _FIXTURES_DIRECTORY / "stations.csv"
DEFAULT_ACCESSIBILITY_FIXTURE = _FIXTURES_DIRECTORY / "accessibility.csv"
DEFAULT_TRACTS_FIXTURE = _FIXTURES_DIRECTORY / "tracts.geojson"

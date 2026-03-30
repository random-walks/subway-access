"""Helpers for accessing packaged fixture data."""

from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path
from typing import ContextManager

_FIXTURE_PACKAGE = "subway_access.data.fixtures"

with as_file(files(_FIXTURE_PACKAGE).joinpath("stations.csv")) as _stations_path:
    DEFAULT_STATIONS_FIXTURE = _stations_path.resolve()

with as_file(files(_FIXTURE_PACKAGE).joinpath("accessibility.csv")) as _accessibility_path:
    DEFAULT_ACCESSIBILITY_FIXTURE = _accessibility_path.resolve()

with as_file(files(_FIXTURE_PACKAGE).joinpath("tracts.geojson")) as _tracts_path:
    DEFAULT_TRACTS_FIXTURE = _tracts_path.resolve()


def fixture_path(name: str) -> ContextManager[Path]:
    """Return a context manager yielding an installed fixture path."""

    resource = files(_FIXTURE_PACKAGE).joinpath(name)
    return as_file(resource)

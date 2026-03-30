"""Helpers for accessing packaged fixture data."""

from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path
from typing import ContextManager


def fixture_path(name: str) -> ContextManager[Path]:
    """Return a context manager yielding an installed fixture path."""

    resource = files("subway_access.data.fixtures").joinpath(name)
    return as_file(resource)

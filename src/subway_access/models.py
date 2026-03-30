"""Typed planning models for the target ``subway-access`` package surface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TimeWindow:
    """Rolling time window used for reliability calculations."""

    days: int


@dataclass(frozen=True)
class CatchmentRequest:
    """Request parameters for station catchment generation."""

    minutes: int
    mode: str = "walk"


@dataclass(frozen=True)
class AccessibilityQuery:
    """High-level filter for a borough or district analysis pass."""

    geography: str
    value: str


@dataclass(frozen=True)
class ExportTarget:
    """Destination metadata for an eventual export command."""

    format: str
    output_path: Path

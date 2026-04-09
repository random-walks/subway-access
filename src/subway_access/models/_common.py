"""Shared helpers and type aliases for ``subway-access`` models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

AccessibilityLabel = Literal[
    "accessible",
    "partially_accessible",
    "not_accessible",
    "unknown",
]
EquipmentType = Literal["elevator", "escalator", "station", "platform", "unknown"]
OutageStatus = Literal["active", "resolved", "scheduled", "unknown"]


def _coerce_utc(value: datetime) -> datetime:
    """Return a timezone-aware UTC datetime for reliable window math."""

    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class AccessibilityQuery:
    """High-level filter for a borough or district analysis pass."""

    geography: str
    value: str

from __future__ import annotations

import importlib.metadata
from datetime import datetime, timezone

import pytest

import subway_access
from subway_access.models import (
    OutageRecord,
    TimeWindow,
)


def _metadata_version_matches_package(
    metadata_version: str, package_version: str
) -> bool:
    """Hatch-VCS can append a date segment to the generated ``_version.py`` local
    part (``+gHASH.dYYYYMMDD``) while editable-install metadata keeps the shorter
    local part (``+gHASH``). Both describe the same VCS state.
    """
    if metadata_version == package_version:
        return True
    if "+" not in metadata_version or "+" not in package_version:
        return False
    meta_base, meta_local = metadata_version.split("+", 1)
    pkg_base, pkg_local = package_version.split("+", 1)
    return meta_base == pkg_base and pkg_local.startswith(meta_local + ".")


def test_root_namespace_only_exports_version() -> None:
    assert subway_access.__all__ == ["__version__"]
    assert _metadata_version_matches_package(
        importlib.metadata.version("subway-access"),
        subway_access.__version__,
    )


def test_time_window_rejects_non_positive_days() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        TimeWindow(days=0)


def test_outage_record_overlap_minutes_clips_to_window() -> None:
    record = OutageRecord(
        station_id="ST001",
        equipment_id="ELV-01",
        equipment_type="elevator",
        status="resolved",
        started_at=datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 4, 3, 12, 0, tzinfo=timezone.utc),
    )

    overlap = record.overlap_minutes(
        TimeWindow(days=2),
        as_of=datetime(2026, 4, 4, 0, 0, tzinfo=timezone.utc),
    )

    assert overlap == 2160


def test_outage_record_overlap_uses_minutes_override() -> None:
    record = OutageRecord(
        station_id="21",
        equipment_id="EL22X",
        equipment_type="elevator",
        status="resolved",
        started_at=datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 2, 28, 23, 59, 59, tzinfo=timezone.utc),
        outage_minutes_override=290,
    )

    overlap = record.overlap_minutes(
        TimeWindow(days=365),
        as_of=datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc),
    )

    assert overlap == 290

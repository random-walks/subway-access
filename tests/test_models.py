from __future__ import annotations

import importlib.metadata
from datetime import datetime, timezone

import pytest

import subway_access
from subway_access.models import (
    OutageRecord,
    TimeWindow,
)


def test_root_namespace_only_exports_version() -> None:
    assert subway_access.__all__ == ["__version__"]
    assert importlib.metadata.version("subway-access") == subway_access.__version__


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

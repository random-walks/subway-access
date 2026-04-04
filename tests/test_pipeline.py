from __future__ import annotations

import os
from pathlib import Path

import pytest

from subway_access import models, pipeline
from tests.test_helpers import TEST_DATA_DIR


def test_load_cached_snapshot_reads_real_slice() -> None:
    snapshot = pipeline.load_cached_snapshot(TEST_DATA_DIR)

    assert snapshot.query.geography == "borough"
    assert snapshot.query.value == "Manhattan"
    assert len(snapshot.stations.stations) == 5
    assert len(snapshot.metadata) == 3


@pytest.mark.skipif(
    os.getenv("SUBWAY_ACCESS_RUN_LIVE") != "1",
    reason="live snapshot fetch is skipped unless SUBWAY_ACCESS_RUN_LIVE=1",
)
def test_fetch_study_area_snapshot_live(tmp_path: Path) -> None:
    snapshot = pipeline.fetch_study_area_snapshot(
        models.AccessibilityQuery(geography="borough", value="Manhattan"),
        cache_dir=tmp_path,
        refresh=True,
        availability_months=1,
        include_gtfs_archive=False,
    )

    assert len(snapshot.stations.stations) > 100
    assert len(snapshot.demographics.tracts) > 100
    assert (tmp_path / "snapshot-metadata.json").exists()

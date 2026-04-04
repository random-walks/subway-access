from __future__ import annotations

import pytest

from tests.test_helpers import build_snapshot_bundle


def test_generate_catchments_and_accessibility_scores_from_real_slice() -> None:
    bundle = build_snapshot_bundle()

    radius_by_station = bundle.catchments.radius_by_station_id()
    assert radius_by_station["21"] == pytest.approx(800.0)
    assert len(bundle.catchments.features[0].polygon) == 25

    scores_by_tract = {record.tract_id: record for record in bundle.scores.records}
    assert scores_by_tract["36061001300"].has_accessible_station is True
    assert scores_by_tract["36061001300"].nearest_accessible_station_id == "21"
    assert scores_by_tract["36061001501"].nearest_accessible_station_id == "105"


def test_compute_reliability_uses_real_availability_slice() -> None:
    bundle = build_snapshot_bundle()
    reliability_by_station = {
        record.station_id: record for record in bundle.reliability.records
    }

    assert reliability_by_station["105"].outage_minutes == 1240
    assert reliability_by_station["105"].reliability_label == "full_service"
    assert reliability_by_station["21"].reliability_score == 1.0
    assert reliability_by_station["23"].reliability_label == "not_accessible"


def test_build_station_metrics_aggregates_real_snapshot_outputs() -> None:
    bundle = build_snapshot_bundle()
    metrics_by_station = {
        record.station_id: record for record in bundle.station_metrics.records
    }

    assert metrics_by_station["21"].covered_population == 29577
    assert metrics_by_station["105"].covered_population == 24206
    assert metrics_by_station["21"].daytime_routes == ("R", "W")
    assert metrics_by_station["21"].structure == "Subway"

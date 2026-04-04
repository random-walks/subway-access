from __future__ import annotations

import pytest

from tests.helpers import build_demo_bundle


def test_generate_catchments_and_gap_scoring() -> None:
    bundle = build_demo_bundle()
    catchments = bundle.catchments
    scores = bundle.scores
    gaps = bundle.gaps

    radius_by_station = catchments.radius_by_station_id()
    assert radius_by_station["ST001"] == pytest.approx(800.0)
    assert len(catchments.features[0].polygon) == 25

    scores_by_tract = {record.tract_id: record for record in scores.records}
    assert scores_by_tract["36061000400"].has_accessible_station is False
    assert scores_by_tract["36061000400"].accessible_station_count == 0
    assert scores_by_tract["36061000400"].nearest_accessible_station_id == "ST001"

    top_gap = gaps.records[0]
    assert top_gap.tract_id == "36061000400"
    assert top_gap.gap_label == "gap"
    assert top_gap.gap_score == pytest.approx(0.2266666667)


def test_compute_reliability_uses_fixture_outage_history() -> None:
    bundle = build_demo_bundle()
    reliability = bundle.reliability
    reliability_by_station = {record.station_id: record for record in reliability.records}

    assert reliability_by_station["ST001"].outage_minutes == 630
    assert reliability_by_station["ST001"].reliability_score == pytest.approx(
        1 - (630 / 43200)
    )
    assert reliability_by_station["ST001"].reliability_label == "strong"
    assert reliability_by_station["ST002"].reliability_score == 0.0
    assert reliability_by_station["ST002"].reliability_label == "not_accessible"
    assert reliability_by_station["ST003"].reliability_label == "at_risk"


def test_build_station_metrics_combines_gap_reliability_and_network() -> None:
    bundle = build_demo_bundle()
    station_metrics = bundle.station_metrics
    metrics_by_station = {record.station_id: record for record in station_metrics.records}

    assert metrics_by_station["ST001"].covered_population == 11300
    assert metrics_by_station["ST001"].nearby_gap_tract_count == 2
    assert metrics_by_station["ST001"].network_connection_count == 2
    assert metrics_by_station["ST001"].reliability_label == "strong"
    assert metrics_by_station["ST003"].covered_tract_count == 0
    assert metrics_by_station["ST003"].network_connection_count == 2

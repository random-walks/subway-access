"""Tests for the temporal panel infrastructure."""

from __future__ import annotations

import pytest

from subway_access.models import Station, StationDataset
from subway_access.temporal import (
    PanelDataset,
    PanelObservation,
    StationUpgradeRecord,
    UpgradeTimeline,
    build_distance_weights,
    build_panel_dataset,
    build_upgrade_timeline,
)


def _make_upgrade_timeline() -> UpgradeTimeline:
    return UpgradeTimeline(
        records=(
            StationUpgradeRecord(
                station_id="S1",
                station_name="Station A",
                borough="Manhattan",
                latitude=40.750,
                longitude=-73.990,
                upgrade_year=2019,
            ),
            StationUpgradeRecord(
                station_id="S2",
                station_name="Station B",
                borough="Manhattan",
                latitude=40.755,
                longitude=-73.985,
                upgrade_year=None,
            ),
        )
    )


def _make_vintage_estimates() -> dict[int, dict[str, dict[str, object]]]:
    """Two tracts across two vintage years."""

    tract_a = {
        "tract_id": "36061000100",
        "tract_name": "Tract A",
        "total_population": 5000,
        "disability_rate": 0.10,
        "senior_rate": 0.15,
        "poverty_rate": 0.20,
        "centroid_latitude": 40.751,
        "centroid_longitude": -73.991,
    }
    tract_b = {
        "tract_id": "36061000200",
        "tract_name": "Tract B",
        "total_population": 3000,
        "disability_rate": 0.08,
        "senior_rate": 0.12,
        "poverty_rate": 0.18,
        "centroid_latitude": 40.760,
        "centroid_longitude": -73.980,
    }
    return {
        2019: {"36061000100": dict(tract_a), "36061000200": dict(tract_b)},
        2020: {"36061000100": dict(tract_a), "36061000200": dict(tract_b)},
    }


class TestUpgradeTimeline:
    def test_stations_upgraded_by(self) -> None:
        timeline = _make_upgrade_timeline()
        assert timeline.stations_upgraded_by(2018) == ()
        assert timeline.stations_upgraded_by(2019) == ("S1",)
        assert timeline.stations_upgraded_by(2025) == ("S1",)

    def test_upgrade_year_for(self) -> None:
        timeline = _make_upgrade_timeline()
        assert timeline.upgrade_year_for("S1") == 2019
        assert timeline.upgrade_year_for("S2") is None
        assert timeline.upgrade_year_for("S99") is None


class TestBuildUpgradeTimeline:
    def test_from_station_dataset(self) -> None:
        stations = StationDataset(
            stations=(
                Station(
                    station_id="S1",
                    name="Station A",
                    borough="Manhattan",
                    latitude=40.750,
                    longitude=-73.990,
                    ada_status="accessible",
                ),
            )
        )
        timeline = build_upgrade_timeline(
            stations, known_upgrades={"S1": 2019}
        )
        assert len(timeline.records) == 1
        assert timeline.records[0].upgrade_year == 2019


class TestBuildPanelDataset:
    def test_basic_panel_construction(self) -> None:
        timeline = _make_upgrade_timeline()
        station_locations = {
            "S1": (40.750, -73.990),
            "S2": (40.755, -73.985),
        }
        vintage = _make_vintage_estimates()
        panel = build_panel_dataset(
            vintage,
            station_locations,
            timeline,
            catchment_radius_meters=500.0,
        )
        assert isinstance(panel, PanelDataset)
        assert panel.periods == ("2019", "2020")
        assert panel.unit_type == "tract"
        assert len(panel.observations) == 4  # 2 tracts x 2 years

    def test_treatment_and_control_groups(self) -> None:
        timeline = _make_upgrade_timeline()
        station_locations = {
            "S1": (40.750, -73.990),
            "S2": (40.755, -73.985),
        }
        vintage = _make_vintage_estimates()
        panel = build_panel_dataset(
            vintage,
            station_locations,
            timeline,
            catchment_radius_meters=500.0,
        )
        treatment = panel.treatment_group()
        control = panel.control_group()
        # All observations should be in either treatment or control
        assert len(treatment.observations) + len(control.observations) == len(
            panel.observations
        )

    def test_observations_have_need_score(self) -> None:
        timeline = _make_upgrade_timeline()
        station_locations = {"S1": (40.750, -73.990)}
        vintage = _make_vintage_estimates()
        panel = build_panel_dataset(
            vintage,
            station_locations,
            timeline,
        )
        for obs in panel.observations:
            assert isinstance(obs.need_score, float)
            assert obs.need_score > 0

    def test_unit_ids(self) -> None:
        timeline = _make_upgrade_timeline()
        station_locations = {"S1": (40.750, -73.990)}
        vintage = _make_vintage_estimates()
        panel = build_panel_dataset(vintage, station_locations, timeline)
        assert panel.unit_ids == ("36061000100", "36061000200")


class TestPanelObservation:
    def test_default_covariates(self) -> None:
        obs = PanelObservation(
            unit_id="T1",
            period="2020",
            has_accessible_station=True,
            treatment_year=2019,
            disability_rate=0.1,
            senior_rate=0.15,
            poverty_rate=0.2,
            total_population=5000,
            accessible_station_count=2,
            nearest_accessible_distance_m=300.0,
            need_score=0.15,
        )
        assert obs.covariates is None


class TestDistanceWeights:
    def test_nearby_units_are_neighbors(self) -> None:
        centroids = {
            "T1": (40.750, -73.990),
            "T2": (40.751, -73.991),
        }
        weights = build_distance_weights(centroids, threshold_meters=500)
        assert "T2" in weights["T1"]
        assert "T1" in weights["T2"]

    def test_far_units_not_neighbors(self) -> None:
        centroids = {
            "T1": (40.750, -73.990),
            "T2": (41.000, -74.500),
        }
        weights = build_distance_weights(centroids, threshold_meters=500)
        assert "T2" not in weights["T1"]

    def test_row_standardized(self) -> None:
        centroids = {
            "T1": (40.750, -73.990),
            "T2": (40.751, -73.991),
            "T3": (40.752, -73.992),
        }
        weights = build_distance_weights(centroids, threshold_meters=5000)
        for uid in centroids:
            row_sum = sum(weights[uid].values())
            if row_sum > 0:
                assert row_sum == pytest.approx(1.0)

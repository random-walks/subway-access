from __future__ import annotations

import json
from pathlib import Path

import pytest

from subway_access.io import (
    load_accessibility_status,
    load_census_data,
    load_gtfs,
    load_outages,
    load_pedestrian_network,
)
from tests.test_helpers import TEST_DATA_DIR


def test_loaders_read_committed_real_snapshot_slice() -> None:
    stations = load_gtfs(TEST_DATA_DIR / "stations.csv")
    accessibility = load_accessibility_status(TEST_DATA_DIR / "accessibility.csv")
    demographics = load_census_data(TEST_DATA_DIR / "tracts.geojson")
    outages = load_outages(TEST_DATA_DIR / "outages.json")
    merged = stations.with_accessibility(accessibility)

    assert len(stations.stations) == 5
    assert merged.as_mapping()["21"].ada_status == "accessible"
    assert merged.as_mapping()["23"].ada_status == "not_accessible"
    assert len(demographics.tracts) == 4
    assert len(outages.records) == 4


def test_duplicate_station_ids_raise_value_error(tmp_path: Path) -> None:
    station_path = tmp_path / "stations.csv"
    station_path.write_text(
        (
            "station_id,name,borough,latitude,longitude\n"
            "21,Cortlandt St,Manhattan,40.710668,-74.011029\n"
            "21,Cortlandt St Duplicate,Manhattan,40.710668,-74.011029\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate station_id values: 21"):
        load_gtfs(station_path)


def test_load_outages_accepts_json_payload_with_override_fields(tmp_path: Path) -> None:
    outage_path = tmp_path / "outages.json"
    outage_path.write_text(
        json.dumps(
            {
                "outages": [
                    {
                        "station_id": "21",
                        "station_complex_id": "624",
                        "equipment_id": "EL22X",
                        "equipment_type": "elevator",
                        "status": "resolved",
                        "started_at": "2026-02-01T00:00:00Z",
                        "ended_at": "2026-02-28T23:59:59Z",
                        "outage_minutes_override": 120,
                        "availability_ratio": 0.99,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    outages = load_outages(outage_path)

    assert outages.records[0].station_complex_id == "624"
    assert outages.records[0].outage_minutes_override == 120


def test_load_pedestrian_network_rejects_non_linestring_geometry(
    tmp_path: Path,
) -> None:
    network_path = tmp_path / "network.geojson"
    network_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "from_station_id": "21",
                            "to_station_id": "105",
                            "walk_minutes": 5,
                            "distance_meters": 400,
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [-74.0, 40.71],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match="must use LineString geometry"):
        load_pedestrian_network(network_path)

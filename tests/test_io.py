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


def test_loader_happy_path_uses_fixture_defaults() -> None:
    station_data = load_gtfs()
    accessibility = load_accessibility_status()
    demographics = load_census_data()
    outages = load_outages()
    network = load_pedestrian_network()
    merged = station_data.with_accessibility(accessibility)

    assert len(station_data.stations) == 3
    assert merged.as_mapping()["ST001"].ada_status == "accessible"
    assert merged.as_mapping()["ST002"].ada_status == "not_accessible"
    assert len(demographics.tracts) == 4
    assert len(outages.records) == 3
    assert len(network.connections) == 3


def test_duplicate_station_ids_raise_value_error(tmp_path: Path) -> None:
    station_path = tmp_path / "stations.csv"
    station_path.write_text(
        (
            "station_id,stop_id,name,borough,latitude,longitude\n"
            "ST001,A12,Station One,Manhattan,40.75,-73.99\n"
            "ST001,A13,Station Duplicate,Manhattan,40.76,-73.98\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate station_id values: ST001"):
        load_gtfs(station_path)


def test_load_outages_accepts_json_payload(tmp_path: Path) -> None:
    outage_path = tmp_path / "outages.json"
    outage_path.write_text(
        json.dumps(
            {
                "outages": [
                    {
                        "station_id": "ST001",
                        "equipment_id": "ELV-01",
                        "equipment_type": "elevator",
                        "status": "resolved",
                        "started_at": "2026-04-01T00:00:00Z",
                        "ended_at": "2026-04-01T02:30:00Z",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    outages = load_outages(outage_path)

    assert len(outages.records) == 1
    assert outages.records[0].station_id == "ST001"


def test_load_pedestrian_network_rejects_non_linestring_geometry(tmp_path: Path) -> None:
    network_path = tmp_path / "network.geojson"
    network_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "from_station_id": "ST001",
                            "to_station_id": "ST002",
                            "walk_minutes": 5,
                            "distance_meters": 400,
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [-73.99, 40.75],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match="must use LineString geometry"):
        load_pedestrian_network(network_path)

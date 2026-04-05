from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from subway_access import analysis
from subway_access.io import (
    build_entrance_snapshot_rows,
    load_entrances,
    load_gtfs_pathways_snapshot,
    parse_gtfs_pathways_zip,
)
from subway_access.io._entrances import entrances_to_geojson
from subway_access.io._gtfs_static import gtfs_pathways_snapshot_to_json
from subway_access.models import GtfsPathwaysSnapshot


def test_build_and_roundtrip_entrance_rows(tmp_path: Path) -> None:
    raw = [
        {
            "station_id": "1",
            "gtfs_stop_id": "A12",
            "complex_id": "100",
            "stop_name": "Test",
            "constituent_station_name": "Test",
            "borough": "M",
            "division": "IRT",
            "line": "Lexington",
            "daytime_routes": "4 5 6",
            "entrance_type": "Stair",
            "entry_allowed": "YES",
            "exit_allowed": "NO",
            "entrance_latitude": "40.75",
            "entrance_longitude": "-73.99",
        }
    ]
    normalized = build_entrance_snapshot_rows(raw)
    assert len(normalized) == 1
    assert normalized[0]["entrance_id"]
    assert normalized[0]["latitude"] == 40.75
    assert normalized[0]["entry_allowed"] is True
    assert normalized[0]["exit_allowed"] is False

    path = tmp_path / "e.geojson"
    path.write_text(
        json.dumps(entrances_to_geojson(normalized)),
        encoding="utf-8",
    )
    dataset = load_entrances(path)
    assert len(dataset.entrances) == 1
    assert dataset.entrances[0].gtfs_stop_id == "A12"
    assert analysis.entrances_per_gtfs_stop_id(dataset) == {"A12": 1}
    assert analysis.entrances_per_complex_id(dataset) == {"100": 1}


def test_parse_gtfs_pathways_zip_returns_none_without_files(tmp_path: Path) -> None:
    zpath = tmp_path / "empty.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("stops.txt", "stop_id,stop_name,stop_lat,stop_lon\n")
    zpath.write_bytes(buf.getvalue())
    assert parse_gtfs_pathways_zip(zpath) is None


def test_parse_gtfs_pathways_zip_reads_pathways(tmp_path: Path) -> None:
    zpath = tmp_path / "p.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr(
            "pathways.txt",
            "pathway_id,from_stop_id,to_stop_id,pathway_mode,is_bidirectional\n"
            "pw1,stopA,stopB,2,1\n",
        )
    snap = parse_gtfs_pathways_zip(zpath)
    assert snap is not None
    assert len(snap.pathways) == 1
    assert snap.pathways[0].pathway_id == "pw1"
    assert analysis.pathways_and_locations_counts(snap) == (1, 0)


def test_gtfs_pathways_json_roundtrip(tmp_path: Path) -> None:
    snap = GtfsPathwaysSnapshot(pathways=(), locations=())
    path = tmp_path / "gp.json"
    path.write_text(
        json.dumps(gtfs_pathways_snapshot_to_json(snap)),
        encoding="utf-8",
    )
    loaded = load_gtfs_pathways_snapshot(path)
    assert len(loaded.pathways) == 0
    assert analysis.pathways_and_locations_counts(loaded) == (0, 0)

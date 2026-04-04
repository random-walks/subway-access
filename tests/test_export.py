from __future__ import annotations

import csv
import json
from pathlib import Path

from subway_access.export import (
    export_catchments_geojson,
    export_gap_table,
    export_station_metrics,
)
from subway_access.models import ExportTarget
from tests.helpers import build_snapshot_bundle


def test_exporters_write_expected_outputs_from_real_slice(tmp_path: Path) -> None:
    bundle = build_snapshot_bundle()

    catchment_path = export_catchments_geojson(
        bundle.catchments,
        ExportTarget(format="geojson", output_path=tmp_path / "catchments.geojson"),
    )
    gap_path = export_gap_table(
        bundle.gaps,
        ExportTarget(format="csv", output_path=tmp_path / "gaps.csv"),
    )
    station_csv_path = export_station_metrics(
        bundle.station_metrics,
        ExportTarget(format="csv", output_path=tmp_path / "station-metrics.csv"),
    )
    station_geojson_path = export_station_metrics(
        bundle.station_metrics,
        ExportTarget(format="geojson", output_path=tmp_path / "station-metrics.geojson"),
    )

    catchment_payload = json.loads(catchment_path.read_text(encoding="utf-8"))
    assert catchment_payload["type"] == "FeatureCollection"
    assert len(catchment_payload["features"]) == 5

    with gap_path.open(newline="", encoding="utf-8") as handle:
        gap_rows = list(csv.DictReader(handle))
    assert gap_rows[0]["tract_id"] == "36061001300"
    assert gap_rows[0]["gap_label"] == "covered"

    with station_csv_path.open(newline="", encoding="utf-8") as handle:
        station_rows = list(csv.DictReader(handle))
    assert station_rows[0]["station_id"] == "20"
    assert "daytime_routes" in station_rows[0]

    station_geojson_payload = json.loads(station_geojson_path.read_text(encoding="utf-8"))
    assert [feature["id"] for feature in station_geojson_payload["features"]] == [
        "20",
        "21",
        "22",
        "23",
        "105",
    ]

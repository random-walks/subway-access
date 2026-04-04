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
from tests.helpers import build_demo_bundle


def test_exporters_write_expected_outputs(tmp_path: Path) -> None:
    bundle = build_demo_bundle()
    catchments = bundle.catchments
    gaps = bundle.gaps
    station_metrics = bundle.station_metrics

    geojson_target = ExportTarget(
        format="geojson",
        output_path=tmp_path / "catchments.geojson",
    )
    gap_csv_target = ExportTarget(format="csv", output_path=tmp_path / "gaps.csv")
    station_csv_target = ExportTarget(
        format="csv",
        output_path=tmp_path / "station-metrics.csv",
    )
    station_geojson_target = ExportTarget(
        format="geojson",
        output_path=tmp_path / "station-metrics.geojson",
    )

    catchment_path = export_catchments_geojson(catchments, geojson_target)
    gap_path = export_gap_table(gaps, gap_csv_target)
    station_csv_path = export_station_metrics(station_metrics, station_csv_target)
    station_geojson_path = export_station_metrics(
        station_metrics,
        station_geojson_target,
    )

    catchment_payload = json.loads(catchment_path.read_text(encoding="utf-8"))
    assert catchment_payload["type"] == "FeatureCollection"
    assert len(catchment_payload["features"]) == 3

    with gap_path.open(newline="", encoding="utf-8") as handle:
        gap_rows = list(csv.DictReader(handle))
    assert gap_rows[0]["tract_id"] == "36061000400"
    assert gap_rows[0]["gap_label"] == "gap"

    with station_csv_path.open(newline="", encoding="utf-8") as handle:
        station_rows = list(csv.DictReader(handle))
    assert station_rows[0]["station_id"] == "ST001"
    assert station_rows[0]["reliability_label"] == "strong"

    station_geojson_payload = json.loads(station_geojson_path.read_text(encoding="utf-8"))
    assert [feature["id"] for feature in station_geojson_payload["features"]] == [
        "ST001",
        "ST002",
        "ST003",
    ]

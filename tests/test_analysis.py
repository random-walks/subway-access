from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING

import pytest

from subway_access.cli import main
from subway_access.exporters import export_catchments_geojson, export_gap_table
from subway_access.loaders import (
    load_accessibility_status,
    load_census_data,
    load_gtfs,
    load_outages,
    load_pedestrian_network,
)
from subway_access.models import CatchmentRequest, ExportTarget, TimeWindow
from subway_access.processors import (
    analyze_gaps,
    compute_reliability,
    generate_catchments,
    score_accessibility,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_loader_happy_path_uses_fixture_defaults() -> None:
    station_data = load_gtfs()
    accessibility = load_accessibility_status()
    demographics = load_census_data()
    merged = station_data.with_accessibility(accessibility)

    assert len(station_data.stations) == 3
    assert merged.as_mapping()["ST001"].ada_status == "accessible"
    assert merged.as_mapping()["ST002"].ada_status == "not_accessible"
    assert len(demographics.tracts) == 4


def test_station_without_accessibility_row_becomes_unknown(tmp_path: Path) -> None:
    station_path = tmp_path / "stations.csv"
    station_path.write_text(
        (
            "station_id,stop_id,name,borough,latitude,longitude\n"
            "ST001,A12,Station One,Manhattan,40.75,-73.99\n"
            "ST002,A13,Station Two,Manhattan,40.76,-73.98\n"
        ),
        encoding="utf-8",
    )
    accessibility_path = tmp_path / "accessibility.csv"
    accessibility_path.write_text(
        "station_id,ada_status\nST001,accessible\n",
        encoding="utf-8",
    )

    merged = load_gtfs(station_path).with_accessibility(
        load_accessibility_status(accessibility_path)
    )

    assert merged.as_mapping()["ST001"].ada_status == "accessible"
    assert merged.as_mapping()["ST002"].ada_status == "unknown"


def test_station_join_rejects_unknown_accessibility_station_ids(tmp_path: Path) -> None:
    station_path = tmp_path / "stations.csv"
    station_path.write_text(
        "station_id,stop_id,name,borough,latitude,longitude\nST001,A12,Station One,Manhattan,40.75,-73.99\n",
        encoding="utf-8",
    )
    accessibility_path = tmp_path / "accessibility.csv"
    accessibility_path.write_text(
        "station_id,ada_status\nST999,accessible\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown station IDs: ST999"):
        load_gtfs(station_path).with_accessibility(
            load_accessibility_status(accessibility_path)
        )


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


def test_generate_catchments_and_gap_scoring() -> None:
    station_data = load_gtfs().with_accessibility(load_accessibility_status())
    demographics = load_census_data()
    catchments = generate_catchments(
        station_data, CatchmentRequest(minutes=10)
    )
    scores = score_accessibility(station_data, catchments, demographics)
    gaps = analyze_gaps(scores)

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


def test_exporters_write_expected_gap_and_geojson_outputs(tmp_path: Path) -> None:
    station_data = load_gtfs().with_accessibility(load_accessibility_status())
    demographics = load_census_data()
    catchments = generate_catchments(
        station_data, CatchmentRequest(minutes=10)
    )
    gaps = analyze_gaps(score_accessibility(station_data, catchments, demographics))

    geojson_target = ExportTarget(format="geojson", output_path=tmp_path / "catchments.geojson")
    csv_target = ExportTarget(format="csv", output_path=tmp_path / "gaps.csv")
    geojson_path = export_catchments_geojson(catchments, geojson_target)
    csv_path = export_gap_table(gaps, csv_target)

    assert geojson_path.exists()
    assert csv_path.exists()

    payload = json.loads(geojson_path.read_text(encoding="utf-8"))
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 3

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert reader.fieldnames is not None
    assert "gap_score" in reader.fieldnames
    assert rows[0]["tract_id"] == "36061000400"
    assert rows[0]["gap_label"] == "gap"


def test_cli_demo_writes_outputs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["demo", "--output-dir", str(tmp_path), "--minutes", "10"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (tmp_path / "catchments.geojson").exists()
    assert (tmp_path / "accessibility-gaps.csv").exists()
    assert "Generated subway-access v0.1 demo outputs" in captured.out


def test_placeholder_surfaces_still_fail_loudly(tmp_path: Path) -> None:
    with pytest.raises(NotImplementedError, match="load_outages"):
        load_outages(tmp_path / "outages.json")
    with pytest.raises(NotImplementedError, match="load_pedestrian_network"):
        load_pedestrian_network()
    with pytest.raises(NotImplementedError, match="compute_reliability"):
        compute_reliability(object(), object(), TimeWindow(days=30))


def test_cli_rejects_non_positive_minutes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["demo", "--output-dir", str(tmp_path), "--minutes", "0"])
    captured = capsys.readouterr()

    assert exc_info.value.code == 2
    assert "must be greater than zero" in captured.err

from __future__ import annotations

import importlib.metadata
from pathlib import Path

import pytest

import subway_access as m
from subway_access.models import (
    AccessibilityQuery,
    CatchmentRequest,
    ExportTarget,
    TimeWindow,
)


def test_version() -> None:
    assert importlib.metadata.version("subway_access") == m.__version__


def test_planned_surface_is_importable() -> None:
    window = TimeWindow(days=30)
    request = CatchmentRequest(minutes=10)
    query = AccessibilityQuery(geography="borough", value="manhattan")
    target = ExportTarget(format="csv", output_path=Path("station-metrics.csv"))

    assert window.days == 30
    assert request.minutes == 10
    assert query.value == "manhattan"
    assert target.format == "csv"
    assert callable(m.load_gtfs)
    assert callable(m.generate_catchments)
    assert callable(m.export_station_metrics)


def test_unimplemented_surfaces_fail_loudly() -> None:
    with pytest.raises(NotImplementedError, match="load_outages"):
        m.load_outages("outages.json")

    with pytest.raises(NotImplementedError, match="load_pedestrian_network"):
        m.load_pedestrian_network()

    with pytest.raises(NotImplementedError, match="compute_reliability"):
        m.compute_reliability({}, {}, TimeWindow(days=30))

    with pytest.raises(NotImplementedError, match="export_station_metrics"):
        m.export_station_metrics({}, ExportTarget(format="csv", output_path=Path("stations.csv")))

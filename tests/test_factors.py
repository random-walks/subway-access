"""Tests for the composable factor pipeline."""

from __future__ import annotations

import pytest

from subway_access.factors import (
    CoverageFactor,
    Factor,
    FactorContext,
    GapScoreFactor,
    NearestStationDistanceFactor,
    NearestStationTravelMinutesFactor,
    NeedScoreFactor,
    Pipeline,
    StationCountFactor,
)
from subway_access.models import (
    AccessibilityLabel,
    CatchmentDataset,
    CatchmentFeature,
    Station,
    StationDataset,
    TractDemographics,
)


def _make_station(
    station_id: str = "S1",
    name: str = "Test Station",
    latitude: float = 40.75,
    longitude: float = -73.99,
    ada_status: AccessibilityLabel = "accessible",
) -> Station:
    return Station(
        station_id=station_id,
        name=name,
        borough="Manhattan",
        latitude=latitude,
        longitude=longitude,
        ada_status=ada_status,
    )


def _make_tract(
    tract_id: str = "T1",
    latitude: float = 40.751,
    longitude: float = -73.991,
    disability_rate: float = 0.10,
    senior_rate: float = 0.15,
    poverty_rate: float = 0.20,
) -> TractDemographics:
    return TractDemographics(
        tract_id=tract_id,
        tract_name=f"Tract {tract_id}",
        borough="Manhattan",
        centroid_latitude=latitude,
        centroid_longitude=longitude,
        disability_rate=disability_rate,
        senior_rate=senior_rate,
        poverty_rate=poverty_rate,
        total_population=5000,
    )


def _make_catchment(station: Station, radius_meters: float = 800.0) -> CatchmentFeature:
    return CatchmentFeature(
        station_id=station.station_id,
        station_name=station.name,
        borough=station.borough,
        ada_status=station.ada_status,
        center_latitude=station.latitude,
        center_longitude=station.longitude,
        radius_meters=radius_meters,
        minutes=10,
        method="euclidean-buffer-v0.2",
        polygon=(),
    )


def _make_context(
    tract: TractDemographics | None = None,
    stations: tuple[Station, ...] | None = None,
    catchments: tuple[CatchmentFeature, ...] | None = None,
) -> FactorContext:
    station_list = stations or (_make_station(),)
    catchment_list = catchments or tuple(_make_catchment(s) for s in station_list)
    return FactorContext(
        tract=tract or _make_tract(),
        stations=StationDataset(stations=station_list),
        catchments=CatchmentDataset(features=catchment_list),
    )


class TestNeedScoreFactor:
    def test_default_equal_weights(self) -> None:
        ctx = _make_context(
            tract=_make_tract(disability_rate=0.10, senior_rate=0.20, poverty_rate=0.30)
        )
        result = NeedScoreFactor().compute(ctx)
        assert result == pytest.approx(0.20)

    def test_custom_weights(self) -> None:
        ctx = _make_context(
            tract=_make_tract(disability_rate=1.0, senior_rate=0.0, poverty_rate=0.0)
        )
        result = NeedScoreFactor(weights={"disability": 1.0}).compute(ctx)
        assert result == pytest.approx(1.0)

    def test_invalid_weight_key(self) -> None:
        with pytest.raises(ValueError, match="Invalid weight keys"):
            NeedScoreFactor(weights={"invalid": 1.0})


class TestCoverageFactor:
    def test_covered_tract(self) -> None:
        ctx = _make_context()
        assert CoverageFactor().compute(ctx) is True

    def test_uncovered_tract(self) -> None:
        # Place tract far from station
        ctx = _make_context(tract=_make_tract(latitude=41.0, longitude=-74.5))
        assert CoverageFactor().compute(ctx) is False

    def test_not_accessible_station(self) -> None:
        station = _make_station(ada_status="not_accessible")
        ctx = _make_context(stations=(station,))
        assert CoverageFactor().compute(ctx) is False


class TestGapScoreFactor:
    def test_covered_returns_zero(self) -> None:
        ctx = _make_context()
        assert GapScoreFactor().compute(ctx) == 0.0

    def test_uncovered_returns_need_score(self) -> None:
        ctx = _make_context(tract=_make_tract(latitude=41.0, longitude=-74.5))
        result = GapScoreFactor().compute(ctx)
        assert result == pytest.approx(0.15)


class TestNearestStationDistanceFactor:
    def test_nearby_station(self) -> None:
        ctx = _make_context()
        result = NearestStationDistanceFactor().compute(ctx)
        assert 0.0 < result < 500.0

    def test_no_accessible_stations(self) -> None:
        station = _make_station(ada_status="not_accessible")
        ctx = _make_context(stations=(station,))
        assert NearestStationDistanceFactor().compute(ctx) == -1.0


class TestNearestStationTravelMinutesFactor:
    def test_nearby_station(self) -> None:
        ctx = _make_context()
        result = NearestStationTravelMinutesFactor().compute(ctx)
        assert 0.0 < result < 10.0

    def test_no_accessible_stations(self) -> None:
        station = _make_station(ada_status="not_accessible")
        ctx = _make_context(stations=(station,))
        assert NearestStationTravelMinutesFactor().compute(ctx) == -1.0


class TestStationCountFactor:
    def test_one_covering_station(self) -> None:
        ctx = _make_context()
        assert StationCountFactor().compute(ctx) == 1

    def test_multiple_covering_stations(self) -> None:
        s1 = _make_station(station_id="S1", latitude=40.750)
        s2 = _make_station(station_id="S2", latitude=40.751)
        ctx = _make_context(stations=(s1, s2))
        assert StationCountFactor().compute(ctx) == 2

    def test_no_covering_stations(self) -> None:
        ctx = _make_context(tract=_make_tract(latitude=41.0, longitude=-74.5))
        assert StationCountFactor().compute(ctx) == 0


class TestPipeline:
    def test_empty_pipeline(self) -> None:
        result = Pipeline().run([_make_context()])
        assert result.tract_ids == ("T1",)
        assert result.columns == {}

    def test_single_factor(self) -> None:
        pipe = Pipeline().add(NeedScoreFactor())
        result = pipe.run([_make_context()])
        assert "need_score" in result.columns
        assert len(result.columns["need_score"]) == 1

    def test_multiple_factors(self) -> None:
        pipe = (
            Pipeline()
            .add(NeedScoreFactor())
            .add(CoverageFactor())
            .add(StationCountFactor())
        )
        ctx1 = _make_context(tract=_make_tract(tract_id="T1"))
        ctx2 = _make_context(
            tract=_make_tract(tract_id="T2", latitude=41.0, longitude=-74.5)
        )
        result = pipe.run([ctx1, ctx2])
        assert result.tract_ids == ("T1", "T2")
        assert len(result.columns) == 3
        assert result.columns["has_accessible_station"] == (True, False)

    def test_immutability(self) -> None:
        pipe1 = Pipeline()
        pipe2 = pipe1.add(NeedScoreFactor())
        assert len(pipe1.factors) == 0
        assert len(pipe2.factors) == 1

    def test_to_records(self) -> None:
        pipe = Pipeline().add(NeedScoreFactor())
        result = pipe.run([_make_context()])
        records = result.to_records()
        assert len(records) == 1
        assert records[0]["tract_id"] == "T1"
        assert "need_score" in records[0]


class TestCustomFactor:
    def test_user_defined_factor(self) -> None:
        class PopulationFactor(Factor):
            name = "population"
            dtype = "int"

            def compute(self, context: FactorContext) -> int:
                return context.tract.total_population

        pipe = Pipeline().add(PopulationFactor())
        result = pipe.run([_make_context()])
        assert result.columns["population"] == (5000,)

    def test_factor_with_external_data(self) -> None:
        class RentFactor(Factor):
            name = "median_rent"
            dtype = "float"

            def __init__(self, rents: dict[str, float]) -> None:
                self._rents = rents

            def compute(self, context: FactorContext) -> float:
                return self._rents.get(context.tract.tract_id, 0.0)

        rents = {"T1": 2500.0, "T2": 1800.0}
        pipe = Pipeline().add(RentFactor(rents))
        ctx = _make_context(tract=_make_tract(tract_id="T1"))
        result = pipe.run([ctx])
        assert result.columns["median_rent"] == (2500.0,)

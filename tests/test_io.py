from __future__ import annotations

import email.message
import json
import urllib.error
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from subway_access.io import (
    load_accessibility_status,
    load_census_data,
    load_gtfs,
    load_outages,
    load_pedestrian_network,
)
from subway_access.io._mta import _read_json
from tests.test_helpers import TEST_DATA_DIR

_TEST_URL = "https://example.com/data.json"


def _fake_http_error(code: int, message: str) -> urllib.error.HTTPError:
    """Build an ``HTTPError`` with the headers arg mypy actually likes."""
    return urllib.error.HTTPError(
        _TEST_URL, code, message, email.message.Message(), None
    )


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


class _FakeHTTPResponse:
    """Minimal stand-in for ``http.client.HTTPResponse`` used by ``urlopen``."""

    def __init__(self, payload: bytes) -> None:
        self._buffer = BytesIO(payload)

    def read(self) -> bytes:
        return self._buffer.read()

    def __enter__(self):
        return self

    def __exit__(self, *_exc: object) -> None:
        self._buffer.close()


class TestReadJsonRetry:
    """`_read_json` must retry transient failures with exponential backoff.

    MTA OpenData (``data.ny.gov``) occasionally returns 5xx or times out
    under load. A single hiccup should not kill a fetch — the library must
    retry before propagating the error.
    """

    def test_succeeds_on_first_attempt(self) -> None:
        payload = json.dumps([{"station_id": "S1"}]).encode("utf-8")
        with patch(
            "subway_access.io._mta.urlopen",
            return_value=_FakeHTTPResponse(payload),
        ) as mock_urlopen:
            result = _read_json(_TEST_URL)
        assert result == [{"station_id": "S1"}]
        assert mock_urlopen.call_count == 1

    def test_retries_on_http_5xx_then_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        payload = json.dumps([{"station_id": "S1"}]).encode("utf-8")
        sequence = iter(
            [
                _fake_http_error(503, "Service Unavailable"),
                _FakeHTTPResponse(payload),
            ]
        )

        def fake_urlopen(*_args: object, **_kwargs: object) -> Any:
            item = next(sequence)
            if isinstance(item, BaseException):
                raise item
            return item

        monkeypatch.setattr("subway_access.io._mta.urlopen", fake_urlopen)
        monkeypatch.setattr("subway_access.io._mta.time.sleep", lambda _: None)

        result = _read_json(_TEST_URL, attempts=3, initial_backoff_seconds=0.0)
        assert result == [{"station_id": "S1"}]

    def test_retries_on_timeout_then_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        payload = json.dumps([{"station_id": "S1"}]).encode("utf-8")
        sequence = iter(
            [
                TimeoutError("read timeout"),
                _FakeHTTPResponse(payload),
            ]
        )

        def fake_urlopen(*_args: object, **_kwargs: object) -> Any:
            item = next(sequence)
            if isinstance(item, BaseException):
                raise item
            return item

        monkeypatch.setattr("subway_access.io._mta.urlopen", fake_urlopen)
        monkeypatch.setattr("subway_access.io._mta.time.sleep", lambda _: None)

        result = _read_json(_TEST_URL, attempts=3, initial_backoff_seconds=0.0)
        assert result == [{"station_id": "S1"}]

    def test_does_not_retry_on_http_4xx(self, monkeypatch: pytest.MonkeyPatch) -> None:
        call_count = 0

        def fake_urlopen(*_args: object, **_kwargs: object) -> Any:
            nonlocal call_count
            call_count += 1
            raise _fake_http_error(404, "Not Found")

        monkeypatch.setattr("subway_access.io._mta.urlopen", fake_urlopen)

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _read_json(_TEST_URL, attempts=3, initial_backoff_seconds=0.0)
        # 4xx is deterministic — exactly one attempt.
        assert call_count == 1
        assert exc_info.value.code == 404

    def test_raises_after_exhausting_retries(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        call_count = 0

        def fake_urlopen(*_args: object, **_kwargs: object) -> Any:
            nonlocal call_count
            call_count += 1
            raise _fake_http_error(503, "Service Unavailable")

        monkeypatch.setattr("subway_access.io._mta.urlopen", fake_urlopen)
        monkeypatch.setattr("subway_access.io._mta.time.sleep", lambda _: None)

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _read_json(_TEST_URL, attempts=3, initial_backoff_seconds=0.0)
        assert call_count == 3
        assert exc_info.value.code == 503

    def test_rejects_zero_attempts(self) -> None:
        with pytest.raises(ValueError, match=r"attempts must be >= 1"):
            _read_json(_TEST_URL, attempts=0)


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

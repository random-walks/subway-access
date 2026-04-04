from __future__ import annotations

import os
from pathlib import Path

import pytest

from subway_access.cli import main
from tests.helpers import TEST_DATA_DIR


def test_cli_analyze_snapshot_writes_outputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "analyze-snapshot",
            "--cache-dir",
            str(TEST_DATA_DIR),
            "--output-dir",
            str(tmp_path),
            "--minutes",
            "10",
            "--reliability-window-days",
            "365",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (tmp_path / "catchments.geojson").exists()
    assert (tmp_path / "accessibility-gaps.csv").exists()
    assert (tmp_path / "station-metrics.csv").exists()
    assert "Generated subway-access snapshot outputs" in captured.out


def test_cli_rejects_non_positive_minutes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "analyze-snapshot",
                "--cache-dir",
                str(TEST_DATA_DIR),
                "--output-dir",
                str(tmp_path),
                "--minutes",
                "0",
            ]
        )
    captured = capsys.readouterr()

    assert exc_info.value.code == 2
    assert "must be greater than zero" in captured.err


@pytest.mark.skipif(
    os.getenv("SUBWAY_ACCESS_RUN_LIVE") != "1",
    reason="live snapshot fetch is skipped unless SUBWAY_ACCESS_RUN_LIVE=1",
)
def test_cli_fetch_snapshot_live(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        [
            "fetch-snapshot",
            "--geography",
            "borough",
            "--value",
            "Manhattan",
            "--cache-dir",
            str(tmp_path),
            "--availability-months",
            "1",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (tmp_path / "stations.csv").exists()
    assert (tmp_path / "accessibility.csv").exists()
    assert (tmp_path / "tracts.geojson").exists()
    assert "Fetched subway-access real-data snapshot" in captured.out

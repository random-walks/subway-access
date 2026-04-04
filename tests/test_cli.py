from __future__ import annotations

from pathlib import Path

import pytest

from subway_access.cli import main


def test_cli_demo_writes_outputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "demo",
            "--output-dir",
            str(tmp_path),
            "--minutes",
            "10",
            "--reliability-window-days",
            "30",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (tmp_path / "catchments.geojson").exists()
    assert (tmp_path / "accessibility-gaps.csv").exists()
    assert (tmp_path / "station-metrics.csv").exists()
    assert "Generated subway-access demo outputs" in captured.out


def test_cli_rejects_non_positive_minutes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["demo", "--output-dir", str(tmp_path), "--minutes", "0"])
    captured = capsys.readouterr()

    assert exc_info.value.code == 2
    assert "must be greater than zero" in captured.err


def test_cli_rejects_invalid_reliability_window(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "demo",
                "--output-dir",
                str(tmp_path),
                "--minutes",
                "10",
                "--reliability-window-days",
                "0",
            ]
        )
    captured = capsys.readouterr()

    assert exc_info.value.code == 2
    assert "TimeWindow.days must be greater than zero" in captured.err

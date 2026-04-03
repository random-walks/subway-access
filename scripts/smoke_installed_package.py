from __future__ import annotations

import importlib.resources
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import subway_access


def main() -> None:
    typing_marker = importlib.resources.files("subway_access").joinpath("py.typed")
    if not typing_marker.is_file():
        raise SystemExit("Installed package is missing `subway_access/py.typed`.")

    cli_candidates = [
        Path(sys.executable).with_name("subway-access.exe"),
        Path(sys.executable).with_name("subway-access"),
    ]
    fallback_cli = shutil.which("subway-access")
    if fallback_cli is not None:
        cli_candidates.append(Path(fallback_cli))
    cli_path = next(
        (candidate for candidate in cli_candidates if candidate.exists()),
        cli_candidates[0],
    )
    if not cli_path.exists():
        raise SystemExit(
            "Installed package is missing the `subway-access` console script."
        )

    subprocess.run([str(cli_path), "--help"], check=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "demo-output"
        subprocess.run(
            [str(cli_path), "demo", "--output-dir", str(output_dir), "--minutes", "10"],
            check=True,
        )
        catchments_path = output_dir / "catchments.geojson"
        gaps_path = output_dir / "accessibility-gaps.csv"
        if not catchments_path.is_file() or not gaps_path.is_file():
            raise SystemExit(
                "Installed package could not generate the expected demo output files."
            )

    version = subway_access.__version__
    if not isinstance(version, str) or not version:
        raise SystemExit("Installed package did not expose a valid version string.")


if __name__ == "__main__":
    main()

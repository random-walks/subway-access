from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

EXAMPLE_TITLE = "subway-access Example Template"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=EXAMPLE_TITLE)
    parser.add_argument(
        "--no-publish-report",
        action="store_true",
        help="Skip writing the tracked tearsheet and figure.",
    )
    return parser


def _write_figure() -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / "example-workflow.png"
    figure, axes = plt.subplots(figsize=(8, 5))
    axes.bar(
        ["Cache", "Analyze", "Report"],
        [1.0, 1.0, 1.0],
        color=["#4c78a8", "#f58518", "#72b7b2"],
    )
    axes.set_title("Example contract: three tracked steps")
    axes.set_ylabel("Relative emphasis (schematic)")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def _write_report(figure: Path) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / "example-template-tearsheet.md"
    path.write_text(
        "\n".join(
            [
                "# Example Template Tearsheet",
                "",
                "Bootstrap folder for new `subway-access` examples. Copy this directory,",
                "rename it, wire `main.py` to real cache-backed workflows, and keep at",
                "least one chart under `reports/figures/` so GitHub readers see a visual",
                "hook without running the script.",
                "",
                "## Figure",
                "",
                f"![Workflow schematic](./figures/{figure.name})",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def main() -> None:
    args = build_parser().parse_args()
    print(EXAMPLE_TITLE)
    print("Copy this folder to start a new tracked example.")
    if args.no_publish_report:
        print("Skipped tracked report (--no-publish-report).")
        return
    figure_path = _write_figure()
    report_path = _write_report(figure_path)
    print(f"Wrote tracked figure: {figure_path}")
    print(f"Wrote tracked report: {report_path}")


if __name__ == "__main__":
    main()

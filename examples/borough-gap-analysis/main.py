from __future__ import annotations

import argparse
import csv
from pathlib import Path

from subway_access import analysis, export, models, pipeline

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"
ARTIFACTS_DIR = ROOT / "artifacts"
REPORTS_DIR = ROOT / "reports"


def cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / name


def artifact_path(name: str) -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACTS_DIR / name


def report_path(name: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR / name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run borough-scale accessibility gap analysis on official cached data.",
    )
    parser.add_argument("--geography", default="borough")
    parser.add_argument("--value", default="Manhattan")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=cache_path("manhattan-snapshot"),
    )
    parser.add_argument("--availability-months", type=int, default=12)
    parser.add_argument("--minutes", type=int, default=10)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--publish-report", action="store_true")
    return parser


def write_report(
    query: models.AccessibilityQuery,
    gaps: models.GapAnalysis,
    output_csv: Path,
) -> Path:
    top_gap = gaps.records[0]
    report = f"""# Borough Gap Analysis Tearsheet

## Query

- Geography: `{query.geography}`
- Value: `{query.value}`

## Snapshot

- Tracts scored: {len(gaps.records)}
- Highest gap score: {top_gap.gap_score:.4f}
- Top gap tract: `{top_gap.tract_id}` ({top_gap.tract_name})
- Nearest accessible station: {top_gap.nearest_accessible_station_name}

## Artifact

- Gap CSV: `{output_csv.name}`
"""
    tearsheet_path = report_path("borough-gap-analysis-tearsheet.md")
    tearsheet_path.write_text(report, encoding="utf-8")
    return tearsheet_path


def main() -> None:
    args = build_parser().parse_args()
    query = models.AccessibilityQuery(geography=args.geography, value=args.value)
    snapshot = pipeline.fetch_study_area_snapshot(
        query,
        cache_dir=args.cache_dir,
        refresh=args.refresh,
        availability_months=args.availability_months,
    )
    catchments = analysis.generate_catchments(
        snapshot.stations,
        models.CatchmentRequest(minutes=args.minutes),
    )
    scores = analysis.score_accessibility(
        snapshot.stations,
        catchments,
        snapshot.demographics,
    )
    gaps = analysis.analyze_gaps(scores)

    catchments_path = export.export_catchments_geojson(
        catchments,
        models.ExportTarget("geojson", artifact_path("catchments.geojson")),
    )
    gaps_path = export.export_gap_table(
        gaps,
        models.ExportTarget("csv", artifact_path("borough-accessibility-gaps.csv")),
    )
    report_file: Path | None = None
    if args.publish_report:
        report_file = write_report(query, gaps, gaps_path)

    print("Borough Gap Analysis")
    print("--------------------")
    print(f"Study area: {query.geography}={query.value}")
    print(f"Wrote {catchments_path}")
    print(f"Wrote {gaps_path}")
    if report_file is None:
        print("Skipped tracked report generation. Re-run with --publish-report to update reports/.")
    else:
        print(f"Wrote tracked report: {report_file}")


if __name__ == "__main__":
    main()

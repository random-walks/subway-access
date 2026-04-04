from __future__ import annotations

import csv
from pathlib import Path

from subway_access import analysis, models, samples

ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = ROOT / "artifacts"
REPORTS_DIR = ROOT / "reports"


def artifact_path(filename: str) -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACTS_DIR / filename


def report_path(filename: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR / filename


def main() -> None:
    query = models.AccessibilityQuery(geography="borough", value="Manhattan")
    stations = samples.load_sample_stations().with_accessibility(
        samples.load_sample_accessibility()
    )
    demographics = samples.load_sample_demographics()
    catchments = analysis.generate_catchments(
        stations,
        models.CatchmentRequest(minutes=10),
    )
    scores = analysis.score_accessibility(stations, catchments, demographics)
    gaps = analysis.analyze_gaps(scores)
    borough_gaps = [record for record in gaps.records if record.borough == query.value]

    csv_path = artifact_path("manhattan-accessibility-gaps.csv")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "tract_id",
                "tract_name",
                "gap_score",
                "gap_label",
                "nearest_accessible_station_name",
            ],
        )
        writer.writeheader()
        for record in borough_gaps:
            writer.writerow(
                {
                    "tract_id": record.tract_id,
                    "tract_name": record.tract_name,
                    "gap_score": f"{record.gap_score:.4f}",
                    "gap_label": record.gap_label,
                    "nearest_accessible_station_name": record.nearest_accessible_station_name
                    or "",
                }
            )

    uncovered = [record for record in borough_gaps if record.gap_label == "gap"]
    report = f"""# Borough Gap Analysis Tearsheet

## Query

- Geography: `{query.geography}`
- Value: `{query.value}`

## Coverage Snapshot

- Tracts in borough slice: {len(borough_gaps)}
- Uncovered tracts: {len(uncovered)}
- Highest gap score: {borough_gaps[0].gap_score:.4f}

## Top Borough Gap

- Tract: `{borough_gaps[0].tract_id}` ({borough_gaps[0].tract_name})
- Nearest accessible station: {borough_gaps[0].nearest_accessible_station_name}

## Artifact

- CSV export: `{csv_path.name}`
"""
    tearsheet_path = report_path("borough-gap-analysis-tearsheet.md")
    tearsheet_path.write_text(report, encoding="utf-8")

    print(f"Wrote {csv_path}")
    print(f"Wrote {tearsheet_path}")


if __name__ == "__main__":
    main()

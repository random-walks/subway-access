from __future__ import annotations

from pathlib import Path

from subway_access import analysis, export, models, samples

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
    stations = samples.load_sample_stations().with_accessibility(
        samples.load_sample_accessibility()
    )
    demographics = samples.load_sample_demographics()
    outages = samples.load_sample_outages()
    pedestrian_network = samples.load_sample_pedestrian_network()

    catchments = analysis.generate_catchments(
        stations,
        models.CatchmentRequest(minutes=10),
    )
    scores = analysis.score_accessibility(stations, catchments, demographics)
    gaps = analysis.analyze_gaps(scores)
    reliability = analysis.compute_reliability(
        stations,
        outages,
        models.TimeWindow(days=30),
    )
    station_metrics = analysis.build_station_metrics(
        stations,
        catchments,
        scores,
        reliability=reliability,
        pedestrian_network=pedestrian_network,
    )

    catchments_path = export.export_catchments_geojson(
        catchments,
        models.ExportTarget("geojson", artifact_path("catchments.geojson")),
    )
    gaps_path = export.export_gap_table(
        gaps,
        models.ExportTarget("csv", artifact_path("accessibility-gaps.csv")),
    )
    station_metrics_path = export.export_station_metrics(
        station_metrics,
        models.ExportTarget("csv", artifact_path("station-metrics.csv")),
    )

    top_gap = gaps.records[0]
    strongest_station = max(
        station_metrics.records,
        key=lambda record: (record.covered_population, record.station_id),
    )
    report = f"""# Quickstart Demo Tearsheet

## Summary

- Stations processed: {len(stations.stations)}
- Tracts scored: {len(scores.records)}
- Outage events loaded: {len(outages.records)}
- Pedestrian connections loaded: {len(pedestrian_network.connections)}

## Top Gap

- Tract: `{top_gap.tract_id}` ({top_gap.tract_name})
- Gap score: {top_gap.gap_score:.4f}
- Nearest accessible station: {top_gap.nearest_accessible_station_name}

## Strongest Coverage

- Station: `{strongest_station.station_id}` ({strongest_station.station_name})
- Covered population: {strongest_station.covered_population}
- Reliability label: {strongest_station.reliability_label}

## Artifacts

- Catchments GeoJSON: `{catchments_path.name}`
- Gap CSV: `{gaps_path.name}`
- Station metrics CSV: `{station_metrics_path.name}`
"""
    tearsheet_path = report_path("quickstart-demo-tearsheet.md")
    tearsheet_path.write_text(report, encoding="utf-8")

    print(f"Wrote {catchments_path}")
    print(f"Wrote {gaps_path}")
    print(f"Wrote {station_metrics_path}")
    print(f"Wrote {tearsheet_path}")


if __name__ == "__main__":
    main()

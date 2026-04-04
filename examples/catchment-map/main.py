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
    station_metrics_path = export.export_station_metrics(
        station_metrics,
        models.ExportTarget("geojson", artifact_path("station-metrics.geojson")),
    )

    report = f"""# Catchment Map Tearsheet

## Output Summary

- Catchment polygons: {len(catchments.features)}
- Station metric points: {len(station_metrics.records)}
- Stations with network links: {sum(1 for record in station_metrics.records if record.network_connection_count > 0)}

## Suggested Styling

- Style `catchments.geojson` polygons by `ada_status`
- Style `station-metrics.geojson` points by `reliability_label`
- Use `covered_population` for graduated point sizing

## Artifacts

- Catchments: `{catchments_path.name}`
- Station metrics: `{station_metrics_path.name}`
"""
    tearsheet_path = report_path("catchment-map-tearsheet.md")
    tearsheet_path.write_text(report, encoding="utf-8")

    print(f"Wrote {catchments_path}")
    print(f"Wrote {station_metrics_path}")
    print(f"Wrote {tearsheet_path}")


if __name__ == "__main__":
    main()

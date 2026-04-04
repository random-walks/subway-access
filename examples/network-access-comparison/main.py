from __future__ import annotations

import argparse
import csv
from pathlib import Path

import networkx as nx
import osmnx as ox
from nyc_geo_toolkit import load_nyc_boundaries
from shapely.geometry import shape
from shapely.ops import unary_union

from subway_access import analysis, models, pipeline

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"
ARTIFACTS_DIR = ROOT / "artifacts"
REPORTS_DIR = ROOT / "reports"
METERS_PER_MINUTE = 80.0


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
        description="Compare Euclidean and OSM walk access for a real subway study area.",
    )
    parser.add_argument("--geography", default="community_district")
    parser.add_argument("--value", default="Manhattan 03")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=cache_path("manhattan-03-snapshot"),
    )
    parser.add_argument("--availability-months", type=int, default=12)
    parser.add_argument("--minutes", type=int, default=10)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--publish-report", action="store_true")
    return parser


def _study_area_shape(query: models.AccessibilityQuery):
    boundaries = load_nyc_boundaries(query.geography, values=query.value)
    return unary_union([shape(feature.geometry) for feature in boundaries.features])


def _nearest_network_minutes(
    graph: nx.MultiDiGraph,
    *,
    tract: models.TractDemographics,
    accessible_stations: tuple[models.Station, ...],
    station_nodes: dict[str, int],
) -> tuple[float | None, str | None]:
    tract_node = ox.distance.nearest_nodes(
        graph,
        X=tract.centroid_longitude,
        Y=tract.centroid_latitude,
    )
    best_minutes: float | None = None
    best_station_id: str | None = None
    for station in accessible_stations:
        try:
            length = nx.shortest_path_length(
                graph,
                tract_node,
                station_nodes[station.station_id],
                weight="length",
            )
        except (nx.NetworkXNoPath, KeyError):
            continue
        minutes = float(length) / METERS_PER_MINUTE
        if best_minutes is None or minutes < best_minutes:
            best_minutes = minutes
            best_station_id = station.station_id
    return best_minutes, best_station_id


def write_report(rows: list[dict[str, str]], output_csv: Path) -> Path:
    network_gaps = sum(1 for row in rows if row["network_has_access"] == "false")
    euclidean_gaps = sum(1 for row in rows if row["euclidean_has_access"] == "false")
    report = f"""# Network Access Comparison Tearsheet

## Summary

- Tracts compared: {len(rows)}
- Euclidean uncovered tracts: {euclidean_gaps}
- Network uncovered tracts: {network_gaps}

## Artifact

- Comparison CSV: `{output_csv.name}`
"""
    output_path = report_path("network-access-comparison-tearsheet.md")
    output_path.write_text(report, encoding="utf-8")
    return output_path


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
    score_by_tract = {record.tract_id: record for record in scores.records}

    graph = ox.graph_from_polygon(
        _study_area_shape(query), network_type="walk", simplify=True
    )
    accessible_stations = snapshot.stations.accessible_stations
    station_nodes = {
        station.station_id: ox.distance.nearest_nodes(
            graph,
            X=station.longitude,
            Y=station.latitude,
        )
        for station in accessible_stations
    }

    rows = []
    for tract in snapshot.demographics.tracts:
        network_minutes, network_station_id = _nearest_network_minutes(
            graph,
            tract=tract,
            accessible_stations=accessible_stations,
            station_nodes=station_nodes,
        )
        euclidean_record = score_by_tract[tract.tract_id]
        rows.append(
            {
                "tract_id": tract.tract_id,
                "tract_name": tract.tract_name,
                "euclidean_has_access": str(
                    euclidean_record.has_accessible_station
                ).lower(),
                "network_has_access": str(
                    network_minutes is not None and network_minutes <= args.minutes
                ).lower(),
                "euclidean_station_id": euclidean_record.nearest_accessible_station_id
                or "",
                "network_station_id": network_station_id or "",
                "network_minutes": ""
                if network_minutes is None
                else f"{network_minutes:.2f}",
            }
        )

    output_csv = artifact_path("network-access-comparison.csv")
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    report_file: Path | None = None
    if args.publish_report:
        report_file = write_report(rows, output_csv)

    print("Network Access Comparison")
    print("-------------------------")
    print(f"Study area: {query.geography}={query.value}")
    print(f"Wrote {output_csv}")
    if report_file is None:
        print(
            "Skipped tracked report generation. Re-run with --publish-report to update reports/."
        )
    else:
        print(f"Wrote tracked report: {report_file}")


if __name__ == "__main__":
    main()

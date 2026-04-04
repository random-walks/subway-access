"""Exporters for ``subway-access`` outputs."""

from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from ..models import (
        CatchmentDataset,
        ExportTarget,
        GapAnalysis,
        StationMetricDataset,
        StationMetricRecord,
    )


def _validate_target_format(
    target: ExportTarget,
    *,
    expected_formats: tuple[str, ...],
) -> Path:
    output_format = target.format.lower()
    if output_format not in expected_formats:
        message = (
            f"Expected export target format in {expected_formats!r}, "
            f"got {target.format!r}."
        )
        raise ValueError(message)
    output_path = target.output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def export_catchments_geojson(data: CatchmentDataset, target: ExportTarget) -> Path:
    """Export station catchments to GeoJSON for mapping workflows."""

    output_path = _validate_target_format(target, expected_formats=("geojson",))
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "station_id": feature.station_id,
                    "station_name": feature.station_name,
                    "borough": feature.borough,
                    "ada_status": feature.ada_status,
                    "radius_meters": round(feature.radius_meters, 3),
                    "minutes": feature.minutes,
                    "method": feature.method,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[list(point) for point in feature.polygon]],
                },
            }
            for feature in data.features
        ],
    }
    output_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    return output_path


def export_gap_table(data: GapAnalysis, target: ExportTarget) -> Path:
    """Export tract-level accessibility gap tables."""

    output_path = _validate_target_format(target, expected_formats=("csv",))
    fieldnames = [
        "tract_id",
        "tract_name",
        "borough",
        "disability_rate",
        "senior_rate",
        "poverty_rate",
        "total_population",
        "need_score",
        "has_accessible_station",
        "accessible_station_count",
        "nearest_accessible_station_id",
        "nearest_accessible_station_name",
        "nearest_accessible_distance_meters",
        "gap_score",
        "gap_label",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in data.records:
            writer.writerow(
                {
                    "tract_id": record.tract_id,
                    "tract_name": record.tract_name,
                    "borough": record.borough,
                    "disability_rate": f"{record.disability_rate:.4f}",
                    "senior_rate": f"{record.senior_rate:.4f}",
                    "poverty_rate": f"{record.poverty_rate:.4f}",
                    "total_population": record.total_population,
                    "need_score": f"{record.need_score:.4f}",
                    "has_accessible_station": str(
                        record.has_accessible_station
                    ).lower(),
                    "accessible_station_count": record.accessible_station_count,
                    "nearest_accessible_station_id": record.nearest_accessible_station_id
                    or "",
                    "nearest_accessible_station_name": record.nearest_accessible_station_name
                    or "",
                    "nearest_accessible_distance_meters": ""
                    if record.nearest_accessible_distance_meters is None
                    else f"{record.nearest_accessible_distance_meters:.2f}",
                    "gap_score": f"{record.gap_score:.4f}",
                    "gap_label": record.gap_label,
                }
            )
    return output_path


def _station_metric_row(record: StationMetricRecord) -> dict[str, object]:
    return {
        "station_id": record.station_id,
        "station_name": record.station_name,
        "borough": record.borough,
        "latitude": round(record.latitude, 6),
        "longitude": round(record.longitude, 6),
        "ada_status": record.ada_status,
        "catchment_minutes": record.catchment_minutes,
        "catchment_radius_meters": round(record.catchment_radius_meters, 3),
        "covered_tract_count": record.covered_tract_count,
        "covered_population": record.covered_population,
        "nearby_gap_tract_count": record.nearby_gap_tract_count,
        "nearby_gap_population": record.nearby_gap_population,
        "mean_need_score": round(record.mean_need_score, 4),
        "reliability_score": None
        if record.reliability_score is None
        else round(record.reliability_score, 4),
        "reliability_label": record.reliability_label,
        "outage_minutes": record.outage_minutes,
        "network_connection_count": record.network_connection_count,
        "daytime_routes": " ".join(record.daytime_routes),
        "structure": record.structure,
    }


def export_station_metrics(data: StationMetricDataset, target: ExportTarget) -> Path:
    """Export station-level accessibility and reliability metrics."""

    output_path = _validate_target_format(target, expected_formats=("csv", "geojson"))
    rows = [_station_metric_row(record) for record in data.records]

    if target.format.lower() == "csv":
        fieldnames = list(rows[0]) if rows else [
            "station_id",
            "station_name",
            "borough",
            "latitude",
            "longitude",
            "ada_status",
            "catchment_minutes",
            "catchment_radius_meters",
            "covered_tract_count",
            "covered_population",
            "nearby_gap_tract_count",
            "nearby_gap_population",
            "mean_need_score",
            "reliability_score",
            "reliability_label",
            "outage_minutes",
            "network_connection_count",
            "daytime_routes",
            "structure",
        ]
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return output_path

    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": row["station_id"],
                "properties": {
                    key: value
                    for key, value in row.items()
                    if key not in {"latitude", "longitude"}
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [row["longitude"], row["latitude"]],
                },
            }
            for row in rows
        ],
    }
    output_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    return output_path

"""Exporters for real and planned subway-access outputs."""

from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING

from ._not_implemented import planned_surface

if TYPE_CHECKING:
    from pathlib import Path

    from .models import CatchmentDataset, ExportTarget, GapAnalysis


def _validate_target_format(target: ExportTarget, *, expected_format: str) -> Path:
    if target.format.lower() != expected_format:
        message = (
            f"Expected export target format {expected_format!r}, got {target.format!r}."
        )
        raise ValueError(message)

    output_path = target.output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def export_catchments_geojson(data: CatchmentDataset, target: ExportTarget) -> Path:
    """Export station catchments to GeoJSON for mapping workflows."""

    output_path = _validate_target_format(target, expected_format="geojson")
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
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def export_station_metrics(data: object, target: ExportTarget) -> object:
    """Export station-level accessibility and reliability metrics."""
    del data, target
    planned_surface("export_station_metrics()")


def export_gap_table(data: GapAnalysis, target: ExportTarget) -> Path:
    """Export tract- or district-level accessibility gap tables."""

    output_path = _validate_target_format(target, expected_format="csv")
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

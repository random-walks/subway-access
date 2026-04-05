"""Load cached subway entrance / exit GeoJSON snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import Entrance, EntranceDataset


def _parse_daytime_routes(raw: object) -> tuple[str, ...]:
    text = str(raw or "").strip()
    if not text:
        return ()
    return tuple(part for part in text.split() if part.strip())


def load_entrances(source: str | Path) -> EntranceDataset:
    """Load a cached ``entrances.geojson`` FeatureCollection into an ``EntranceDataset``."""

    path = Path(source).expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "FeatureCollection":
        message = f"{path} must be a GeoJSON FeatureCollection."
        raise ValueError(message)

    entrances: list[Entrance] = []
    for feature in payload.get("features", []):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            continue
        geometry = feature.get("geometry")
        properties = feature.get("properties")
        if not isinstance(geometry, dict) or geometry.get("type") != "Point":
            continue
        if not isinstance(properties, dict):
            continue
        coords = geometry.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        complex_id = properties.get("complex_id")
        gtfs_stop_id = properties.get("gtfs_stop_id")
        entrances.append(
            Entrance(
                entrance_id=str(properties.get("entrance_id") or "").strip(),
                station_id=str(properties.get("station_id") or "").strip(),
                latitude=lat,
                longitude=lon,
                stop_name=str(properties.get("stop_name") or "").strip(),
                constituent_station_name=str(
                    properties.get("constituent_station_name") or ""
                ).strip(),
                complex_id=str(complex_id).strip() if complex_id else None,
                gtfs_stop_id=str(gtfs_stop_id).strip() if gtfs_stop_id else None,
                borough_code=str(properties.get("borough") or "").strip(),
                entrance_type=str(properties.get("entrance_type") or "").strip(),
                entry_allowed=bool(properties.get("entry_allowed")),
                exit_allowed=bool(properties.get("exit_allowed")),
                division=_optional_str(properties.get("division")),
                line=_optional_str(properties.get("line")),
                daytime_routes=_parse_daytime_routes(properties.get("daytime_routes")),
                source=str(properties.get("source") or "").strip(),
            )
        )
    return EntranceDataset(entrances=tuple(entrances))


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def entrances_to_geojson(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a GeoJSON FeatureCollection from normalized entrance property dicts."""

    features: list[dict[str, Any]] = []
    for row in rows:
        lat = row.get("latitude")
        lon = row.get("longitude")
        if lat is None or lon is None:
            continue
        props = {
            k: v for k, v in row.items() if k not in ("latitude", "longitude")
        }
        features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(lon), float(lat)],
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}

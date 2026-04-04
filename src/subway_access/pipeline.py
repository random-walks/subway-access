"""High-level real-data pipeline helpers for ``subway-access``."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from nyc_geo_toolkit import (
    boundaries_to_geojson,
    load_nyc_boundaries,
    load_nyc_census_tracts,
)
from shapely.geometry import Point, shape
from shapely.ops import unary_union

from .io import (
    load_accessibility_status,
    load_census_data,
    load_gtfs,
    load_outages,
)
from .io._acs import (
    ACS_5YEAR_YEAR,
    ACS_COUNTS_API_URL,
    ACS_SUBJECT_API_URL,
    fetch_nyc_acs_tract_estimates,
)
from .io._cache import cache_timestamp, ensure_directory, write_csv_rows, write_json
from .io._mta import (
    MTA_ELEVATOR_AVAILABILITY_API_URL,
    MTA_EQUIPMENT_ASSET_API_URL,
    MTA_GTFS_STATIC_URL,
    MTA_SUBWAY_STATIONS_API_URL,
    build_outage_snapshot_rows,
    build_station_snapshot_rows,
    fetch_mta_availability_history,
    fetch_mta_equipment_assets,
    fetch_mta_gtfs_archive,
    fetch_mta_station_catalog,
)
from .models import AccessibilityQuery, DataSourceMetadata, StudyAreaSnapshot

__all__ = [
    "fetch_study_area_snapshot",
    "load_cached_snapshot",
]

_BOROUGH_BY_COUNTY = {
    "005": "Bronx",
    "047": "Brooklyn",
    "061": "Manhattan",
    "081": "Queens",
    "085": "Staten Island",
}


def _first_day_months_ago(months: int) -> date:
    today = datetime.now(tz=timezone.utc).date()
    year = today.year
    month = today.month - months + 1
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def _snapshot_paths(cache_dir: Path) -> dict[str, Path]:
    return {
        "stations": cache_dir / "stations.csv",
        "accessibility": cache_dir / "accessibility.csv",
        "tracts": cache_dir / "tracts.geojson",
        "outages": cache_dir / "outages.json",
        "metadata": cache_dir / "snapshot-metadata.json",
        "boundary": cache_dir / "study-area.geojson",
        "assets": cache_dir / "mta-equipment-assets.json",
        "availability": cache_dir / "mta-availability-history.json",
        "station_catalog": cache_dir / "mta-station-catalog.json",
        "gtfs_archive": cache_dir / "gtfs_subway.zip",
    }


def _require_cached_snapshot(paths: dict[str, Path]) -> None:
    required = ("stations", "accessibility", "tracts", "outages", "metadata")
    missing = [name for name in required if not paths[name].exists()]
    if missing:
        joined = ", ".join(missing)
        message = (
            "Missing cached snapshot files. Run fetch_study_area_snapshot() first: "
            f"{joined}."
        )
        raise FileNotFoundError(message)


def _selected_boundary_geometry(query: AccessibilityQuery) -> tuple[Any, dict[str, Any]]:
    boundaries = load_nyc_boundaries(query.geography, values=query.value)
    boundary_shapes = [shape(feature.geometry) for feature in boundaries.features]
    study_area_shape = unary_union(boundary_shapes)
    return study_area_shape, boundaries_to_geojson(boundaries)


def _filter_station_rows(
    station_catalog_rows: list[dict[str, Any]],
    *,
    study_area_shape: Any,
) -> list[dict[str, Any]]:
    selected_rows = []
    for row in station_catalog_rows:
        longitude = row.get("gtfs_longitude")
        latitude = row.get("gtfs_latitude")
        if longitude is None or latitude is None:
            continue
        point = Point(float(longitude), float(latitude))
        if study_area_shape.covers(point):
            selected_rows.append(row)
    return selected_rows


def _selected_tract_features(
    query: AccessibilityQuery,
    *,
    study_area_shape: Any,
) -> list[Any]:
    tract_boundaries = load_nyc_census_tracts()
    selected_features = []
    for feature in tract_boundaries.features:
        tract_shape = shape(feature.geometry)
        if study_area_shape.covers(tract_shape.centroid):
            selected_features.append(feature)
    if not selected_features:
        message = f"No census tracts intersect the requested study area {query!r}."
        raise ValueError(message)
    return selected_features


def _build_demographic_snapshot_features(
    tract_features: list[Any],
    estimates: dict[str, dict[str, object]],
) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    for feature in tract_features:
        tract_id = feature.geography_value
        estimate = estimates.get(tract_id)
        if estimate is None:
            continue
        centroid = shape(feature.geometry).centroid
        county_code = tract_id[2:5]
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "tract_id": tract_id,
                    "tract_name": str(estimate["tract_name"]),
                    "borough": _BOROUGH_BY_COUNTY.get(county_code, ""),
                    "centroid_latitude": centroid.y,
                    "centroid_longitude": centroid.x,
                    "disability_rate": estimate["disability_rate"],
                    "senior_rate": estimate["senior_rate"],
                    "poverty_rate": estimate["poverty_rate"],
                    "population": estimate["total_population"],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [centroid.x, centroid.y],
                },
            }
        )
    return features


def _load_metadata(
    path: Path,
) -> tuple[AccessibilityQuery, tuple[DataSourceMetadata, ...]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    query_payload = payload["query"]
    metadata_rows = [
        DataSourceMetadata(
            name=row["name"],
            source_url=row["source_url"],
            cache_path=Path(row["cache_path"]),
            refreshed_at=datetime.fromisoformat(row["refreshed_at"]),
            record_count=int(row["record_count"]),
            notes=row.get("notes", ""),
        )
        for row in payload["sources"]
    ]
    return (
        AccessibilityQuery(
            geography=query_payload["geography"],
            value=query_payload["value"],
        ),
        tuple(metadata_rows),
    )


def load_cached_snapshot(cache_dir: str | Path) -> StudyAreaSnapshot:
    """Load a previously fetched real-data study-area snapshot."""

    cache_root = Path(cache_dir).expanduser().resolve()
    paths = _snapshot_paths(cache_root)
    _require_cached_snapshot(paths)
    query, metadata = _load_metadata(paths["metadata"])
    accessibility = load_accessibility_status(paths["accessibility"])
    stations = load_gtfs(paths["stations"]).with_accessibility(accessibility)
    demographics = load_census_data(paths["tracts"])
    outages = load_outages(paths["outages"])
    return StudyAreaSnapshot(
        query=query,
        stations=stations,
        accessibility=accessibility,
        demographics=demographics,
        outages=outages,
        metadata=metadata,
    )


def fetch_study_area_snapshot(
    query: AccessibilityQuery,
    *,
    cache_dir: str | Path,
    refresh: bool = False,
    availability_months: int = 12,
    include_gtfs_archive: bool = True,
) -> StudyAreaSnapshot:
    """Fetch, cache, and load a real-data study-area snapshot."""

    cache_root = ensure_directory(Path(cache_dir).expanduser().resolve())
    paths = _snapshot_paths(cache_root)
    if (
        not refresh
        and paths["stations"].exists()
        and paths["accessibility"].exists()
        and paths["tracts"].exists()
        and paths["outages"].exists()
        and paths["metadata"].exists()
    ):
        return load_cached_snapshot(cache_root)

    refreshed_at = cache_timestamp()
    study_area_shape, boundary_geojson = _selected_boundary_geometry(query)
    write_json(paths["boundary"], boundary_geojson)

    station_catalog_rows = fetch_mta_station_catalog()
    write_json(paths["station_catalog"], station_catalog_rows)
    selected_station_rows = _filter_station_rows(
        station_catalog_rows,
        study_area_shape=study_area_shape,
    )
    station_rows, accessibility_rows = build_station_snapshot_rows(selected_station_rows)
    write_csv_rows(
        paths["stations"],
        [dict(row) for row in station_rows],
    )
    write_csv_rows(
        paths["accessibility"],
        [dict(row) for row in accessibility_rows],
    )

    station_complex_ids = tuple(
        sorted(
            {
                str(row["complex_id"])
                for row in station_rows
                if row.get("complex_id")
            }
        )
    )
    asset_rows = fetch_mta_equipment_assets(station_complex_ids=station_complex_ids)
    write_json(paths["assets"], asset_rows)

    start_month = _first_day_months_ago(availability_months)
    availability_rows = fetch_mta_availability_history(
        station_complex_ids=station_complex_ids,
        start_month=start_month,
    )
    write_json(paths["availability"], availability_rows)
    write_json(paths["outages"], build_outage_snapshot_rows(availability_rows))

    if include_gtfs_archive:
        fetch_mta_gtfs_archive(paths["gtfs_archive"], refresh=refresh)

    tract_features = _selected_tract_features(query, study_area_shape=study_area_shape)
    tract_geoids = tuple(feature.geography_value for feature in tract_features)
    acs_estimates = fetch_nyc_acs_tract_estimates(tract_geoids=tract_geoids)
    tract_payload = {
        "type": "FeatureCollection",
        "features": _build_demographic_snapshot_features(tract_features, acs_estimates),
    }
    write_json(paths["tracts"], tract_payload)

    metadata = (
        DataSourceMetadata(
            name="mta_station_catalog",
            source_url=MTA_SUBWAY_STATIONS_API_URL,
            cache_path=paths["station_catalog"],
            refreshed_at=datetime.fromisoformat(refreshed_at),
            record_count=len(selected_station_rows),
            notes="Filtered in memory against the selected study area boundary.",
        ),
        DataSourceMetadata(
            name="mta_equipment_assets",
            source_url=MTA_EQUIPMENT_ASSET_API_URL,
            cache_path=paths["assets"],
            refreshed_at=datetime.fromisoformat(refreshed_at),
            record_count=len(asset_rows),
        ),
        DataSourceMetadata(
            name="mta_availability_history",
            source_url=MTA_ELEVATOR_AVAILABILITY_API_URL,
            cache_path=paths["availability"],
            refreshed_at=datetime.fromisoformat(refreshed_at),
            record_count=len(availability_rows),
            notes=f"Monthly availability rows since {start_month.isoformat()}.",
        ),
        DataSourceMetadata(
            name="acs_tract_demographics",
            source_url=f"{ACS_COUNTS_API_URL} and {ACS_SUBJECT_API_URL}",
            cache_path=paths["tracts"],
            refreshed_at=datetime.fromisoformat(refreshed_at),
            record_count=len(tract_payload["features"]),
            notes=f"ACS 5-year {ACS_5YEAR_YEAR} estimates merged to NYC tract centroids.",
        ),
    )
    metadata_payload = {
        "generated_at": refreshed_at,
        "query": asdict(query),
        "sources": [
            {
                "name": item.name,
                "source_url": item.source_url,
                "cache_path": str(item.cache_path),
                "refreshed_at": item.refreshed_at.isoformat(),
                "record_count": item.record_count,
                "notes": item.notes,
            }
            for item in metadata
        ],
        "include_gtfs_archive": include_gtfs_archive,
        "gtfs_archive_path": str(paths["gtfs_archive"]) if include_gtfs_archive else None,
        "gtfs_archive_url": MTA_GTFS_STATIC_URL if include_gtfs_archive else None,
    }
    write_json(paths["metadata"], metadata_payload)
    return load_cached_snapshot(cache_root)

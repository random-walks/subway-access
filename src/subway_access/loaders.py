"""Loader entry points for the implemented v0.1 analysis slice."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ._fixtures import (
    DEFAULT_ACCESSIBILITY_FIXTURE,
    DEFAULT_STATIONS_FIXTURE,
    DEFAULT_TRACTS_FIXTURE,
)
from ._not_implemented import planned_surface
from .models import (
    AccessibilityDataset,
    AccessibilityStatus,
    DemographicDataset,
    Station,
    StationDataset,
    TractDemographics,
)

if TYPE_CHECKING:
    from .models import AccessibilityLabel

_VALID_ACCESSIBILITY_STATUSES: tuple[AccessibilityLabel, ...] = (
    "accessible",
    "not_accessible",
    "unknown",
)


def _resolve_source(source: str | Path) -> Path:
    return Path(source).expanduser().resolve()


def _load_csv_rows(
    source: str | Path, *, required_columns: tuple[str, ...]
) -> list[dict[str, str]]:
    path = _resolve_source(source)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            message = f"{path} does not contain a header row."
            raise ValueError(message)

        missing_columns = sorted(set(required_columns).difference(reader.fieldnames))
        if missing_columns:
            joined = ", ".join(missing_columns)
            message = f"{path} is missing required columns: {joined}."
            raise ValueError(message)

        return [dict(row) for row in reader]


def _parse_accessibility_label(
    raw_value: str, *, path: Path, station_id: str
) -> AccessibilityLabel:
    value = raw_value.strip().lower()
    if value not in _VALID_ACCESSIBILITY_STATUSES:
        valid_values = ", ".join(_VALID_ACCESSIBILITY_STATUSES)
        message = (
            f"{path} contains invalid ada_status {value!r} for station {station_id}. "
            f"Expected one of: {valid_values}."
        )
        raise ValueError(message)
    return cast("AccessibilityLabel", value)


def _parse_float(value: str, *, field_name: str, path: Path, row_id: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        message = (
            f"{path} contains a non-numeric {field_name!r} value "
            f"for record {row_id!r}: {value!r}."
        )
        raise ValueError(message) from exc


def _parse_int(value: int | str, *, field_name: str, path: Path, row_id: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        message = (
            f"{path} contains a non-integer {field_name!r} value "
            f"for record {row_id!r}: {value!r}."
        )
        raise ValueError(message) from exc


def _ensure_unique_ids(
    records: list[dict[str, str]], *, id_field: str, path: Path
) -> None:
    seen_ids: set[str] = set()
    duplicates: set[str] = set()
    for record in records:
        identifier = record[id_field]
        if identifier in seen_ids:
            duplicates.add(identifier)
        seen_ids.add(identifier)

    if duplicates:
        joined = ", ".join(sorted(duplicates))
        message = f"{path} contains duplicate {id_field} values: {joined}."
        raise ValueError(message)


def load_gtfs(source: str | Path = DEFAULT_STATIONS_FIXTURE) -> StationDataset:
    """Load the v0.1 GTFS-like station fixture or a compatible station CSV.

    The current implementation supports a narrow station-file subset with the
    columns ``station_id``, ``name``, ``borough``, ``latitude``, and
    ``longitude``. It intentionally does not attempt full GTFS parsing yet.
    """

    path = _resolve_source(source)
    rows = _load_csv_rows(
        path,
        required_columns=("station_id", "name", "borough", "latitude", "longitude"),
    )
    _ensure_unique_ids(rows, id_field="station_id", path=path)

    stations = tuple(
        Station(
            station_id=row["station_id"].strip(),
            name=row["name"].strip(),
            borough=row["borough"].strip(),
            latitude=_parse_float(
                row["latitude"],
                field_name="latitude",
                path=path,
                row_id=row["station_id"],
            ),
            longitude=_parse_float(
                row["longitude"],
                field_name="longitude",
                path=path,
                row_id=row["station_id"],
            ),
        )
        for row in rows
    )
    return StationDataset(stations=stations)


def load_accessibility_status(
    source: str | Path = DEFAULT_ACCESSIBILITY_FIXTURE,
) -> AccessibilityDataset:
    """Load station accessibility status keyed by station identifier."""

    path = _resolve_source(source)
    rows = _load_csv_rows(path, required_columns=("station_id", "ada_status"))
    _ensure_unique_ids(rows, id_field="station_id", path=path)

    statuses = tuple(
        AccessibilityStatus(
            station_id=row["station_id"].strip(),
            ada_status=_parse_accessibility_label(
                row["ada_status"], path=path, station_id=row["station_id"].strip()
            ),
        )
        for row in rows
    )
    return AccessibilityDataset(statuses=statuses)


def load_outages(source: str | Path) -> Any:
    """Load current or historical elevator and escalator outage data."""
    del source
    planned_surface("load_outages()")


def load_census_data(source: str | Path = DEFAULT_TRACTS_FIXTURE) -> DemographicDataset:
    """Load tract-level demographic variables used in v0.1 need scoring."""

    path = _resolve_source(source)
    with path.open(encoding="utf-8") as handle:
        raw_payload = json.load(handle)

    features = raw_payload.get("features")
    if not isinstance(features, list):
        message = f"{path} must contain a GeoJSON FeatureCollection with features."
        raise TypeError(message)

    tracts: list[TractDemographics] = []
    seen_ids: set[str] = set()
    duplicates: set[str] = set()

    for feature in features:
        if not isinstance(feature, dict):
            message = f"{path} contains a non-object feature entry."
            raise TypeError(message)

        properties = feature.get("properties")
        if not isinstance(properties, dict):
            message = f"{path} contains a feature without object properties."
            raise TypeError(message)

        tract_id = str(properties.get("tract_id", "")).strip()
        if not tract_id:
            message = f"{path} contains a feature without a tract_id."
            raise ValueError(message)
        if tract_id in seen_ids:
            duplicates.add(tract_id)
        seen_ids.add(tract_id)

        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") != "Point":
            message = (
                f"{path} feature {tract_id} must use Point geometry "
                "for centroid-based v0.1 joins."
            )
            raise TypeError(message)

        coordinates = geometry.get("coordinates")
        if (
            not isinstance(coordinates, list)
            or len(coordinates) != 2
            or not all(isinstance(value, int | float) for value in coordinates)
        ):
            message = (
                f"{path} feature {tract_id} must contain two numeric point coordinates."
            )
            raise TypeError(message)

        tracts.append(
            TractDemographics(
                tract_id=tract_id,
                tract_name=str(properties.get("tract_name", "")).strip() or tract_id,
                borough=str(properties.get("borough", "")).strip(),
                centroid_latitude=_parse_float(
                    str(properties.get("centroid_latitude", coordinates[1])),
                    field_name="centroid_latitude",
                    path=path,
                    row_id=tract_id,
                ),
                centroid_longitude=_parse_float(
                    str(properties.get("centroid_longitude", coordinates[0])),
                    field_name="centroid_longitude",
                    path=path,
                    row_id=tract_id,
                ),
                disability_rate=_parse_float(
                    str(properties["disability_rate"]),
                    field_name="disability_rate",
                    path=path,
                    row_id=tract_id,
                ),
                senior_rate=_parse_float(
                    str(properties["senior_rate"]),
                    field_name="senior_rate",
                    path=path,
                    row_id=tract_id,
                ),
                poverty_rate=_parse_float(
                    str(properties["poverty_rate"]),
                    field_name="poverty_rate",
                    path=path,
                    row_id=tract_id,
                ),
                total_population=_parse_int(
                    properties["population"],
                    field_name="population",
                    path=path,
                    row_id=tract_id,
                ),
            )
        )

    if duplicates:
        joined = ", ".join(sorted(duplicates))
        message = f"{path} contains duplicate tract_id values: {joined}."
        raise ValueError(message)

    return DemographicDataset(tracts=tuple(tracts))


def load_pedestrian_network(source: str | Path | None = None) -> Any:
    """Load or build the pedestrian network used for catchment analysis."""
    del source
    planned_surface("load_pedestrian_network()")

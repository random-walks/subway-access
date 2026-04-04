"""Loader entry points for ``subway-access`` datasets."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from ..models import (
    AccessibilityDataset,
    AccessibilityLabel,
    AccessibilityStatus,
    DemographicDataset,
    EquipmentType,
    OutageDataset,
    OutageRecord,
    OutageStatus,
    PedestrianConnection,
    PedestrianNetworkDataset,
    Station,
    StationDataset,
    TractDemographics,
)

_FIXTURES_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "fixtures"
DEFAULT_STATIONS_FIXTURE = _FIXTURES_DIRECTORY / "stations.csv"
DEFAULT_ACCESSIBILITY_FIXTURE = _FIXTURES_DIRECTORY / "accessibility.csv"
DEFAULT_TRACTS_FIXTURE = _FIXTURES_DIRECTORY / "tracts.geojson"
DEFAULT_OUTAGES_FIXTURE = _FIXTURES_DIRECTORY / "outages.csv"
DEFAULT_PEDESTRIAN_NETWORK_FIXTURE = _FIXTURES_DIRECTORY / "pedestrian-network.geojson"

_VALID_ACCESSIBILITY_STATUSES: tuple[AccessibilityLabel, ...] = (
    "accessible",
    "not_accessible",
    "unknown",
)
_VALID_EQUIPMENT_TYPES: tuple[EquipmentType, ...] = (
    "elevator",
    "escalator",
    "station",
    "platform",
    "unknown",
)
_VALID_OUTAGE_STATUSES: tuple[OutageStatus, ...] = (
    "active",
    "resolved",
    "scheduled",
    "unknown",
)


def _is_url(source: str | Path) -> bool:
    return isinstance(source, str) and source.startswith(("http://", "https://"))


def _resolve_source(source: str | Path) -> Path:
    return Path(source).expanduser().resolve()


def _read_text(source: str | Path, *, timeout_seconds: float = 10.0) -> tuple[str, str]:
    if _is_url(source):
        with urlopen(str(source), timeout=timeout_seconds) as response:
            encoding = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(encoding), str(source)

    path = _resolve_source(source)
    return path.read_text(encoding="utf-8"), str(path)


def _load_csv_rows(
    source: str | Path,
    *,
    required_columns: tuple[str, ...],
) -> tuple[list[dict[str, str]], str]:
    text, source_name = _read_text(source)
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None:
        message = f"{source_name} does not contain a header row."
        raise ValueError(message)

    missing_columns = sorted(set(required_columns).difference(reader.fieldnames))
    if missing_columns:
        joined = ", ".join(missing_columns)
        message = f"{source_name} is missing required columns: {joined}."
        raise ValueError(message)

    return [dict(row) for row in reader], source_name


def _parse_float(
    value: object,
    *,
    field_name: str,
    source_name: str,
    row_id: str,
) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError) as exc:
        message = (
            f"{source_name} contains a non-numeric {field_name!r} value "
            f"for record {row_id!r}: {value!r}."
        )
        raise ValueError(message) from exc


def _parse_int(
    value: object,
    *,
    field_name: str,
    source_name: str,
    row_id: str,
) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        message = (
            f"{source_name} contains a non-integer {field_name!r} value "
            f"for record {row_id!r}: {value!r}."
        )
        raise ValueError(message) from exc


def _ensure_unique_ids(
    records: list[dict[str, str]],
    *,
    id_field: str,
    source_name: str,
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
        message = f"{source_name} contains duplicate {id_field} values: {joined}."
        raise ValueError(message)


def _parse_accessibility_label(
    raw_value: str,
    *,
    source_name: str,
    station_id: str,
) -> AccessibilityLabel:
    value = raw_value.strip().lower()
    if value not in _VALID_ACCESSIBILITY_STATUSES:
        valid_values = ", ".join(_VALID_ACCESSIBILITY_STATUSES)
        message = (
            f"{source_name} contains invalid ada_status {value!r} for station "
            f"{station_id}. Expected one of: {valid_values}."
        )
        raise ValueError(message)
    return value


def _parse_timestamp(
    raw_value: str,
    *,
    field_name: str,
    source_name: str,
    row_id: str,
) -> datetime:
    candidate = raw_value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        message = (
            f"{source_name} contains an invalid timestamp in {field_name!r} "
            f"for record {row_id!r}: {raw_value!r}."
        )
        raise ValueError(message) from exc
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _parse_outage_status(raw_value: str) -> OutageStatus:
    value = raw_value.strip().lower()
    return value if value in _VALID_OUTAGE_STATUSES else "unknown"


def _parse_equipment_type(raw_value: str) -> EquipmentType:
    value = raw_value.strip().lower()
    return value if value in _VALID_EQUIPMENT_TYPES else "unknown"


def load_gtfs(source: str | Path = DEFAULT_STATIONS_FIXTURE) -> StationDataset:
    """Load the narrow GTFS-like station table used by the project examples."""

    rows, source_name = _load_csv_rows(
        source,
        required_columns=("station_id", "name", "borough", "latitude", "longitude"),
    )
    _ensure_unique_ids(rows, id_field="station_id", source_name=source_name)

    stations = tuple(
        Station(
            station_id=row["station_id"].strip(),
            name=row["name"].strip(),
            borough=row["borough"].strip(),
            latitude=_parse_float(
                row["latitude"],
                field_name="latitude",
                source_name=source_name,
                row_id=row["station_id"],
            ),
            longitude=_parse_float(
                row["longitude"],
                field_name="longitude",
                source_name=source_name,
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

    rows, source_name = _load_csv_rows(
        source,
        required_columns=("station_id", "ada_status"),
    )
    _ensure_unique_ids(rows, id_field="station_id", source_name=source_name)

    statuses = tuple(
        AccessibilityStatus(
            station_id=row["station_id"].strip(),
            ada_status=_parse_accessibility_label(
                row["ada_status"],
                source_name=source_name,
                station_id=row["station_id"].strip(),
            ),
        )
        for row in rows
    )
    return AccessibilityDataset(statuses=statuses)


def load_census_data(source: str | Path = DEFAULT_TRACTS_FIXTURE) -> DemographicDataset:
    """Load tract-level demographic variables used in need scoring."""

    text, source_name = _read_text(source)
    raw_payload = json.loads(text)
    features = raw_payload.get("features")
    if not isinstance(features, list):
        message = f"{source_name} must contain a GeoJSON FeatureCollection with features."
        raise TypeError(message)

    tracts: list[TractDemographics] = []
    seen_ids: set[str] = set()
    duplicates: set[str] = set()
    for feature in features:
        if not isinstance(feature, dict):
            message = f"{source_name} contains a non-object feature entry."
            raise TypeError(message)
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            message = f"{source_name} contains a feature without object properties."
            raise TypeError(message)

        tract_id = str(properties.get("tract_id", "")).strip()
        if not tract_id:
            message = f"{source_name} contains a feature without a tract_id."
            raise ValueError(message)
        if tract_id in seen_ids:
            duplicates.add(tract_id)
        seen_ids.add(tract_id)

        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") != "Point":
            message = (
                f"{source_name} feature {tract_id} must use Point geometry "
                "for centroid-based joins."
            )
            raise TypeError(message)
        coordinates = geometry.get("coordinates")
        if (
            not isinstance(coordinates, list)
            or len(coordinates) != 2
            or not all(isinstance(value, int | float) for value in coordinates)
        ):
            message = (
                f"{source_name} feature {tract_id} must contain two numeric point "
                "coordinates."
            )
            raise TypeError(message)

        tracts.append(
            TractDemographics(
                tract_id=tract_id,
                tract_name=str(properties.get("tract_name", "")).strip() or tract_id,
                borough=str(properties.get("borough", "")).strip(),
                centroid_latitude=_parse_float(
                    properties.get("centroid_latitude", coordinates[1]),
                    field_name="centroid_latitude",
                    source_name=source_name,
                    row_id=tract_id,
                ),
                centroid_longitude=_parse_float(
                    properties.get("centroid_longitude", coordinates[0]),
                    field_name="centroid_longitude",
                    source_name=source_name,
                    row_id=tract_id,
                ),
                disability_rate=_parse_float(
                    properties["disability_rate"],
                    field_name="disability_rate",
                    source_name=source_name,
                    row_id=tract_id,
                ),
                senior_rate=_parse_float(
                    properties["senior_rate"],
                    field_name="senior_rate",
                    source_name=source_name,
                    row_id=tract_id,
                ),
                poverty_rate=_parse_float(
                    properties["poverty_rate"],
                    field_name="poverty_rate",
                    source_name=source_name,
                    row_id=tract_id,
                ),
                total_population=_parse_int(
                    properties["population"],
                    field_name="population",
                    source_name=source_name,
                    row_id=tract_id,
                ),
            )
        )

    if duplicates:
        joined = ", ".join(sorted(duplicates))
        message = f"{source_name} contains duplicate tract_id values: {joined}."
        raise ValueError(message)

    return DemographicDataset(tracts=tuple(tracts))


def _normalize_outage_record(
    record: dict[str, Any],
    *,
    source_name: str,
    record_index: int,
) -> OutageRecord:
    station_id = str(record.get("station_id") or record.get("stationId") or "").strip()
    if not station_id:
        message = f"{source_name} outage record {record_index} is missing station_id."
        raise ValueError(message)
    equipment_id = str(
        record.get("equipment_id") or record.get("equipmentId") or record.get("unit") or ""
    ).strip() or f"{station_id}-equipment-{record_index}"
    started_raw = str(
        record.get("started_at")
        or record.get("start_time")
        or record.get("startTime")
        or record.get("outageStart")
        or ""
    ).strip()
    if not started_raw:
        message = f"{source_name} outage record {record_index} is missing started_at."
        raise ValueError(message)
    ended_raw = str(
        record.get("ended_at")
        or record.get("end_time")
        or record.get("endTime")
        or record.get("outageEnd")
        or ""
    ).strip()
    return OutageRecord(
        station_id=station_id,
        equipment_id=equipment_id,
        equipment_type=_parse_equipment_type(
            str(record.get("equipment_type") or record.get("equipmentType") or "unknown")
        ),
        status=_parse_outage_status(str(record.get("status") or "unknown")),
        started_at=_parse_timestamp(
            started_raw,
            field_name="started_at",
            source_name=source_name,
            row_id=equipment_id,
        ),
        ended_at=None
        if not ended_raw
        else _parse_timestamp(
            ended_raw,
            field_name="ended_at",
            source_name=source_name,
            row_id=equipment_id,
        ),
        description=str(record.get("description") or record.get("message") or "").strip(),
        source=source_name,
    )


def load_outages(source: str | Path = DEFAULT_OUTAGES_FIXTURE) -> OutageDataset:
    """Load elevator or escalator outage history from CSV, JSON, or a URL."""

    if not _is_url(source):
        path = _resolve_source(source)
        suffix = path.suffix.lower()
    else:
        path = None
        suffix = ".json"

    if suffix == ".csv":
        rows, source_name = _load_csv_rows(
            source,
            required_columns=(
                "station_id",
                "equipment_id",
                "equipment_type",
                "status",
                "started_at",
                "ended_at",
            ),
        )
        records = tuple(
            _normalize_outage_record(row, source_name=source_name, record_index=index)
            for index, row in enumerate(rows, start=1)
        )
        return OutageDataset(records=records)

    text, source_name = _read_text(source)
    payload = json.loads(text)
    raw_records = payload
    if isinstance(payload, dict):
        raw_records = (
            payload.get("outages") or payload.get("results") or payload.get("data") or []
        )
    if not isinstance(raw_records, list):
        message = f"{source_name} must contain a list of outage records."
        raise TypeError(message)
    records = tuple(
        _normalize_outage_record(record, source_name=source_name, record_index=index)
        for index, record in enumerate(raw_records, start=1)
        if isinstance(record, dict)
    )
    return OutageDataset(records=records)


def _normalize_network_record(
    record: dict[str, Any],
    *,
    source_name: str,
    record_index: int,
    geometry: tuple[tuple[float, float], ...] = (),
) -> PedestrianConnection:
    from_station_id = str(
        record.get("from_station_id") or record.get("fromStationId") or ""
    ).strip()
    to_station_id = str(
        record.get("to_station_id") or record.get("toStationId") or ""
    ).strip()
    if not from_station_id or not to_station_id:
        message = (
            f"{source_name} pedestrian connection {record_index} is missing "
            "from_station_id or to_station_id."
        )
        raise ValueError(message)
    connection_id = str(record.get("connection_id") or "").strip() or (
        f"{from_station_id}-{to_station_id}"
    )
    return PedestrianConnection(
        connection_id=connection_id,
        from_station_id=from_station_id,
        to_station_id=to_station_id,
        walk_minutes=_parse_float(
            record.get("walk_minutes", 0),
            field_name="walk_minutes",
            source_name=source_name,
            row_id=connection_id,
        ),
        distance_meters=_parse_float(
            record.get("distance_meters", 0),
            field_name="distance_meters",
            source_name=source_name,
            row_id=connection_id,
        ),
        geometry=geometry,
    )


def load_pedestrian_network(
    source: str | Path = DEFAULT_PEDESTRIAN_NETWORK_FIXTURE,
) -> PedestrianNetworkDataset:
    """Load a simplified pedestrian connection graph from CSV or GeoJSON."""

    suffix = ".json" if _is_url(source) else _resolve_source(source).suffix.lower()

    if suffix == ".csv":
        rows, source_name = _load_csv_rows(
            source,
            required_columns=(
                "from_station_id",
                "to_station_id",
                "walk_minutes",
                "distance_meters",
            ),
        )
        csv_connections = tuple(
            _normalize_network_record(row, source_name=source_name, record_index=index)
            for index, row in enumerate(rows, start=1)
        )
        return PedestrianNetworkDataset(connections=csv_connections)

    text, source_name = _read_text(source)
    payload = json.loads(text)
    features = payload.get("features") if isinstance(payload, dict) else None
    if not isinstance(features, list):
        message = f"{source_name} must contain a GeoJSON FeatureCollection."
        raise TypeError(message)

    connections: list[PedestrianConnection] = []
    for index, feature in enumerate(features, start=1):
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(properties, dict) or not isinstance(geometry, dict):
            continue
        coordinates = geometry.get("coordinates")
        if geometry.get("type") != "LineString" or not isinstance(coordinates, list):
            message = (
                f"{source_name} pedestrian connection {index} must use LineString geometry."
            )
            raise TypeError(message)
        geometry_points = tuple(
            (float(point[0]), float(point[1]))
            for point in coordinates
            if isinstance(point, list) and len(point) >= 2
        )
        connections.append(
            _normalize_network_record(
                properties,
                source_name=source_name,
                record_index=index,
                geometry=geometry_points,
            )
        )
    return PedestrianNetworkDataset(connections=tuple(connections))

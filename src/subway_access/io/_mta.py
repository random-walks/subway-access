"""Official MTA fetch helpers for ``subway-access``."""

from __future__ import annotations

import calendar
import json
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import quote
from urllib.request import urlopen

if TYPE_CHECKING:
    from pathlib import Path

MTA_SUBWAY_STATIONS_API_URL = "https://data.ny.gov/resource/39hk-dx4f.json"
MTA_EQUIPMENT_ASSET_API_URL = "https://data.ny.gov/resource/94fv-bak7.json"
MTA_ELEVATOR_AVAILABILITY_API_URL = "https://data.ny.gov/resource/rc78-7x78.json"
MTA_GTFS_STATIC_URL = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip"

_BOROUGH_MAP = {
    "B": "Brooklyn",
    "BK": "Brooklyn",
    "BRONX": "Bronx",
    "BX": "Bronx",
    "M": "Manhattan",
    "MN": "Manhattan",
    "Q": "Queens",
    "QN": "Queens",
    "R": "Staten Island",
    "SI": "Staten Island",
    "S": "Staten Island",
    "X": "Bronx",
}
_ADA_STATUS_MAP = {
    "0": "not_accessible",
    "1": "accessible",
    "2": "partially_accessible",
}


def _read_json(url: str) -> list[dict[str, Any]]:
    with urlopen(url, timeout=30.0) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        message = f"Expected a JSON list from {url!r}."
        raise TypeError(message)
    return [row for row in payload if isinstance(row, dict)]


def _build_socrata_url(
    base_url: str,
    *,
    select: str | None = None,
    where: str | None = None,
    order: str | None = None,
    limit: int | None = None,
) -> str:
    parts = []
    if select:
        parts.append("$select=" + quote(select, safe=",()*_"))
    if where:
        parts.append("$where=" + quote(where, safe="'(),:*_<>"))
    if order:
        parts.append("$order=" + quote(order, safe=",_"))
    if limit is not None:
        parts.append(f"$limit={limit}")
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{'&'.join(parts)}" if parts else base_url


def fetch_mta_station_catalog(*, limit: int = 2000) -> list[dict[str, Any]]:
    """Fetch the public MTA subway station catalog from Open NY."""

    url = _build_socrata_url(
        MTA_SUBWAY_STATIONS_API_URL,
        limit=limit,
        order="station_id",
    )
    return _read_json(url)


def fetch_mta_equipment_assets(
    *,
    station_complex_ids: tuple[str, ...] | None = None,
    limit: int = 5000,
) -> list[dict[str, Any]]:
    """Fetch elevator and escalator asset inventory rows."""

    where = None
    if station_complex_ids:
        joined = ", ".join(f"'{value}'" for value in sorted(set(station_complex_ids)))
        where = f"station_complex_mrn in ({joined})"
    url = _build_socrata_url(
        MTA_EQUIPMENT_ASSET_API_URL,
        where=where,
        order="equipment_code",
        limit=limit,
    )
    return _read_json(url)


def fetch_mta_availability_history(
    *,
    station_complex_ids: tuple[str, ...] | None = None,
    start_month: date | None = None,
    limit: int = 50000,
) -> list[dict[str, Any]]:
    """Fetch public monthly elevator and escalator availability history."""

    where_clauses: list[str] = []
    if station_complex_ids:
        joined = ", ".join(f"'{value}'" for value in sorted(set(station_complex_ids)))
        where_clauses.append(f"station_complex_mrn in ({joined})")
    if start_month is not None:
        start_text = start_month.isoformat()
        where_clauses.append(f"month >= '{start_text}T00:00:00'")
    where = " and ".join(where_clauses) if where_clauses else None
    url = _build_socrata_url(
        MTA_ELEVATOR_AVAILABILITY_API_URL,
        where=where,
        order="month desc",
        limit=limit,
    )
    return _read_json(url)


def fetch_mta_gtfs_archive(
    target_path: Path,
    *,
    source_url: str = MTA_GTFS_STATIC_URL,
    refresh: bool = False,
) -> Path:
    """Download the official subway GTFS archive into the cache."""

    if target_path.exists() and not refresh:
        return target_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(source_url, timeout=60.0) as response:
        target_path.write_bytes(response.read())
    return target_path


def _full_borough_name(raw_value: str) -> str:
    value = raw_value.strip().upper()
    return _BOROUGH_MAP.get(value, raw_value.strip())


def _map_ada_status(raw_value: str) -> str:
    return _ADA_STATUS_MAP.get(raw_value.strip(), "unknown")


def build_station_snapshot_rows(
    station_catalog_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Normalize raw station catalog rows into cacheable CSV snapshots."""

    station_rows: list[dict[str, str]] = []
    accessibility_rows: list[dict[str, str]] = []
    seen_station_ids: set[str] = set()

    for row in station_catalog_rows:
        station_id = str(row.get("station_id") or "").strip()
        if not station_id or station_id in seen_station_ids:
            continue
        seen_station_ids.add(station_id)
        station_rows.append(
            {
                "station_id": station_id,
                "name": str(row.get("stop_name") or "").strip(),
                "borough": _full_borough_name(str(row.get("borough") or "")),
                "latitude": str(row.get("gtfs_latitude") or ""),
                "longitude": str(row.get("gtfs_longitude") or ""),
                "complex_id": str(row.get("complex_id") or "").strip(),
                "gtfs_stop_id": str(row.get("gtfs_stop_id") or "").strip(),
                "daytime_routes": str(row.get("daytime_routes") or "").strip(),
                "division": str(row.get("division") or "").strip(),
                "line": str(row.get("line") or "").strip(),
                "structure": str(row.get("structure") or "").strip(),
                "north_direction_label": str(
                    row.get("north_direction_label") or ""
                ).strip(),
                "south_direction_label": str(
                    row.get("south_direction_label") or ""
                ).strip(),
                "accessibility_notes": str(
                    row.get("ada_direction_notes") or ""
                ).strip(),
            }
        )
        accessibility_rows.append(
            {
                "station_id": station_id,
                "ada_status": _map_ada_status(str(row.get("ada") or "")),
                "notes": str(row.get("ada_direction_notes") or "").strip(),
            }
        )

    return station_rows, accessibility_rows


def build_outage_snapshot_rows(
    availability_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize public availability history rows into outage-style snapshot rows."""

    normalized_rows: list[dict[str, Any]] = []
    for row in availability_rows:
        station_id = str(
            row.get("station_mrn") or row.get("station_complex_mrn") or ""
        ).strip()
        equipment_id = str(row.get("equipment_code") or "").strip()
        month_text = str(row.get("month") or "").strip()
        if not station_id or not equipment_id or not month_text:
            continue

        month_start = datetime.fromisoformat(month_text.replace("Z", "+00:00"))
        month_start = (
            month_start
            if month_start.tzinfo is not None
            else month_start.replace(tzinfo=timezone.utc)
        )
        last_day = calendar.monthrange(month_start.year, month_start.month)[1]
        month_end = month_start.replace(day=last_day, hour=23, minute=59, second=59)

        total_hours = float(str(row.get("_24_hour_total_hours") or 0))
        available_hours = float(str(row.get("_24_hour_hours_available") or 0))
        availability_ratio = (
            float(str(row.get("_24_hour_availability")))
            if row.get("_24_hour_availability") is not None
            else 0.0
        )
        outage_minutes_override = max(round((total_hours - available_hours) * 60), 0)
        normalized_rows.append(
            {
                "station_id": station_id,
                "station_complex_id": str(row.get("station_complex_mrn") or "").strip(),
                "equipment_id": equipment_id,
                "equipment_type": str(row.get("equipment_type") or "").strip().lower(),
                "status": "resolved",
                "started_at": month_start.isoformat(),
                "ended_at": month_end.isoformat(),
                "description": (
                    f"Monthly availability snapshot for {row.get('station_name', station_id)}"
                ),
                "availability_ratio": availability_ratio,
                "outage_minutes_override": outage_minutes_override,
                "total_outages": row.get("total_outages"),
                "scheduled_outages": row.get("scheduled_outages"),
                "unscheduled_outages": row.get("unscheduled_outages"),
            }
        )
    return normalized_rows

"""Optional GTFS-Pathways parsing from a static GTFS zip (``pathways.txt``, ``locations.txt``)."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..models import GtfsLocation, GtfsPathway, GtfsPathwaysSnapshot


def parse_gtfs_pathways_zip(zip_path: Path) -> GtfsPathwaysSnapshot | None:
    """Parse GTFS-Pathways files from a static archive if present.

    Returns ``None`` when neither ``pathways.txt`` nor ``locations.txt`` exists in the zip
    (current MTA ``gtfs_subway.zip`` has neither).
    """

    path = zip_path.expanduser().resolve()
    if not path.exists():
        return None

    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        has_pathways = "pathways.txt" in names
        has_locations = "locations.txt" in names
        if not has_pathways and not has_locations:
            return None

        pathways: tuple[GtfsPathway, ...] = ()
        locations: tuple[GtfsLocation, ...] = ()

        if has_pathways:
            text = zf.read("pathways.txt").decode("utf-8")
            pathways = _parse_pathways_txt(text)
        if has_locations:
            text = zf.read("locations.txt").decode("utf-8")
            locations = _parse_locations_txt(text)

    return GtfsPathwaysSnapshot(pathways=pathways, locations=locations)


def _parse_pathways_txt(text: str) -> tuple[GtfsPathway, ...]:
    reader = csv.DictReader(io.StringIO(text))
    rows: list[GtfsPathway] = []
    for raw in reader:
        pathway_id = str(raw.get("pathway_id") or "").strip()
        from_id = str(raw.get("from_stop_id") or "").strip()
        to_id = str(raw.get("to_stop_id") or "").strip()
        if not pathway_id or not from_id or not to_id:
            continue
        rows.append(
            GtfsPathway(
                pathway_id=pathway_id,
                from_stop_id=from_id,
                to_stop_id=to_id,
                pathway_mode=str(raw.get("pathway_mode") or "").strip(),
                is_bidirectional=str(raw.get("is_bidirectional") or "").strip(),
                length=_optional_cell(raw.get("length")),
                traversal_time=_optional_cell(raw.get("traversal_time")),
                stair_count=_optional_cell(raw.get("stair_count")),
                max_slope=_optional_cell(raw.get("max_slope")),
                min_width=_optional_cell(raw.get("min_width")),
                signposted_as=_optional_cell(raw.get("signposted_as")),
            )
        )
    return tuple(rows)


def _parse_locations_txt(text: str) -> tuple[GtfsLocation, ...]:
    reader = csv.DictReader(io.StringIO(text))
    rows: list[GtfsLocation] = []
    for raw in reader:
        location_id = str(raw.get("location_id") or "").strip()
        if not location_id:
            continue
        parent = raw.get("parent_station")
        rows.append(
            GtfsLocation(
                location_id=location_id,
                location_type=str(raw.get("location_type") or "").strip(),
                parent_station=str(parent).strip() if parent else None,
                latitude=_optional_cell(raw.get("stop_lat")),
                longitude=_optional_cell(raw.get("stop_lon")),
            )
        )
    return tuple(rows)


def _optional_cell(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def gtfs_pathways_snapshot_to_json(snapshot: GtfsPathwaysSnapshot) -> dict[str, Any]:
    """Serialize a pathways snapshot for ``write_json``."""

    return {
        "pathways": [asdict(p) for p in snapshot.pathways],
        "locations": [asdict(loc) for loc in snapshot.locations],
    }


def load_gtfs_pathways_snapshot(source: str | Path) -> GtfsPathwaysSnapshot:
    """Load ``gtfs-pathways.json`` written by the pipeline."""

    path = Path(source).expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    pathways_raw = payload.get("pathways", [])
    locations_raw = payload.get("locations", [])
    pathways_list: list[GtfsPathway] = []
    for row in pathways_raw:
        if not isinstance(row, dict):
            continue
        pathways_list.append(
            GtfsPathway(
                pathway_id=str(row.get("pathway_id") or ""),
                from_stop_id=str(row.get("from_stop_id") or ""),
                to_stop_id=str(row.get("to_stop_id") or ""),
                pathway_mode=str(row.get("pathway_mode") or ""),
                is_bidirectional=str(row.get("is_bidirectional") or ""),
                length=_optional_cell(row.get("length")),
                traversal_time=_optional_cell(row.get("traversal_time")),
                stair_count=_optional_cell(row.get("stair_count")),
                max_slope=_optional_cell(row.get("max_slope")),
                min_width=_optional_cell(row.get("min_width")),
                signposted_as=_optional_cell(row.get("signposted_as")),
            )
        )
    locations_list: list[GtfsLocation] = []
    for row in locations_raw:
        if not isinstance(row, dict):
            continue
        parent = row.get("parent_station")
        locations_list.append(
            GtfsLocation(
                location_id=str(row.get("location_id") or ""),
                location_type=str(row.get("location_type") or ""),
                parent_station=str(parent).strip() if parent else None,
                latitude=_optional_cell(row.get("latitude")),
                longitude=_optional_cell(row.get("longitude")),
            )
        )
    return GtfsPathwaysSnapshot(
        pathways=tuple(pathways_list),
        locations=tuple(locations_list),
    )

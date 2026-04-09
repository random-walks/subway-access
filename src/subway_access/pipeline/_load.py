"""Cached snapshot loading for ``subway-access``."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..io import (
    load_accessibility_status,
    load_census_data,
    load_gtfs,
    load_outages,
)
from ..io._entrances import load_entrances
from ..io._gtfs_static import load_gtfs_pathways_snapshot
from ..models import (
    AccessibilityQuery,
    DataSourceMetadata,
    EntranceDataset,
    StudyAreaSnapshot,
)


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
        "entrances": cache_dir / "entrances.geojson",
        "gtfs_pathways": cache_dir / "gtfs-pathways.json",
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
    if paths["entrances"].exists():
        entrances = load_entrances(paths["entrances"])
    else:
        entrances = EntranceDataset(entrances=())
    gtfs_pathways = None
    if paths["gtfs_pathways"].exists():
        gtfs_pathways = load_gtfs_pathways_snapshot(paths["gtfs_pathways"])
    return StudyAreaSnapshot(
        query=query,
        stations=stations,
        accessibility=accessibility,
        demographics=demographics,
        outages=outages,
        metadata=metadata,
        entrances=entrances,
        gtfs_pathways=gtfs_pathways,
        generated_at=datetime.fromisoformat(
            json.loads(paths["metadata"].read_text(encoding="utf-8"))["generated_at"]
        ),
        cache_dir=cache_root,
    )

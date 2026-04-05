"""Fetch all public subway-access snapshot layers across NYC boroughs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from subway_access import models, pipeline

if TYPE_CHECKING:
    from pathlib import Path

ALL_BOROUGHS: tuple[str, ...] = (
    "Manhattan",
    "Brooklyn",
    "Queens",
    "Bronx",
    "Staten Island",
)


def borough_slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def borough_cache_dir(cache_root: Path, borough: str) -> Path:
    return cache_root / borough_slug(borough)


def parse_borough_list(raw: str | None) -> tuple[str, ...]:
    if not raw or not raw.strip():
        return ALL_BOROUGHS
    names = tuple(part.strip() for part in raw.split(",") if part.strip())
    unknown = [n for n in names if n not in ALL_BOROUGHS]
    if unknown:
        joined = ", ".join(ALL_BOROUGHS)
        message = (
            f"Unknown borough name(s): {unknown}. Expected one or more of: {joined}."
        )
        raise ValueError(message)
    return names


def download_borough_snapshots(
    *,
    cache_root: Path,
    boroughs: tuple[str, ...],
    refresh: bool,
    availability_months: int,
) -> list[models.StudyAreaSnapshot]:
    """Fetch one study-area snapshot per borough. GTFS archive is downloaded only for the first borough."""
    cache_root = cache_root.expanduser().resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    snapshots: list[models.StudyAreaSnapshot] = []
    for index, borough in enumerate(boroughs):
        include_gtfs = index == 0
        target = borough_cache_dir(cache_root, borough)
        snapshot = pipeline.fetch_study_area_snapshot(
            models.AccessibilityQuery(geography="borough", value=borough),
            cache_dir=target,
            refresh=refresh,
            availability_months=availability_months,
            include_gtfs_archive=include_gtfs,
        )
        snapshots.append(snapshot)
    return snapshots


def download_walk_graphs(
    *,
    cache_root: Path,
    boroughs: tuple[str, ...],
    refresh: bool,
    buffer_meters: int,
) -> None:
    """Cache an OSM walking graph in each borough snapshot directory."""
    cache_root = cache_root.expanduser().resolve()
    for borough in boroughs:
        target = borough_cache_dir(cache_root, borough)
        pipeline.fetch_walk_graph(
            models.AccessibilityQuery(geography="borough", value=borough),
            cache_dir=target,
            refresh=refresh,
            buffer_meters=buffer_meters,
        )

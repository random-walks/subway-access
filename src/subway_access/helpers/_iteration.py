"""Multi-borough snapshot iteration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..models import AccessibilityQuery, StudyAreaSnapshot
from ..pipeline import fetch_study_area_snapshot, load_cached_snapshot

if TYPE_CHECKING:
    from collections.abc import Iterator


ALL_BOROUGHS: tuple[str, ...] = (
    "Manhattan",
    "Brooklyn",
    "Queens",
    "Bronx",
    "Staten Island",
)


def borough_cache_dir(cache_root: str | Path, borough: str) -> Path:
    """Return the canonical cache directory for a borough snapshot.

    Args:
        cache_root: Parent directory for all borough caches.
        borough: Borough name (e.g. ``"Manhattan"``).

    Returns:
        Path to the borough-specific cache directory.

    Example:
        >>> borough_cache_dir("cache", "Manhattan")
        PosixPath('cache/manhattan')
    """

    return Path(cache_root).expanduser().resolve() / borough.lower().replace(" ", "-")


def fetch_borough_snapshots(
    boroughs: tuple[str, ...] | None = None,
    *,
    cache_root: str | Path,
    refresh: bool = False,
    availability_months: int = 12,
    include_gtfs_archive: bool = True,
) -> dict[str, StudyAreaSnapshot]:
    """Fetch and cache study-area snapshots for multiple boroughs.

    Downloads GTFS archive only for the first borough to avoid redundant
    fetches of the same static feed.

    Args:
        boroughs: Borough names to fetch. Defaults to all five boroughs.
        cache_root: Parent directory for all borough caches.
        refresh: Force re-download of all data sources.
        availability_months: Months of availability history to fetch.
        include_gtfs_archive: Whether to download the GTFS static archive.

    Returns:
        Mapping of borough name to loaded ``StudyAreaSnapshot``.

    Example:
        >>> snapshots = fetch_borough_snapshots(
        ...     ("Manhattan", "Brooklyn"),
        ...     cache_root="cache",
        ... )
        >>> len(snapshots["Manhattan"].stations.stations)
        151
    """

    borough_list = boroughs or ALL_BOROUGHS
    root = Path(cache_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    snapshots: dict[str, StudyAreaSnapshot] = {}
    for index, borough in enumerate(borough_list):
        target = borough_cache_dir(root, borough)
        snapshot = fetch_study_area_snapshot(
            AccessibilityQuery(geography="borough", value=borough),
            cache_dir=target,
            refresh=refresh,
            availability_months=availability_months,
            include_gtfs_archive=include_gtfs_archive and index == 0,
        )
        snapshots[borough] = snapshot
    return snapshots


def load_borough_snapshots(
    boroughs: tuple[str, ...] | None = None,
    *,
    cache_root: str | Path,
) -> dict[str, StudyAreaSnapshot]:
    """Load previously cached snapshots for multiple boroughs.

    Args:
        boroughs: Borough names to load. Defaults to all five boroughs.
        cache_root: Parent directory for all borough caches.

    Returns:
        Mapping of borough name to loaded ``StudyAreaSnapshot``.

    Raises:
        FileNotFoundError: If any borough's cache is missing.

    Example:
        >>> snapshots = load_borough_snapshots(
        ...     ("Manhattan",), cache_root="cache"
        ... )
    """

    borough_list = boroughs or ALL_BOROUGHS
    root = Path(cache_root).expanduser().resolve()
    return {
        borough: load_cached_snapshot(borough_cache_dir(root, borough))
        for borough in borough_list
    }


def iter_borough_snapshots(
    boroughs: tuple[str, ...] | None = None,
    *,
    cache_root: str | Path,
) -> Iterator[tuple[str, StudyAreaSnapshot]]:
    """Iterate over cached borough snapshots lazily.

    Args:
        boroughs: Borough names to iterate. Defaults to all five boroughs.
        cache_root: Parent directory for all borough caches.

    Yields:
        Tuples of ``(borough_name, snapshot)``.

    Example:
        >>> for borough, snap in iter_borough_snapshots(cache_root="cache"):
        ...     print(borough, len(snap.stations.stations))
    """

    borough_list = boroughs or ALL_BOROUGHS
    root = Path(cache_root).expanduser().resolve()
    for borough in borough_list:
        yield borough, load_cached_snapshot(borough_cache_dir(root, borough))

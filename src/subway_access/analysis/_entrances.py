"""Lightweight summaries over ``EntranceDataset`` for analysis workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import EntranceDataset, GtfsPathwaysSnapshot


def entrances_per_gtfs_stop_id(dataset: EntranceDataset) -> dict[str, int]:
    """Return entrance counts keyed by GTFS parent stop id."""

    return dataset.count_by_gtfs_stop_id()


def entrances_per_complex_id(dataset: EntranceDataset) -> dict[str, int]:
    """Return entrance counts keyed by station complex id."""

    return dataset.count_by_complex_id()


def pathways_and_locations_counts(
    snapshot: GtfsPathwaysSnapshot | None,
) -> tuple[int, int]:
    """Return (pathway row count, location row count) for optional GTFS-Pathways data."""

    if snapshot is None:
        return (0, 0)
    return (len(snapshot.pathways), len(snapshot.locations))

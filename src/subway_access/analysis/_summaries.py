"""Grouped summary helpers for ``subway-access`` outputs."""

from __future__ import annotations

from collections import defaultdict
from statistics import fmean

from ..models import (
    AccessibilityScoreDataset,
    AccessibilitySummaryDataset,
    AccessibilitySummaryRecord,
)


def summarize_accessibility_by_group(
    scored_data: AccessibilityScoreDataset,
    *,
    group_by: str = "borough",
) -> AccessibilitySummaryDataset:
    """Summarize tract accessibility results by a record attribute.

    Groups scored tracts by the given attribute and computes aggregate
    coverage rates, population counts, need scores, and travel times.

    Args:
        scored_data: Tract accessibility scores from ``score_accessibility``.
        group_by: Attribute name to group by (default ``"borough"``).

    Returns:
        An ``AccessibilitySummaryDataset`` with one record per group.

    Example:
        >>> summary = summarize_accessibility_by_group(scores, group_by="borough")
        >>> summary.records[0].coverage_rate
        0.72
    """

    grouped = defaultdict(list)
    for record in scored_data.records:
        grouped[str(getattr(record, group_by))].append(record)

    summary_records = []
    for group_value, records in sorted(grouped.items()):
        covered = [record for record in records if record.has_accessible_station]
        uncovered = [record for record in records if not record.has_accessible_station]
        covered_population = sum(record.total_population for record in covered)
        total_population = sum(record.total_population for record in records)
        travel_minutes = [
            record.nearest_accessible_travel_minutes
            for record in records
            if record.nearest_accessible_travel_minutes is not None
        ]
        summary_records.append(
            AccessibilitySummaryRecord(
                group_by=group_by,
                group_value=group_value,
                tract_count=len(records),
                covered_tract_count=len(covered),
                uncovered_tract_count=len(uncovered),
                total_population=total_population,
                covered_population=covered_population,
                uncovered_population=total_population - covered_population,
                mean_need_score=fmean(record.need_score for record in records),
                mean_nearest_travel_minutes=None
                if not travel_minutes
                else fmean(travel_minutes),
                coverage_rate=0.0 if not records else len(covered) / len(records),
            )
        )
    return AccessibilitySummaryDataset(records=tuple(summary_records))

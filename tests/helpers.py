from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from subway_access import analysis, models, pipeline

TEST_DATA_DIR = Path(__file__).resolve().parent / "data" / "real_snapshot"


@dataclass(frozen=True)
class SnapshotBundle:
    """Typed bundle built from the committed real-data test snapshot."""

    snapshot: models.StudyAreaSnapshot
    catchments: models.CatchmentDataset
    scores: models.AccessibilityScoreDataset
    gaps: models.GapAnalysis
    reliability: models.ReliabilityDataset
    station_metrics: models.StationMetricDataset


def build_snapshot_bundle(*, minutes: int = 10, reliability_days: int = 365) -> SnapshotBundle:
    snapshot = pipeline.load_cached_snapshot(TEST_DATA_DIR)
    catchments = analysis.generate_catchments(
        snapshot.stations,
        models.CatchmentRequest(minutes=minutes),
    )
    scores = analysis.score_accessibility(
        snapshot.stations,
        catchments,
        snapshot.demographics,
    )
    gaps = analysis.analyze_gaps(scores)
    reliability = analysis.compute_reliability(
        snapshot.stations,
        snapshot.outages,
        models.TimeWindow(days=reliability_days),
    )
    station_metrics = analysis.build_station_metrics(
        snapshot.stations,
        catchments,
        scores,
        reliability=reliability,
    )
    return SnapshotBundle(
        snapshot=snapshot,
        catchments=catchments,
        scores=scores,
        gaps=gaps,
        reliability=reliability,
        station_metrics=station_metrics,
    )

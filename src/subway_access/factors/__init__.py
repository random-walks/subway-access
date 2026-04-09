"""Composable factor pipeline for accessibility analysis."""

from __future__ import annotations

from ._base import Factor, FactorContext, Pipeline, PipelineResult
from ._builtin import (
    CoverageFactor,
    GapScoreFactor,
    NearestStationDistanceFactor,
    NearestStationTravelMinutesFactor,
    NeedScoreFactor,
    ReliabilityWeightedCoverageFactor,
    StationCountFactor,
)

__all__ = [
    "CoverageFactor",
    "Factor",
    "FactorContext",
    "GapScoreFactor",
    "NearestStationDistanceFactor",
    "NearestStationTravelMinutesFactor",
    "NeedScoreFactor",
    "Pipeline",
    "PipelineResult",
    "ReliabilityWeightedCoverageFactor",
    "StationCountFactor",
]

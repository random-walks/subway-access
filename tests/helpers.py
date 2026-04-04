from __future__ import annotations

from dataclasses import dataclass

from subway_access import analysis, io, models


@dataclass(frozen=True)
class DemoBundle:
    """Typed bundle of the sample-backed subway-access workflow."""

    stations: models.StationDataset
    demographics: models.DemographicDataset
    outages: models.OutageDataset
    pedestrian_network: models.PedestrianNetworkDataset
    catchments: models.CatchmentDataset
    scores: models.AccessibilityScoreDataset
    gaps: models.GapAnalysis
    reliability: models.ReliabilityDataset
    station_metrics: models.StationMetricDataset


def build_demo_bundle(
    *,
    minutes: int = 10,
    reliability_days: int = 30,
) -> DemoBundle:
    stations = io.load_gtfs().with_accessibility(io.load_accessibility_status())
    demographics = io.load_census_data()
    outages = io.load_outages()
    pedestrian_network = io.load_pedestrian_network()
    catchments = analysis.generate_catchments(
        stations,
        models.CatchmentRequest(minutes=minutes),
    )
    scores = analysis.score_accessibility(stations, catchments, demographics)
    gaps = analysis.analyze_gaps(scores)
    reliability = analysis.compute_reliability(
        stations,
        outages,
        models.TimeWindow(days=reliability_days),
    )
    station_metrics = analysis.build_station_metrics(
        stations,
        catchments,
        scores,
        reliability=reliability,
        pedestrian_network=pedestrian_network,
    )
    return DemoBundle(
        stations=stations,
        demographics=demographics,
        outages=outages,
        pedestrian_network=pedestrian_network,
        catchments=catchments,
        scores=scores,
        gaps=gaps,
        reliability=reliability,
        station_metrics=station_metrics,
    )

"""Analysis steps for the refactored ``subway-access`` workflow."""

from __future__ import annotations

from statistics import fmean

from ..models import (
    AccessibilityDataset,
    AccessibilityLabel,
    AccessibilityScoreDataset,
    CatchmentDataset,
    CatchmentFeature,
    CatchmentRequest,
    DemographicDataset,
    GapAnalysis,
    GapRecord,
    OutageDataset,
    PedestrianNetworkDataset,
    ReliabilityDataset,
    ReliabilityRecord,
    StationDataset,
    StationMetricDataset,
    StationMetricRecord,
    TimeWindow,
)
from ._geo import build_circle_polygon, walk_radius_meters


def generate_catchments(
    station_data: StationDataset,
    request: CatchmentRequest,
) -> CatchmentDataset:
    """Generate first-pass Euclidean catchments for a walk threshold.

    Args:
        station_data: Loaded station rows for the study area.
        request: Catchment parameters (walk minutes, mode).

    Returns:
        A ``CatchmentDataset`` with one circular polygon per station.

    Example:
        >>> catchments = generate_catchments(
        ...     stations, models.CatchmentRequest(minutes=10)
        ... )
    """

    radius_meters = walk_radius_meters(request.minutes)
    features = tuple(
        CatchmentFeature(
            station_id=station.station_id,
            station_name=station.name,
            borough=station.borough,
            ada_status=station.ada_status,
            center_latitude=station.latitude,
            center_longitude=station.longitude,
            radius_meters=radius_meters,
            minutes=request.minutes,
            method="euclidean-buffer-v0.2",
            polygon=build_circle_polygon(
                latitude=station.latitude,
                longitude=station.longitude,
                radius_meters=radius_meters,
            ),
        )
        for station in station_data.stations
    )
    return CatchmentDataset(features=features)


def score_accessibility(
    station_data: StationDataset,
    catchments: CatchmentDataset,
    demographics: DemographicDataset,
) -> AccessibilityScoreDataset:
    """Score tract accessibility using station, catchment, and demographic inputs.

    For each tract, tests whether its centroid falls within any accessible
    station's catchment radius and computes a composite need score.

    Args:
        station_data: Loaded station rows with ADA status.
        catchments: Generated catchment geometries.
        demographics: Tract-level demographic data.

    Returns:
        An ``AccessibilityScoreDataset`` with one record per tract.

    Example:
        >>> scores = score_accessibility(stations, catchments, demographics)
        >>> scores.records[0].has_accessible_station
        True
    """

    from ..factors._compat import score_tracts_via_factors

    records = score_tracts_via_factors(station_data, catchments, demographics)
    return AccessibilityScoreDataset(records=records)


def analyze_gaps(scored_data: AccessibilityScoreDataset) -> GapAnalysis:
    """Identify tracts with high need and weak accessible station coverage.

    Classifies each tract as ``"covered"`` or ``"gap"`` based on whether
    it has at least one accessible station in its catchment. Gap score
    is 0.0 for covered tracts, or the need score for uncovered tracts.

    Args:
        scored_data: Tract accessibility scores from ``score_accessibility``.

    Returns:
        A ``GapAnalysis`` with records sorted by gap score descending.

    Example:
        >>> gaps = analyze_gaps(scores)
        >>> gaps.records[0].gap_label
        'gap'
    """

    records = tuple(
        sorted(
            (
                GapRecord(
                    tract_id=record.tract_id,
                    tract_name=record.tract_name,
                    borough=record.borough,
                    disability_rate=record.disability_rate,
                    senior_rate=record.senior_rate,
                    poverty_rate=record.poverty_rate,
                    total_population=record.total_population,
                    need_score=record.need_score,
                    has_accessible_station=record.has_accessible_station,
                    accessible_station_count=record.accessible_station_count,
                    nearest_accessible_station_id=record.nearest_accessible_station_id,
                    nearest_accessible_station_name=record.nearest_accessible_station_name,
                    nearest_accessible_distance_meters=record.nearest_accessible_distance_meters,
                    gap_score=0.0
                    if record.has_accessible_station
                    else record.need_score,
                    gap_label="covered" if record.has_accessible_station else "gap",
                )
                for record in scored_data.records
            ),
            key=lambda record: (-record.gap_score, record.tract_id),
        )
    )
    return GapAnalysis(records=records)


def _reliability_label(*, score: float, ada_status: AccessibilityLabel) -> str:
    if ada_status == "not_accessible":
        return "not_accessible"
    if ada_status == "partially_accessible":
        return "partial_access"
    if ada_status == "unknown":
        return "unknown"
    if score >= 0.995:
        return "full_service"
    if score >= 0.98:
        return "strong"
    if score >= 0.95:
        return "at_risk"
    return "fragile"


def _station_metadata(
    accessibility_data: StationDataset | AccessibilityDataset,
) -> tuple[
    dict[str, AccessibilityLabel],
    dict[str, str | None],
    dict[str, str | None],
]:
    status_by_station: dict[str, AccessibilityLabel] = {}
    names_by_station: dict[str, str | None] = {}
    boroughs_by_station: dict[str, str | None] = {}
    if isinstance(accessibility_data, StationDataset):
        for station in accessibility_data.stations:
            status_by_station[station.station_id] = station.ada_status
            names_by_station[station.station_id] = station.name
            boroughs_by_station[station.station_id] = station.borough
    else:
        for status in accessibility_data.statuses:
            status_by_station[status.station_id] = status.ada_status
            names_by_station[status.station_id] = None
            boroughs_by_station[status.station_id] = None
    return status_by_station, names_by_station, boroughs_by_station


def compute_reliability(
    accessibility_data: StationDataset | AccessibilityDataset,
    outage_data: OutageDataset,
    window: TimeWindow,
) -> ReliabilityDataset:
    """Compute a rolling station reliability score from outage history.

    For each station, calculates the fraction of the time window that
    was outage-free and assigns a reliability label.

    Args:
        accessibility_data: Station or accessibility dataset with ADA status.
        outage_data: Loaded outage events.
        window: Rolling time window (e.g. 30 days, 365 days).

    Returns:
        A ``ReliabilityDataset`` with one record per station.

    Example:
        >>> reliability = compute_reliability(
        ...     stations, outages, models.TimeWindow(days=30)
        ... )
    """

    status_by_station, names_by_station, boroughs_by_station = _station_metadata(
        accessibility_data
    )
    as_of = outage_data.recommended_as_of()
    outage_minutes = outage_data.outage_minutes_by_station(window, as_of=as_of)
    outage_counts = outage_data.outage_count_by_station(window, as_of=as_of)
    total_outages = outage_data.outage_total_by_station(window, as_of=as_of)
    scheduled_outages = outage_data.scheduled_outage_total_by_station(
        window,
        as_of=as_of,
    )
    unscheduled_outages = outage_data.unscheduled_outage_total_by_station(
        window,
        as_of=as_of,
    )
    availability_ratios = outage_data.mean_availability_ratio_by_station(
        window,
        as_of=as_of,
    )
    station_ids = sorted(
        set(status_by_station)
        | set(outage_minutes)
        | set(outage_counts)
        | set(total_outages)
        | set(scheduled_outages)
        | set(unscheduled_outages)
    )
    total_minutes = window.total_minutes

    records = []
    for station_id in station_ids:
        ada_status = status_by_station.get(station_id, "unknown")
        total_outage_minutes = min(outage_minutes.get(station_id, 0), total_minutes)
        outage_count = outage_counts.get(station_id, 0)
        reliability_score = (
            0.0
            if ada_status != "accessible"
            else max(total_minutes - total_outage_minutes, 0) / total_minutes
        )
        records.append(
            ReliabilityRecord(
                station_id=station_id,
                station_name=names_by_station.get(station_id),
                borough=boroughs_by_station.get(station_id),
                ada_status=ada_status,
                outage_count=outage_count,
                outage_minutes=total_outage_minutes,
                window_days=window.days,
                reliability_score=reliability_score,
                reliability_label=_reliability_label(
                    score=reliability_score,
                    ada_status=ada_status,
                ),
                total_outages=total_outages.get(station_id, 0),
                scheduled_outages=scheduled_outages.get(station_id, 0),
                unscheduled_outages=unscheduled_outages.get(station_id, 0),
                mean_availability_ratio=availability_ratios.get(station_id),
            )
        )

    return ReliabilityDataset(records=tuple(records))


def build_station_metrics(
    station_data: StationDataset,
    catchments: CatchmentDataset,
    scored_data: AccessibilityScoreDataset,
    *,
    reliability: ReliabilityDataset | None = None,
    pedestrian_network: PedestrianNetworkDataset | None = None,
    analysis_method: str = "euclidean",
) -> StationMetricDataset:
    """Aggregate station-level metrics for reporting and export.

    Combines coverage counts, population served, need scores, and
    optional reliability data into one record per station.

    Args:
        station_data: Loaded station rows.
        catchments: Generated catchment geometries.
        scored_data: Tract accessibility scores.
        reliability: Optional reliability dataset for score/label inclusion.
        pedestrian_network: Optional pedestrian network for connection counts.
        analysis_method: Label for the analysis method used.

    Returns:
        A ``StationMetricDataset`` with one record per station.

    Example:
        >>> metrics = build_station_metrics(
        ...     stations, catchments, scores, reliability=reliability
        ... )
    """

    reliability_by_station = {} if reliability is None else reliability.as_mapping()
    network_counts = (
        {}
        if pedestrian_network is None
        else pedestrian_network.connection_count_by_station()
    )
    catchment_by_station = {
        feature.station_id: feature for feature in catchments.features
    }

    records: list[StationMetricRecord] = []
    for station in station_data.stations:
        covered = [
            record
            for record in scored_data.records
            if station.station_id in record.covering_station_ids
        ]
        nearby_gap_records = [
            record
            for record in scored_data.records
            if (
                record.nearest_accessible_station_id == station.station_id
                and not record.has_accessible_station
            )
        ]
        mean_need_score = (
            fmean([record.need_score for record in covered]) if covered else 0.0
        )
        reliability_record = reliability_by_station.get(station.station_id)
        catchment = catchment_by_station.get(station.station_id)
        if catchment is None:
            message = f"Missing catchment for station {station.station_id}."
            raise ValueError(message)

        records.append(
            StationMetricRecord(
                station_id=station.station_id,
                station_name=station.name,
                borough=station.borough,
                latitude=station.latitude,
                longitude=station.longitude,
                ada_status=station.ada_status,
                catchment_minutes=catchment.minutes,
                catchment_radius_meters=catchment.radius_meters,
                covered_tract_count=len(covered),
                covered_population=sum(record.total_population for record in covered),
                nearby_gap_tract_count=len(nearby_gap_records),
                nearby_gap_population=sum(
                    record.total_population for record in nearby_gap_records
                ),
                mean_need_score=mean_need_score,
                reliability_score=None
                if reliability_record is None
                else reliability_record.reliability_score,
                reliability_label=None
                if reliability_record is None
                else reliability_record.reliability_label,
                outage_minutes=None
                if reliability_record is None
                else reliability_record.outage_minutes,
                network_connection_count=network_counts.get(station.station_id, 0),
                daytime_routes=station.daytime_routes,
                structure=station.structure,
                analysis_method=analysis_method,
            )
        )

    return StationMetricDataset(records=tuple(records))

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
    TractAccessibilityRecord,
)
from ._geo import build_circle_polygon, haversine_distance_meters, walk_radius_meters


def generate_catchments(
    station_data: StationDataset,
    request: CatchmentRequest,
) -> CatchmentDataset:
    """Generate first-pass Euclidean catchments for a walk threshold."""

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
    """Score tract accessibility using station, catchment, and demographic inputs."""

    radius_by_station_id = catchments.radius_by_station_id()
    accessible_stations = station_data.accessible_stations

    records: list[TractAccessibilityRecord] = []
    for tract in demographics.tracts:
        covering_station_ids: list[str] = []
        nearest_station_id: str | None = None
        nearest_station_name: str | None = None
        nearest_distance: float | None = None

        for station in accessible_stations:
            distance = haversine_distance_meters(
                latitude_a=tract.centroid_latitude,
                longitude_a=tract.centroid_longitude,
                latitude_b=station.latitude,
                longitude_b=station.longitude,
            )
            if nearest_distance is None or distance < nearest_distance:
                nearest_distance = distance
                nearest_station_id = station.station_id
                nearest_station_name = station.name

            if distance <= radius_by_station_id[station.station_id]:
                covering_station_ids.append(station.station_id)

        need_score = fmean(
            (tract.disability_rate, tract.senior_rate, tract.poverty_rate)
        )
        records.append(
            TractAccessibilityRecord(
                tract_id=tract.tract_id,
                tract_name=tract.tract_name,
                borough=tract.borough,
                centroid_latitude=tract.centroid_latitude,
                centroid_longitude=tract.centroid_longitude,
                disability_rate=tract.disability_rate,
                senior_rate=tract.senior_rate,
                poverty_rate=tract.poverty_rate,
                total_population=tract.total_population,
                need_score=need_score,
                has_accessible_station=bool(covering_station_ids),
                accessible_station_count=len(covering_station_ids),
                covering_station_ids=tuple(covering_station_ids),
                nearest_accessible_station_id=nearest_station_id,
                nearest_accessible_station_name=nearest_station_name,
                nearest_accessible_distance_meters=nearest_distance,
            )
        )

    return AccessibilityScoreDataset(records=tuple(records))


def analyze_gaps(scored_data: AccessibilityScoreDataset) -> GapAnalysis:
    """Identify tracts with high need and weak accessible station coverage."""

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
    """Compute a rolling station reliability score from outage history."""

    status_by_station, names_by_station, boroughs_by_station = _station_metadata(
        accessibility_data
    )
    as_of = outage_data.recommended_as_of()
    outage_minutes = outage_data.outage_minutes_by_station(window, as_of=as_of)
    outage_counts = outage_data.outage_count_by_station(window, as_of=as_of)
    station_ids = sorted(set(status_by_station) | set(outage_minutes) | set(outage_counts))
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
) -> StationMetricDataset:
    """Aggregate station-level metrics for reporting and export."""

    reliability_by_station = {} if reliability is None else reliability.as_mapping()
    network_counts = (
        {}
        if pedestrian_network is None
        else pedestrian_network.connection_count_by_station()
    )
    catchment_by_station = {feature.station_id: feature for feature in catchments.features}

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
        mean_need_score = fmean([record.need_score for record in covered]) if covered else 0.0
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
            )
        )

    return StationMetricDataset(records=tuple(records))

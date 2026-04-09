"""Panel dataset construction from multi-vintage snapshots."""

from __future__ import annotations

from statistics import fmean
from typing import TYPE_CHECKING

from ..analysis._geo import haversine_distance_meters
from ._models import PanelDataset, PanelObservation

if TYPE_CHECKING:
    from ._models import UpgradeTimeline


def build_panel_dataset(
    vintage_estimates: dict[int, dict[str, dict[str, object]]],
    station_locations: dict[str, tuple[float, float]],
    upgrade_timeline: UpgradeTimeline,
    *,
    catchment_radius_meters: float = 800.0,
    unit_type: str = "tract",
    extra_covariates: dict[int, dict[str, dict[str, float]]] | None = None,
) -> PanelDataset:
    """Construct a geographic panel dataset from multi-vintage ACS estimates.

    Joins demographic estimates across vintage years with station accessibility
    status (derived from the upgrade timeline) to produce a panel suitable for
    difference-in-differences or spatial panel regression.

    Args:
        vintage_estimates: Nested mapping year -> tract_geoid -> estimate dict.
            Each estimate dict must have keys: disability_rate, senior_rate,
            poverty_rate, total_population.
        station_locations: Mapping of station_id -> (latitude, longitude) for
            all stations in the study area.
        upgrade_timeline: Station ADA upgrade records with year information.
        catchment_radius_meters: Maximum distance in meters for a tract to
            be considered "covered" by a station. Defaults to 800m (~10 min walk).
        unit_type: Geographic unit type label (``"tract"`` or ``"nta"``).
        extra_covariates: Optional nested mapping year -> tract_geoid -> dict
            of additional time-varying covariates (e.g. median_rent).

    Returns:
        A PanelDataset with one observation per (unit, period) pair.

    Example:
        >>> panel = build_panel_dataset(
        ...     vintage_estimates=multi_vintage,
        ...     station_locations=stations,
        ...     upgrade_timeline=timeline,
        ... )
        >>> len(panel.observations)
        1400
    """

    periods = tuple(str(year) for year in sorted(vintage_estimates))
    extras = extra_covariates or {}
    observations: list[PanelObservation] = []

    # Pre-compute which station_ids are accessible by each year.
    years = sorted(vintage_estimates)
    accessible_by_year: dict[int, set[str]] = {}
    for year in years:
        accessible_by_year[year] = set(upgrade_timeline.stations_upgraded_by(year))

    # Collect all tract_ids across all vintages.
    all_tract_ids: set[str] = set()
    for year_estimates in vintage_estimates.values():
        all_tract_ids.update(year_estimates)

    for tract_id in sorted(all_tract_ids):
        # Determine treatment year: earliest year this tract gains an accessible station.
        first_treatment_year: int | None = None

        for year in years:
            estimate = vintage_estimates[year].get(tract_id)
            if estimate is None:
                continue

            # Compute which accessible stations cover this tract.
            tract_lat = _safe_float(estimate.get("centroid_latitude"))
            tract_lon = _safe_float(estimate.get("centroid_longitude"))
            accessible_stations_in_year = accessible_by_year[year]

            covering_count = 0
            nearest_distance: float | None = None

            if tract_lat is not None and tract_lon is not None:
                for station_id, (slat, slon) in station_locations.items():
                    distance = haversine_distance_meters(
                        latitude_a=tract_lat,
                        longitude_a=tract_lon,
                        latitude_b=slat,
                        longitude_b=slon,
                    )
                    if station_id in accessible_stations_in_year:
                        if distance <= catchment_radius_meters:
                            covering_count += 1
                        if nearest_distance is None or distance < nearest_distance:
                            nearest_distance = distance

            has_accessible = covering_count > 0
            if has_accessible and first_treatment_year is None:
                first_treatment_year = year

            disability_rate = _safe_float(estimate.get("disability_rate")) or 0.0
            senior_rate = _safe_float(estimate.get("senior_rate")) or 0.0
            poverty_rate = _safe_float(estimate.get("poverty_rate")) or 0.0
            raw_pop = estimate.get("total_population")
            total_population = int(str(raw_pop)) if raw_pop is not None else 0

            year_extras = extras.get(year, {}).get(tract_id, {})

            observations.append(
                PanelObservation(
                    unit_id=tract_id,
                    period=str(year),
                    has_accessible_station=has_accessible,
                    treatment_year=first_treatment_year,
                    disability_rate=disability_rate,
                    senior_rate=senior_rate,
                    poverty_rate=poverty_rate,
                    total_population=total_population,
                    accessible_station_count=covering_count,
                    nearest_accessible_distance_m=nearest_distance,
                    need_score=fmean((disability_rate, senior_rate, poverty_rate)),
                    covariates=year_extras,
                )
            )

    return PanelDataset(
        observations=tuple(observations),
        unit_type=unit_type,
        periods=periods,
    )


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None

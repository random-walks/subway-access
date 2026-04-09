"""Typed models for temporal panel data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PanelObservation:
    """Single (unit x period) observation in the geographic panel.

    Args:
        unit_id: NTA code or census tract GEOID.
        period: ACS vintage year, e.g. ``"2019"``.
        has_accessible_station: Treatment indicator -- True if this unit
            gained at least one accessible station by this period.
        treatment_year: Year the first accessible station opened in
            this unit's catchment, or None if never treated.
        disability_rate: ACS 5-year estimate for this vintage.
        senior_rate: ACS 5-year estimate for this vintage.
        poverty_rate: ACS 5-year estimate for this vintage.
        total_population: ACS 5-year estimate for this vintage.
        accessible_station_count: Number of accessible stations in catchment.
        nearest_accessible_distance_m: Haversine distance to nearest
            accessible station, or None if none exist.
        need_score: Composite factor pipeline output.
        covariates: Extensible dict for additional time-varying covariates
            (median_rent, employment rate, etc.).

    Example:
        >>> obs = PanelObservation(
        ...     unit_id="36061000100", period="2020",
        ...     has_accessible_station=True, treatment_year=2019,
        ...     disability_rate=0.08, senior_rate=0.12, poverty_rate=0.15,
        ...     total_population=4500, accessible_station_count=2,
        ...     nearest_accessible_distance_m=320.0, need_score=0.117,
        ... )
    """

    unit_id: str
    period: str
    has_accessible_station: bool
    treatment_year: int | None
    disability_rate: float
    senior_rate: float
    poverty_rate: float
    total_population: int
    accessible_station_count: int
    nearest_accessible_distance_m: float | None
    need_score: float
    covariates: dict[str, float] | None = None


@dataclass(frozen=True, slots=True)
class PanelDataset:
    """Geographic panel: unit x time observations.

    Args:
        observations: All panel rows.
        unit_type: Geographic unit type (``"nta"`` or ``"tract"``).
        periods: Ordered tuple of period labels.

    Example:
        >>> panel.periods
        ('2017', '2018', '2019', '2020', '2021', '2022', '2023')
        >>> len(panel.observations)
        1400
    """

    observations: tuple[PanelObservation, ...]
    unit_type: str
    periods: tuple[str, ...]

    def treatment_group(self) -> PanelDataset:
        """Return only observations in units that were ever treated."""

        treated_units = {
            obs.unit_id for obs in self.observations if obs.treatment_year is not None
        }
        return PanelDataset(
            observations=tuple(
                obs for obs in self.observations if obs.unit_id in treated_units
            ),
            unit_type=self.unit_type,
            periods=self.periods,
        )

    def control_group(self) -> PanelDataset:
        """Return only observations in units that were never treated."""

        treated_units = {
            obs.unit_id for obs in self.observations if obs.treatment_year is not None
        }
        return PanelDataset(
            observations=tuple(
                obs for obs in self.observations if obs.unit_id not in treated_units
            ),
            unit_type=self.unit_type,
            periods=self.periods,
        )

    def to_dataframe(self) -> Any:
        """Convert to a pandas DataFrame with (unit_id, period) index.

        Returns:
            A pandas DataFrame.

        Raises:
            ImportError: If pandas is not installed.
        """

        try:
            import pandas as pd
        except ImportError as exc:
            message = (
                "pandas is required for to_dataframe(). "
                "Install it with: pip install subway-access[panel]"
            )
            raise ImportError(message) from exc

        rows: list[dict[str, Any]] = []
        for obs in self.observations:
            row: dict[str, Any] = {
                "unit_id": obs.unit_id,
                "period": obs.period,
                "has_accessible_station": obs.has_accessible_station,
                "treatment_year": obs.treatment_year,
                "disability_rate": obs.disability_rate,
                "senior_rate": obs.senior_rate,
                "poverty_rate": obs.poverty_rate,
                "total_population": obs.total_population,
                "accessible_station_count": obs.accessible_station_count,
                "nearest_accessible_distance_m": obs.nearest_accessible_distance_m,
                "need_score": obs.need_score,
                **(obs.covariates or {}),
            }
            rows.append(row)
        df = pd.DataFrame(rows)
        return df.set_index(["unit_id", "period"])

    @property
    def unit_ids(self) -> tuple[str, ...]:
        """Return sorted unique unit identifiers."""

        return tuple(sorted({obs.unit_id for obs in self.observations}))


@dataclass(frozen=True, slots=True)
class StationUpgradeRecord:
    """Record of a station's ADA upgrade timeline.

    Args:
        station_id: MTA station identifier.
        station_name: Human-readable station name.
        borough: NYC borough.
        latitude: Station latitude.
        longitude: Station longitude.
        upgrade_year: Year the station became ADA-accessible, or None.
        upgrade_source: Data source for the upgrade date.
    """

    station_id: str
    station_name: str
    borough: str
    latitude: float
    longitude: float
    upgrade_year: int | None
    upgrade_source: str = ""


@dataclass(frozen=True, slots=True)
class UpgradeTimeline:
    """Collection of station ADA upgrade records.

    Args:
        records: All station upgrade records.

    Example:
        >>> timeline.stations_upgraded_by(2020)
        ('S1', 'S2', 'S3')
    """

    records: tuple[StationUpgradeRecord, ...]

    def stations_upgraded_by(self, year: int) -> tuple[str, ...]:
        """Return station IDs upgraded on or before the given year."""

        return tuple(
            r.station_id
            for r in self.records
            if r.upgrade_year is not None and r.upgrade_year <= year
        )

    def upgrade_year_for(self, station_id: str) -> int | None:
        """Return the upgrade year for a specific station, or None."""

        for r in self.records:
            if r.station_id == station_id:
                return r.upgrade_year
        return None

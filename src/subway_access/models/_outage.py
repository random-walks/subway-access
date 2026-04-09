"""Outage, reliability, and time-window models."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from ._common import AccessibilityLabel, EquipmentType, OutageStatus, _coerce_utc


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """Rolling time window used for reliability calculations."""

    days: int

    def __post_init__(self) -> None:
        if self.days <= 0:
            message = "TimeWindow.days must be greater than zero."
            raise ValueError(message)

    @property
    def total_minutes(self) -> int:
        """Return the total minutes in the window."""

        return self.days * 24 * 60


@dataclass(frozen=True, slots=True)
class OutageRecord:
    """Single elevator or escalator outage event."""

    station_id: str
    equipment_id: str
    equipment_type: EquipmentType
    status: OutageStatus
    started_at: datetime
    ended_at: datetime | None
    description: str = ""
    source: str = ""
    station_complex_id: str | None = None
    total_outages: int | None = None
    scheduled_outages: int | None = None
    unscheduled_outages: int | None = None
    availability_ratio: float | None = None
    outage_minutes_override: int | None = None

    def overlap_minutes(
        self, window: TimeWindow, *, as_of: datetime | None = None
    ) -> int:
        """Return outage minutes that fall inside the supplied rolling window."""

        window_end = _coerce_utc(as_of or self.ended_at or self.started_at)
        event_start = _coerce_utc(self.started_at)
        event_end = _coerce_utc(self.ended_at or window_end)
        window_start = window_end - timedelta(days=window.days)
        overlap_start = max(event_start, window_start)
        overlap_end = min(event_end, window_end)
        if overlap_end <= overlap_start:
            return 0
        if self.outage_minutes_override is not None:
            total_duration_minutes = max(
                int((event_end - event_start).total_seconds() // 60),
                1,
            )
            overlap_duration_minutes = int(
                (overlap_end - overlap_start).total_seconds() // 60
            )
            return int(
                self.outage_minutes_override
                * (overlap_duration_minutes / total_duration_minutes)
            )
        return int((overlap_end - overlap_start).total_seconds() // 60)


@dataclass(frozen=True, slots=True)
class ReliabilityRecord:
    """Rolling reliability summary for a station."""

    station_id: str
    station_name: str | None
    borough: str | None
    ada_status: AccessibilityLabel
    outage_count: int
    outage_minutes: int
    window_days: int
    reliability_score: float
    reliability_label: str
    total_outages: int = 0
    scheduled_outages: int = 0
    unscheduled_outages: int = 0
    mean_availability_ratio: float | None = None


@dataclass(frozen=True, slots=True)
class OutageDataset:
    """Loaded outage events."""

    records: tuple[OutageRecord, ...]

    def outage_minutes_by_station(
        self, window: TimeWindow, *, as_of: datetime | None = None
    ) -> dict[str, int]:
        minutes_by_station: dict[str, int] = defaultdict(int)
        for record in self.records:
            minutes_by_station[record.station_id] += record.overlap_minutes(
                window,
                as_of=as_of,
            )
        return dict(minutes_by_station)

    def outage_count_by_station(
        self, window: TimeWindow, *, as_of: datetime | None = None
    ) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for record in self.records:
            if record.overlap_minutes(window, as_of=as_of) > 0:
                counts[record.station_id] += 1
        return dict(counts)

    def recommended_as_of(self) -> datetime | None:
        """Return the latest timestamp represented in the dataset."""

        timestamps = [
            _coerce_utc(timestamp)
            for record in self.records
            for timestamp in (record.started_at, record.ended_at)
            if timestamp is not None
        ]
        return max(timestamps) if timestamps else None

    def outage_total_by_station(
        self,
        window: TimeWindow,
        *,
        as_of: datetime | None = None,
    ) -> dict[str, int]:
        totals: dict[str, int] = defaultdict(int)
        for record in self.records:
            if record.overlap_minutes(window, as_of=as_of) > 0 and record.total_outages:
                totals[record.station_id] += record.total_outages
        return dict(totals)

    def scheduled_outage_total_by_station(
        self,
        window: TimeWindow,
        *,
        as_of: datetime | None = None,
    ) -> dict[str, int]:
        totals: dict[str, int] = defaultdict(int)
        for record in self.records:
            if (
                record.overlap_minutes(window, as_of=as_of) > 0
                and record.scheduled_outages
            ):
                totals[record.station_id] += record.scheduled_outages
        return dict(totals)

    def unscheduled_outage_total_by_station(
        self,
        window: TimeWindow,
        *,
        as_of: datetime | None = None,
    ) -> dict[str, int]:
        totals: dict[str, int] = defaultdict(int)
        for record in self.records:
            if (
                record.overlap_minutes(window, as_of=as_of) > 0
                and record.unscheduled_outages
            ):
                totals[record.station_id] += record.unscheduled_outages
        return dict(totals)

    def mean_availability_ratio_by_station(
        self,
        window: TimeWindow,
        *,
        as_of: datetime | None = None,
    ) -> dict[str, float]:
        sums: dict[str, float] = defaultdict(float)
        counts: dict[str, int] = defaultdict(int)
        for record in self.records:
            if (
                record.overlap_minutes(window, as_of=as_of) > 0
                and record.availability_ratio is not None
            ):
                sums[record.station_id] += record.availability_ratio
                counts[record.station_id] += 1
        return {
            station_id: sums[station_id] / counts[station_id]
            for station_id in sums
            if counts[station_id] > 0
        }


@dataclass(frozen=True, slots=True)
class ReliabilityDataset:
    """Rolling reliability results for stations."""

    records: tuple[ReliabilityRecord, ...]

    def as_mapping(self) -> dict[str, ReliabilityRecord]:
        return {record.station_id: record for record in self.records}

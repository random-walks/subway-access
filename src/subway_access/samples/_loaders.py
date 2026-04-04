"""Sample-data helpers for ``subway-access`` examples."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..io import (
    load_accessibility_status,
    load_census_data,
    load_gtfs,
    load_outages,
    load_pedestrian_network,
)

if TYPE_CHECKING:
    from ..models import (
        AccessibilityDataset,
        DemographicDataset,
        OutageDataset,
        PedestrianNetworkDataset,
        StationDataset,
    )


def load_sample_stations() -> StationDataset:
    """Load the packaged station fixture."""

    return load_gtfs()


def load_sample_accessibility() -> AccessibilityDataset:
    """Load the packaged accessibility fixture."""

    return load_accessibility_status()


def load_sample_demographics() -> DemographicDataset:
    """Load the packaged tract-demographics fixture."""

    return load_census_data()


def load_sample_outages() -> OutageDataset:
    """Load the packaged outage fixture."""

    return load_outages()


def load_sample_pedestrian_network() -> PedestrianNetworkDataset:
    """Load the packaged pedestrian-network fixture."""

    return load_pedestrian_network()

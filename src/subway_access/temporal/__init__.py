"""Temporal panel infrastructure for accessibility-over-time analysis."""

from __future__ import annotations

from ._acs_vintage import (
    AVAILABLE_VINTAGE_YEARS,
    fetch_acs_tract_estimates_for_year,
    fetch_multi_vintage_estimates,
)
from ._models import (
    PanelDataset,
    PanelObservation,
    StationUpgradeRecord,
    UpgradeTimeline,
)
from ._panel import build_panel_dataset
from ._spatial_weights import build_distance_weights, weights_to_pysal
from ._upgrade_timeline import (
    build_upgrade_timeline,
    load_known_upgrades,
    load_known_upgrades_from_dir,
)

__all__ = [
    "AVAILABLE_VINTAGE_YEARS",
    "PanelDataset",
    "PanelObservation",
    "StationUpgradeRecord",
    "UpgradeTimeline",
    "build_distance_weights",
    "build_panel_dataset",
    "build_upgrade_timeline",
    "fetch_acs_tract_estimates_for_year",
    "fetch_multi_vintage_estimates",
    "load_known_upgrades",
    "load_known_upgrades_from_dir",
    "weights_to_pysal",
]

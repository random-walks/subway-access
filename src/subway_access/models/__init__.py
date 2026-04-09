"""Public typed models for ``subway-access``."""

from __future__ import annotations

from ._common import (
    AccessibilityLabel,
    AccessibilityQuery,
    EquipmentType,
    OutageStatus,
)
from ._entrance import (
    Entrance,
    EntranceDataset,
    GtfsLocation,
    GtfsPathway,
    GtfsPathwaysSnapshot,
)
from ._gap import (
    GapAnalysis,
    GapRecord,
)
from ._metric import (
    CatchmentDataset,
    CatchmentFeature,
    CatchmentRequest,
    StationMetricDataset,
    StationMetricRecord,
)
from ._network import (
    AccessibilityComparisonDataset,
    AccessibilityComparisonRecord,
    NetworkGraphSnapshot,
    PedestrianConnection,
    PedestrianNetworkDataset,
)
from ._outage import (
    OutageDataset,
    OutageRecord,
    ReliabilityDataset,
    ReliabilityRecord,
    TimeWindow,
)
from ._snapshot import (
    AccessibilitySummaryDataset,
    AccessibilitySummaryRecord,
    DataSourceMetadata,
    ExportTarget,
    StudyAreaSnapshot,
)
from ._station import (
    AccessibilityDataset,
    AccessibilityStatus,
    Station,
    StationDataset,
)
from ._tract import (
    AccessibilityScoreDataset,
    DemographicDataset,
    TractAccessibilityRecord,
    TractDemographics,
)

__all__ = [
    "AccessibilityComparisonDataset",
    "AccessibilityComparisonRecord",
    "AccessibilityDataset",
    "AccessibilityLabel",
    "AccessibilityQuery",
    "AccessibilityScoreDataset",
    "AccessibilityStatus",
    "AccessibilitySummaryDataset",
    "AccessibilitySummaryRecord",
    "CatchmentDataset",
    "CatchmentFeature",
    "CatchmentRequest",
    "DataSourceMetadata",
    "DemographicDataset",
    "Entrance",
    "EntranceDataset",
    "EquipmentType",
    "ExportTarget",
    "GapAnalysis",
    "GapRecord",
    "GtfsLocation",
    "GtfsPathway",
    "GtfsPathwaysSnapshot",
    "NetworkGraphSnapshot",
    "OutageDataset",
    "OutageRecord",
    "OutageStatus",
    "PedestrianConnection",
    "PedestrianNetworkDataset",
    "ReliabilityDataset",
    "ReliabilityRecord",
    "Station",
    "StationDataset",
    "StationMetricDataset",
    "StationMetricRecord",
    "StudyAreaSnapshot",
    "TimeWindow",
    "TractAccessibilityRecord",
    "TractDemographics",
]

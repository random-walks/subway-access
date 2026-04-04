"""Public loader entry points for ``subway-access``."""

from __future__ import annotations

from ._acs import (
    ACS_5YEAR_YEAR,
    fetch_nyc_acs_tract_estimates,
)
from ._cache import cache_timestamp, ensure_directory, write_csv_rows, write_json
from ._core import (
    load_accessibility_status,
    load_census_data,
    load_gtfs,
    load_outages,
    load_pedestrian_network,
)
from ._mta import (
    MTA_ELEVATOR_AVAILABILITY_API_URL,
    MTA_EQUIPMENT_ASSET_API_URL,
    MTA_GTFS_STATIC_URL,
    MTA_SUBWAY_STATIONS_API_URL,
    build_outage_snapshot_rows,
    build_station_snapshot_rows,
    fetch_mta_availability_history,
    fetch_mta_equipment_assets,
    fetch_mta_gtfs_archive,
    fetch_mta_station_catalog,
)
from ._osm import OSM_SOURCE_URL, fetch_walk_graph, load_cached_walk_graph

__all__ = [
    "ACS_5YEAR_YEAR",
    "MTA_ELEVATOR_AVAILABILITY_API_URL",
    "MTA_EQUIPMENT_ASSET_API_URL",
    "MTA_GTFS_STATIC_URL",
    "MTA_SUBWAY_STATIONS_API_URL",
    "OSM_SOURCE_URL",
    "build_outage_snapshot_rows",
    "build_station_snapshot_rows",
    "cache_timestamp",
    "ensure_directory",
    "fetch_mta_availability_history",
    "fetch_mta_equipment_assets",
    "fetch_mta_gtfs_archive",
    "fetch_mta_station_catalog",
    "fetch_nyc_acs_tract_estimates",
    "fetch_walk_graph",
    "load_accessibility_status",
    "load_cached_walk_graph",
    "load_census_data",
    "load_gtfs",
    "load_outages",
    "load_pedestrian_network",
    "write_csv_rows",
    "write_json",
]

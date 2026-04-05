# Architecture

`subway-access` is organized as a small typed library with explicit subpackages
and a real-data snapshot workflow.

## Package Shape

- `subway_access.models`: typed data contracts for requests, datasets, and
  exports
- `subway_access.io`: file and URL loading entry points
- `subway_access.analysis`: catchment generation, scoring, gaps, reliability,
  and station metrics
- `subway_access.export`: GeoJSON and CSV outputs
- `subway_access.pipeline`: official-data fetch/cache helpers and snapshot
  loading
- `subway_access.cli`: installed real-data CLI workflows

## Current data flow

1. `pipeline.fetch_study_area_snapshot()` selects a study area through
   `nyc-geo-toolkit`.
2. The pipeline fetches official MTA station, equipment, and availability data.
3. The pipeline fetches MTA subway entrance/exit points and filters them to the
   study area (`entrances.geojson`). When a GTFS zip is present, it optionally
   parses GTFS-Pathways `pathways.txt` / `locations.txt` into
   `gtfs-pathways.json` when those files exist in the archive.
4. The pipeline fetches ACS tract-level demographics and writes cache files.
5. `pipeline.load_cached_snapshot()` loads those cache files back into typed
   datasets (including `EntranceDataset` and optional `GtfsPathwaysSnapshot`).
6. `analysis.generate_catchments()` builds first-pass circle polygons.
7. `pipeline.fetch_walk_graph()` can cache an OSM walking graph for the same
   study area.
8. `analysis.score_accessibility()` joins station coverage to tract demand.
9. `analysis.score_accessibility_network()` compares the Euclidean baseline to
   network travel.
10. `analysis.compute_reliability()` scores stations from public availability
    history.
11. `analysis.compare_accessibility_models()` and
    `analysis.summarize_accessibility_by_group()` produce richer rollups.
12. `analysis.analyze_gaps()` ranks uncovered tracts.
13. `analysis.build_station_metrics()` aggregates station-level metrics.
14. `export.export_catchments_geojson()`, `export.export_gap_table()`, and
    `export.export_station_metrics()` write outputs.

## Geography and shared foundations

The repo now centers on example-local cache directories rather than packaged
synthetic fixtures. The intended consumer pattern is:

- fetch official public records once
- pin a local cache snapshot
- optionally pin a local OSM walking graph
- reload it in memory for analysis and export
- update tracked reports intentionally, not implicitly

Reusable dependency-free geodesy helpers now live in `nyc-geo-toolkit`, while
the accessibility-specific scoring and transit-domain logic stays local to this
package.

## Planned expansion

The package now grows along two explicit tracks:

- Euclidean accessibility as a documented baseline
- network-based walking graphs and comparison outputs as the advanced path

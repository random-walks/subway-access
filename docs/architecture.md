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
- `subway_access.pipeline`: official-data fetch/cache helpers and snapshot loading
- `subway_access.cli`: installed real-data CLI workflows

## Current data flow

1. `pipeline.fetch_study_area_snapshot()` selects a study area through
   `nyc-geo-toolkit`.
2. The pipeline fetches official MTA station, equipment, and availability data.
3. The pipeline fetches ACS tract-level demographics and writes cache files.
4. `pipeline.load_cached_snapshot()` loads those cache files back into typed datasets.
5. `analysis.generate_catchments()` builds first-pass circle polygons.
6. `analysis.score_accessibility()` joins station coverage to tract demand.
7. `analysis.compute_reliability()` scores stations from public availability history.
8. `analysis.analyze_gaps()` ranks uncovered tracts.
9. `analysis.build_station_metrics()` aggregates station-level metrics.
10. `export.export_catchments_geojson()`, `export.export_gap_table()`, and
   `export.export_station_metrics()` write outputs.

## Geography and shared foundations

The repo now centers on example-local cache directories rather than packaged
synthetic fixtures. The intended consumer pattern is:

- fetch official public records once
- pin a local cache snapshot
- reload it in memory for analysis and export
- update tracked reports intentionally, not implicitly

Reusable dependency-free geodesy helpers now live in `nyc-geo-toolkit`, while
the accessibility-specific scoring and transit-domain logic stays local to this
package.

## Planned expansion

The near-term roadmap grows from Euclidean coverage toward:

- network-based walking catchments
- richer geography rollups
- true network-based isochrone generation

The package already supports official-data fetch/cache flows, while the heavier
network routing layer remains a distinct next step.

# Architecture

`subway-access` is organized as a small typed library with explicit subpackages
and a sample-backed analysis workflow.

## Package Shape

- `subway_access.models`: typed data contracts for requests, datasets, and
  exports
- `subway_access.io`: file and URL loading entry points
- `subway_access.analysis`: catchment generation, scoring, gaps, reliability,
  and station metrics
- `subway_access.export`: GeoJSON and CSV outputs
- `subway_access.samples`: packaged sample-data loaders for examples
- `subway_access.cli`: installed demo workflow

## Current data flow

1. `io.load_gtfs()` loads a narrow station table.
2. `io.load_accessibility_status()` loads ADA labels keyed by station ID.
3. `StationDataset.with_accessibility()` merges those two sources.
4. `io.load_census_data()` loads tract centroids and demographic rates.
5. `analysis.generate_catchments()` builds first-pass circle polygons.
6. `analysis.score_accessibility()` joins station coverage to tract demand.
7. `analysis.compute_reliability()` scores stations from outage history.
8. `analysis.analyze_gaps()` ranks uncovered tracts.
9. `analysis.build_station_metrics()` aggregates station-level metrics.
10. `export.export_catchments_geojson()`, `export.export_gap_table()`, and
   `export.export_station_metrics()` write outputs.

## Geography and shared foundations

The repo keeps packaged fixture inputs under `src/subway_access/data/fixtures/`
and exposes them through `subway_access.samples`. That layout is intentionally
aligned with the broader NYC package ecosystem in this workspace so packaged
resources, smoke tests, and repo-level examples follow the same pattern across
projects.

Reusable dependency-free geodesy helpers now live in `nyc-geo-toolkit`, while
the accessibility-specific scoring and transit-domain logic stays local to this
package.

## Planned expansion

The near-term roadmap still grows from Euclidean coverage toward:

- network-based walking catchments
- outage-aware reliability scoring
- richer geography rollups
- broader official-data ingestion
- true network-based isochrone generation

The current public surface is real and typed, but the heavier routing and live
data integrations remain deliberately modest.

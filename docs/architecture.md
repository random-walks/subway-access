# Architecture

`subway-access` is organized as a small typed library with one implemented
analysis path and a larger explicit roadmap.

## Package Shape

- `subway_access.loaders`: fixture and file loading entry points
- `subway_access.processors`: catchment generation, scoring, and gap analysis
- `subway_access.exporters`: GeoJSON and CSV outputs
- `subway_access.models`: typed data contracts for requests, datasets, and exports
- `subway_access.cli`: installed demo workflow

## Current data flow

1. `load_gtfs()` loads a narrow station table.
2. `load_accessibility_status()` loads ADA labels keyed by station ID.
3. `StationDataset.with_accessibility()` merges those two sources.
4. `generate_catchments()` builds first-pass circle polygons around stations.
5. `load_census_data()` loads tract centroids and demographic rates.
6. `score_accessibility()` joins station coverage to tract demand.
7. `analyze_gaps()` ranks uncovered tracts.
8. `export_catchments_geojson()` and `export_gap_table()` write outputs.

## Geography and shared foundations

The repo keeps packaged fixture inputs under `src/subway_access/data/fixtures/`.
That layout is intentionally aligned with the broader NYC package ecosystem in
this workspace so packaged resources, smoke tests, and docs examples follow the
same pattern across projects.

Reusable dependency-free geodesy helpers now live in `nyc-geo-toolkit`, while
the accessibility-specific scoring and transit-domain logic stays local to this
package.

## Planned expansion

The near-term roadmap grows from Euclidean coverage toward:

- network-based walking catchments
- outage-aware reliability scoring
- richer geography rollups
- broader official-data ingestion

Those surfaces stay importable but intentionally unimplemented until the code is
real.

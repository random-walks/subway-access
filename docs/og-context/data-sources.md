# Data Sources

## Current Official Inputs

- MTA Subway Stations dataset:
  `https://data.ny.gov/resource/39hk-dx4f.json`
- MTA GTFS static subway archive:
  `https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip`
- MTA Subway Elevator and Escalator Asset Inventory:
  `https://data.ny.gov/resource/94fv-bak7.json`
- MTA NYCT Subway Elevator and Escalator Availability: Beginning 2015:
  `https://data.ny.gov/resource/rc78-7x78.json`
- Census ACS 5-year tract counts:
  `https://api.census.gov/data/2023/acs/acs5`
- Census ACS 5-year tract subject tables:
  `https://api.census.gov/data/2023/acs/acs5/subject`

## Real Workflow Notes

- the station catalog is the easiest public source for station-level ADA flags,
  GTFS stop IDs, route labels, and station coordinates
- the public asset inventory and monthly availability history are auth-free and
  currently power reliability scoring
- the auth-gated real-time elevator/escalator current-outage feed still exists
  through the MTA developer program, but the public first-pass workflow uses the
  historical availability dataset instead
- ACS tract centroids are derived by joining Census estimates onto tract
  geometries packaged in `nyc-geo-toolkit`
- study-area selection should happen through `nyc-geo-toolkit` boundary layers,
  not ad-hoc borough lists or hand-written outlines

## Initial Data Principles

- prefer official or well-documented public sources
- document all joins between station, complex, stop, and tract identifiers
- preserve source URLs, refresh timestamps, and row counts in cache metadata

## Early Technical Notes

- the current public workflow still uses Euclidean catchments around station
  points rather than network isochrones
- station catalog `station_id` aligns most directly with elevator-history
  `station_mrn`; `complex_id` aligns with `station_complex_mrn`
- ADA values from the station catalog use `0`/`1`/`2` and should be documented
  as not accessible / accessible / partially accessible
- tract joins currently use tract centroids rather than full polygon overlap
- OSM-based pedestrian routing is the next layer, not the baseline model

## Documentation Follow-Up

## Refresh Cadence To Document

- station catalog and asset inventory refresh from the live public endpoints
- availability history should be snapshot-pinned with an explicit lookback window
- ACS release year should stay explicit in cache metadata and reports

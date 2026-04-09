# MVP Roadmap

## Implemented through v0.4

- fetch official MTA station catalog, ADA status, elevator/escalator
  availability history, equipment assets, street entrances, and GTFS-Pathways
  from live public APIs
- fetch ACS 5-year tract-level demographics (disability, senior, poverty rates)
- cache reusable local snapshot bundles per study area
- merge station and ADA status into typed station datasets
- create Euclidean catchments using a documented fixed walking speed
- generate OSM-network walk isochrones for comparison
- join tract-level disability, age, and poverty indicators
- compute tract accessibility gap scores
- compute rolling station reliability from outage history
- build station-level metrics combining coverage, need, and reliability
- export map-friendly GeoJSON, tract-level CSV, and station metric outputs
- composable factor pipeline (NeedScore, Coverage, GapScore,
  NearestStationDistance, StationCount, ReliabilityWeightedCoverage, and custom
  factors via subclassing)
- temporal panel infrastructure (multi-vintage ACS, upgrade timelines,
  treatment/control splitting, spatial weights)
- borough and group-level summary aggregation
- council district and community district study areas via `nyc-geo-toolkit`
- run the full workflow from the installed `subway-access` CLI
  (`fetch-snapshot` and `analyze-snapshot`)

## Still planned

- public-facing notebook and dashboard reporting
- fully polished public dashboard UX

## Non-Goals

- perfect routing realism
- advanced travel-time or multi-modal network analysis beyond walking

## Release Philosophy

The first release should prove the analytical frame clearly: reliable
accessibility is different from nominal accessibility, and that difference can
be measured with public data. The package now implements the full pipeline from
live data ingestion through research-grade panel analysis.

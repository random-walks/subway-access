# MVP Roadmap

## Implemented in v0.1 foundation

- load a small GTFS-like station fixture plus separate ADA status fixture
- merge station and ADA status into a typed station dataset
- create first-pass Euclidean catchments using a documented fixed walking speed
- join tract-level disability, age, and poverty indicators from a packaged
  GeoJSON fixture
- compute a basic tract accessibility gap score
- export map-friendly GeoJSON and tract-level CSV outputs
- run the real happy path with `subway-access demo --output-dir <path>`

## Still planned after v0.1

- direct ingestion from official live MTA feeds
- street-network isochrone catchments
- elevator and escalator outage integration
- historical reliability scoring
- council district and community district rollups
- public-facing notebook and dashboard reporting

## v0.1 Non-Goals

- perfect routing realism on day one
- advanced travel-time or network analysis
- claiming reliability modeling before outage history is implemented
- fully polished public dashboard UX

## Release Philosophy

The first release should prove the analytical frame clearly: reliable
accessibility is different from nominal accessibility, and that difference can
be measured with public data. This foundation intentionally implements only a
deterministic, fixture-backed happy path and leaves later ambitions as explicit
placeholders rather than partially faked features.

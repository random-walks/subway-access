# Data Sources

## Implemented In v0.1

- packaged synthetic station fixture in a GTFS-like CSV shape
- packaged synthetic ADA status fixture keyed by station ID
- packaged synthetic tract centroid GeoJSON with demographic rates

These fixtures are intentionally small and deterministic so the first release
can be tested end to end without requiring live feed access.

## Planned Official Inputs

- MTA static GTFS station and route data
- MTA elevator and escalator equipment feeds
- MTA current outage data
- official station accessibility datasets
- Census ACS tract-level demographic tables
- pedestrian network data from OpenStreetMap or other open street sources

## Initial Data Principles

- prefer official or well-documented public sources
- document all joins between station, complex, stop, and tract identifiers
- keep methodology explicit when historical outage data must be collected rather than downloaded as a clean archive

## Early Technical Notes

- v0.1 uses Euclidean catchments around station points rather than network
  isochrones
- outage history may require local persistence and collection strategy notes
- station naming crosswalks will matter early
- tract joins currently use tract centroids rather than full polygon overlap

## Documentation Follow-Up

As the package develops, this page should grow to include:

- exact feed URLs
- refresh cadence
- field notes for joins
- caveats around partial accessibility and directionality

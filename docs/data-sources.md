# Data Sources

## Primary Inputs

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

- first-pass catchments can be simpler than the eventual full network model
- outage history may require local persistence and collection strategy notes
- station naming crosswalks will matter early

## Documentation Follow-Up

As the package develops, this page should grow to include:

- exact feed URLs
- refresh cadence
- field notes for joins
- caveats around partial accessibility and directionality

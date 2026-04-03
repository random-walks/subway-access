# API overview

The public API now mixes a small implemented v0.1 slice with explicit typed
placeholders for planned later capabilities.

## Implemented in v0.1

- station loading from a narrow GTFS-like CSV fixture
- ADA status loading
- tract demographic loading from a centroid-based GeoJSON fixture
- Euclidean first-pass catchment generation
- tract accessibility scoring
- tract accessibility gap analysis
- GeoJSON catchment export
- CSV accessibility-gap export
- `subway-access demo` CLI workflow

## Still planned later

These callables remain intentionally unimplemented and continue to raise
`NotImplementedError`:

- outage loading
- pedestrian network loading
- reliability scoring
- station metrics export

That split is intentional: the public surface should stay honest about what is
real today versus still planned.

## Models

::: subway_access.models

## Loaders

::: subway_access.loaders

## Processors

::: subway_access.processors

## Exporters

::: subway_access.exporters

## CLI

::: subway_access.cli

# API overview

The public API spans 10 subpackages with 123 public symbols covering the full
data pipeline from live ingestion through research-grade analysis.

## Implemented

- station loading from official MTA station catalog API
- ADA status loading and merging
- elevator/escalator availability history and outage loading
- pedestrian network loading (CSV and GeoJSON)
- street entrance and GTFS-Pathways loading
- tract demographic loading from ACS 5-year estimates
- Euclidean and OSM-network walk catchment generation
- tract accessibility scoring via composable factor pipeline
- tract accessibility gap analysis
- rolling station reliability scoring from outage history
- station-level metrics combining coverage, need, and reliability
- borough and group-level summary aggregation
- GeoJSON catchment export, CSV gap export, and station metrics export
- `subway-access fetch-snapshot` and `subway-access analyze-snapshot` CLI
- temporal panel infrastructure for longitudinal analysis

## Models

::: subway_access.models

## IO

::: subway_access.io

## Analysis

::: subway_access.analysis

## Export

::: subway_access.export

## CLI

::: subway_access.cli

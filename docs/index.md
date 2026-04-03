# subway-access

`subway-access` is a Python toolkit for reproducible NYC subway accessibility
analysis.

It is designed to answer a practical question: which neighborhoods have weak
access to accessible stations today, and how can that gap be measured with a
small, transparent workflow?

## What ships now

The current `0.1` line provides one honest end-to-end slice:

- load a narrow GTFS-like station dataset
- load ADA accessibility status rows
- load tract-level demographic fixture data
- generate Euclidean first-pass walk catchments
- score tract accessibility coverage
- export GeoJSON and CSV outputs
- run the packaged demo from the installed `subway-access` CLI

## What does not ship yet

These surfaces remain explicit placeholders so the roadmap stays visible:

- outage ingestion
- pedestrian-network routing
- reliability scoring
- station-level metrics export

## Positioning

This package is not a trip planner. It is a transparent analysis toolkit for
policy, planning, journalism, and reproducible civic-tech workflows.

## Docs Paths

- Hosted docs:
  [subway-access.readthedocs.io](https://subway-access.readthedocs.io/)
- Local preview: `make docs`
- Strict docs build: `make docs-build`

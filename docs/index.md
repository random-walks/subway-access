# subway-access

`subway-access` is a Python toolkit for reproducible NYC subway accessibility
analysis.

Authored by [Blaise Albis-Burdige](https://blaiseab.com/).

It is designed to answer a practical question: which neighborhoods have weak
access to accessible stations today, and how can that gap be measured with a
small, transparent workflow?

## What ships now

The current package provides a real-data fetch/cache workflow:

- fetch official MTA station, equipment, and availability data
- fetch ACS tract-level demographics for a selected NYC study area
- cache a reusable local snapshot bundle
- run Euclidean first-pass accessibility and reliability analysis
- export GeoJSON and CSV outputs, including station metrics
- run the snapshot and analysis flow from the installed `subway-access` CLI

## Positioning

This package is not a trip planner. It is a transparent analysis toolkit for
policy, planning, journalism, and reproducible civic-tech workflows.

## Docs Paths

- Hosted docs:
  [subway-access.readthedocs.io](https://subway-access.readthedocs.io/)
- Local preview: `make docs`
- Strict docs build: `make docs-build`

## Choose Your Path

- Start with [Getting Started](getting-started.md) for installation and the
  first real snapshot run.
- Browse the repo-level `examples/` folders for report-rich consumer workflows.
- Use [CLI Reference](cli.md) for repeatable command-line usage.
- Use [Architecture](architecture.md) to understand the current data flow and
  shared geography boundaries.
- Use [Python API](api.md) for the complete public package surface.
- Use [Contributing](contributing.md) if you are maintaining or extending the
  repo.

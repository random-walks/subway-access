# subway-access

[![Actions Status][actions-badge]][actions-link]
[![Documentation Status][rtd-badge]][rtd-link]
[![PyPI version][pypi-version]][pypi-link]
[![PyPI platforms][pypi-platforms]][pypi-link]

`subway-access` is a Python toolkit for reproducible NYC subway accessibility
analysis.

Authored by [Blaise Albis-Burdige](https://blaiseab.com/).

It is designed to measure neighborhood access to accessible stations with a
small, transparent workflow that is easy to inspect, test, and extend.

## What ships in the `0.1` line

The current release deliberately implements one narrow, honest slice:

- load a small station dataset plus ADA status data
- generate first-pass Euclidean walk catchments
- join tract-level demographics
- export one tract accessibility-gap table plus catchment GeoJSON
- run the full fixture-backed workflow from the installed CLI

It does **not** pretend to ship outage-aware reliability scoring, pedestrian
network routing, or richer station-level metrics yet. Those surfaces remain
explicit typed placeholders that raise `NotImplementedError`.

## Why this exists

Official MTA and NYC data can tell you whether a station is nominally
accessible, but the policy question is broader: which neighborhoods have weak
access to accessible transit in practice?

This repo aims to grow into a reusable analysis toolkit rather than a notebook
dump or trip planner.

## Quickstart

Install:

```bash
pip install subway-access
```

Run the packaged demo workflow:

```bash
subway-access demo --output-dir demo-output --minutes 10
```

This writes:

- `demo-output/catchments.geojson`
- `demo-output/accessibility-gaps.csv`

## Python example

```python
from subway_access import (
    CatchmentRequest,
    analyze_gaps,
    generate_catchments,
    load_accessibility_status,
    load_census_data,
    load_gtfs,
    score_accessibility,
)

stations = load_gtfs().with_accessibility(load_accessibility_status())
demographics = load_census_data()
catchments = generate_catchments(stations, CatchmentRequest(minutes=10))
scores = score_accessibility(stations, catchments, demographics)
gaps = analyze_gaps(scores)
print(len(gaps.records))
```

## Current methodology

The implemented `0.1` workflow is intentionally simple and reproducible:

1. load stations and ADA status
2. create circular walk catchments using a fixed walking speed
3. test each tract centroid against accessible-station catchments
4. compute a tract need score from disability, senior, and poverty rates
5. assign a basic gap score when high-need tracts have no accessible station in
   catchment

This is intentionally a **first-pass Euclidean approximation**, not a network
isochrone model. Reliability-aware analysis remains future work.

## Documentation

- Hosted docs:
  [subway-access.readthedocs.io](https://subway-access.readthedocs.io/)
- Local preview: `make docs`
- Strict docs build: `make docs-build`

## Quick links

Docs: [Home](https://subway-access.readthedocs.io/en/latest/),
[Getting Started](https://subway-access.readthedocs.io/en/latest/getting-started/),
[CLI Reference](https://subway-access.readthedocs.io/en/latest/cli/),
[Architecture](https://subway-access.readthedocs.io/en/latest/architecture/),
[Python API](https://subway-access.readthedocs.io/en/latest/api/),
[Contributing](https://subway-access.readthedocs.io/en/latest/contributing/),
[Releasing](https://subway-access.readthedocs.io/en/latest/releasing/),
[Changelog](https://subway-access.readthedocs.io/en/latest/changelog/)

## Development

```bash
make install-dev
make test
make lint
make docs-build
make ci
```

## License

MIT.

<!-- prettier-ignore-start -->
[actions-badge]:            https://github.com/random-walks/subway-access/actions/workflows/ci.yml/badge.svg
[actions-link]:             https://github.com/random-walks/subway-access/actions
[github-discussions-badge]: https://img.shields.io/static/v1?label=Discussions&message=Ask&color=blue&logo=github
[github-discussions-link]:  https://github.com/random-walks/subway-access/discussions
[pypi-link]:                https://pypi.org/project/subway-access/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/subway-access
[pypi-version]:             https://img.shields.io/pypi/v/subway-access
[rtd-badge]:                https://readthedocs.org/projects/subway-access/badge/?version=latest
[rtd-link]:                 https://subway-access.readthedocs.io/en/latest/?badge=latest
<!-- prettier-ignore-end -->

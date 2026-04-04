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

## What ships in the current line

The current package now includes a full sample-backed analysis slice:

- load packaged station, ADA, tract, outage, and pedestrian-network fixtures
- generate first-pass Euclidean walk catchments
- score tract accessibility gaps
- compute rolling station reliability from outage history
- export catchment GeoJSON, tract gap CSV, and station metrics CSV or GeoJSON
- run the full workflow from the installed CLI

The routing model is still intentionally simple. Catchments remain Euclidean
buffers, while the pedestrian network is currently used for richer examples and
station-metrics context rather than full isochrone generation.

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
- `demo-output/station-metrics.csv`

## Examples

`examples/` now follows the same self-contained project pattern used by
`nyc311`. Each example folder has its own `pyproject.toml`, `README.md`,
`.gitignore`, `main.py`, and tracked `reports/` output.

Start with:

- `examples/quickstart-demo/`
- `examples/borough-gap-analysis/`
- `examples/catchment-map/`
- `examples/example-template/`

## Python example

```python
from subway_access import analysis, io, models

stations = io.load_gtfs().with_accessibility(io.load_accessibility_status())
demographics = io.load_census_data()
outages = io.load_outages()
catchments = analysis.generate_catchments(
    stations,
    models.CatchmentRequest(minutes=10),
)
scores = analysis.score_accessibility(stations, catchments, demographics)
reliability = analysis.compute_reliability(
    stations,
    outages,
    models.TimeWindow(days=30),
)
gaps = analysis.analyze_gaps(scores)
print(len(gaps.records), len(reliability.records))
```

## Current methodology

The current workflow is intentionally simple and reproducible:

1. load stations and ADA status
2. create circular walk catchments using a fixed walking speed
3. test each tract centroid against accessible-station catchments
4. compute a tract need score from disability, senior, and poverty rates
5. compute rolling reliability from outage events
6. assign a basic gap score when high-need tracts have no accessible station in
   catchment
7. aggregate station-level coverage and reliability metrics

This is intentionally a **first-pass Euclidean approximation**, not a full
network-isochrone model.

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

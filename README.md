# subway-access

[![Actions Status][actions-badge]][actions-link]
[![Documentation Status][rtd-badge]][rtd-link]
[![PyPI version][pypi-version]][pypi-link]
[![PyPI platforms][pypi-platforms]][pypi-link]

`subway-access` is a Python-first toolkit for making subway accessibility gaps
visible at the neighborhood level.

The v0.1 foundation deliberately implements only a narrow, honest slice of the
seeded vision:

- load a small station dataset plus ADA status data
- generate first-pass Euclidean walk catchments
- join tract-level demographics
- export one tract accessibility-gap table plus catchment GeoJSON

It does **not** pretend to ship advanced routing, travel-time modeling, or
reliability analysis yet. Those surfaces remain explicit typed placeholders that
raise `NotImplementedError`.

## Why this exists

Official MTA and NYC data can tell you whether a station is marked accessible,
and live feeds can tell you when equipment is out of service. What is much
harder to answer is whether neighborhoods with high disability, age, and
poverty burdens have good access to accessible stations in practice.

This project is meant to grow into a reusable analysis toolkit rather than a
one-off notebook or trip planner.

## Implemented now in v0.1

- `load_gtfs()` for a narrow GTFS-like station CSV
- `load_accessibility_status()` for station ADA status rows
- `load_census_data()` for tract centroid + demographic GeoJSON
- `generate_catchments()` using a documented Euclidean first pass
- `score_accessibility()` for tract-level joins against accessible stations
- `analyze_gaps()` for a basic tract accessibility-gap output
- `export_catchments_geojson()` and `export_gap_table()`
- `subway-access demo` CLI command backed by packaged fixture data

## Planned later

These public surfaces stay importable but intentionally fail loudly because they
are not honestly implemented yet:

- `load_outages()`
- `load_pedestrian_network()`
- `compute_reliability()`
- `export_station_metrics()`

## Methodology for the implemented slice

The current release uses a simple, deterministic methodology:

1. load stations and ADA status
2. mark missing ADA rows as `unknown`
3. create circular walk catchments using a fixed walking speed
4. test each tract centroid against accessible-station catchments
5. compute a tract need score from disability, senior, and poverty rates
6. assign a basic gap score when high-need tracts have no accessible station in
   catchment

This is intentionally a **first-pass Euclidean approximation**, not a network
isochrone model. The roadmap still treats pedestrian-network routing and outage
reliability as future work.

## Quickstart

Install in editable mode for development:

```bash
python -m pip install -e .
```

Run the packaged demo workflow:

```bash
python -m subway_access.cli demo --output-dir ./demo-output --minutes 10
```

This writes:

- `demo-output/catchments.geojson`
- `demo-output/accessibility-gaps.csv`

## Seeded sources of truth

The seeded docs remain the source of truth for scope and positioning:

- `docs/notes/original-spec.md`
- `docs/notes/gap-explination.md`
- `docs/mvp-roadmap.md`
- `docs/agent-kickoff-todo.md`

## Development

```bash
python -m pip install -e . pytest pytest-cov ruff mypy
python -m ruff check src tests
python -m mypy src tests
python -m pytest
python -m mkdocs build
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

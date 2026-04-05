# subway-access

[![Actions Status][actions-badge]][actions-link]
[![Documentation Status][rtd-badge]][rtd-link]
[![PyPI version][pypi-version]][pypi-link]
[![PyPI platforms][pypi-platforms]][pypi-link]

<!-- Hero: also at docs/images/subway-access-hero.png (relative path works on GitHub). PyPI needs absolute URL. -->

![NYC subway accessibility snapshot: street entrances, MTA stations, and ACS tract disability (example: Atlantic Brooklyn)](https://raw.githubusercontent.com/random-walks/subway-access/main/docs/images/subway-access-hero.png)

`subway-access` is a Python toolkit for reproducible NYC subway accessibility
analysis.

Authored by [Blaise Albis-Burdige](https://blaiseab.com/).

It is designed to measure neighborhood access to accessible stations with a
small, transparent workflow that is easy to inspect, cache, analyze in memory,
and extend.

## What ships in the current line

The current package now includes a real public-data workflow:

- fetch MTA subway stations and ADA status from the public station catalog
- fetch public elevator and escalator availability history plus asset inventory
- fetch ACS tract-level demographics for a selected NYC study area
- cache a reusable local snapshot bundle
- analyze Euclidean first-pass accessibility gaps and rolling reliability
- compare the Euclidean baseline against cached local OSM walking graphs
- export catchment GeoJSON, tract gap CSV, and station metrics
- run the snapshot and analysis flow from the installed CLI

The hero image above is committed as
[`docs/images/subway-access-hero.png`](docs/images/subway-access-hero.png)
(regenerated from [`examples/about-the-data`](examples/about-the-data/) as
`map-library-header-horizontal.png` when refreshing that example).

The current scoring model is intentionally staged:

- official public data is already real
- Euclidean catchments remain the baseline comparator
- cached OSM walking graphs now power the advanced network comparison layer

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

For the full plotting + network stack:

```bash
pip install "subway-access[all]"
```

Fetch a real official-data borough snapshot:

```bash
subway-access fetch-snapshot --geography borough --value Manhattan --cache-dir cache/manhattan
```

Then analyze the cached snapshot:

```bash
subway-access analyze-snapshot --cache-dir cache/manhattan --output-dir artifacts/manhattan
```

## Examples

`examples/` now follows the same self-contained project pattern used by
`nyc311`. Each example folder has its own `pyproject.toml`, `README.md`,
`.gitignore`, `main.py`, and tracked `reports/` output.

Start with:

- `examples/fetch-borough-snapshot/`
- `examples/borough-gap-analysis/`
- `examples/outage-reliability-report/`
- `examples/multi-borough-access-profile/`
- `examples/network-access-comparison/`
- `examples/example-template/`

## Python example

```python
from pathlib import Path

from subway_access import analysis, models, pipeline

snapshot = pipeline.fetch_study_area_snapshot(
    models.AccessibilityQuery(geography="borough", value="Manhattan"),
    cache_dir=Path("cache/manhattan"),
)
catchments = analysis.generate_catchments(
    snapshot.stations,
    models.CatchmentRequest(minutes=10),
)
scores = analysis.score_accessibility(
    snapshot.stations,
    catchments,
    snapshot.demographics,
)
reliability = analysis.compute_reliability(
    snapshot.stations,
    snapshot.outages,
    models.TimeWindow(days=30),
)
gaps = analysis.analyze_gaps(scores)
print(len(gaps.records), len(reliability.records))
```

## Current methodology

The current workflow is intentionally explicit and reproducible:

1. select a study area through `nyc-geo-toolkit`
2. fetch official MTA and Census sources into a local cache
3. load those cached files back into typed in-memory datasets
4. create Euclidean walk catchments using a fixed walking speed
5. test tract centroids against accessible-station catchments
6. compute tract need, rolling reliability, and station metrics
7. export publishable GeoJSON and CSV outputs

This is intentionally a staged model rather than a one-shot perfect routing
claim. Euclidean access remains the baseline, while the advanced examples now
show how cached OSM walking graphs change the story.

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

# subway-access

[![Actions Status][actions-badge]][actions-link]
[![Documentation Status][rtd-badge]][rtd-link]
[![PyPI version][pypi-version]][pypi-link]
[![PyPI platforms][pypi-platforms]][pypi-link]

<!-- Hero: also at docs/images/subway-access-hero.png (relative path works on GitHub). PyPI needs absolute URL. -->

![NYC subway accessibility snapshot: street entrances, MTA stations, and ACS tract disability (example: Atlantic Brooklyn)](https://raw.githubusercontent.com/random-walks/subway-access/main/docs/images/subway-access-hero.png)

`subway-access` is a Python toolkit for reproducible NYC subway accessibility
analysis. It fetches live MTA and Census data, scores every census tract for
accessible-station coverage, measures elevator reliability, and produces
research-ready panel datasets -- all from a single `pip install`.

Authored by [Blaise Albis-Burdige](https://blaiseab.com/).

## What ships in the package

**Data pipeline:**

- Fetch MTA subway stations, ADA status, elevator/escalator availability
  history, equipment assets, street-level entrances, and GTFS-Pathways from
  public APIs
- Fetch ACS 5-year tract-level demographics (disability, senior, poverty rates)
- Cache reusable local snapshot bundles per study area
- Run the full workflow from the installed `subway-access` CLI

**Analysis:**

- Euclidean and OSM-network walk catchments
- Tract-level accessibility gap scoring and rolling station reliability
- Station-level metrics combining coverage, need, and reliability
- Borough and group-level summary aggregation
- Export to GeoJSON, CSV, and station metric formats

**Composable factor pipeline** (v0.4):

- Class-based `Factor` / `Pipeline` system inspired by Quantopian's Zipline
- 7 built-in factors: NeedScore, Coverage, GapScore, NearestStationDistance,
  NearestStationTravelMinutes, StationCount, ReliabilityWeightedCoverage
- Custom factors via subclassing -- bring in external data (housing costs,
  economic indicators) as first-class inputs
- `PipelineResult` with `.to_records()` and optional `.to_dataframe()`

**Temporal panel infrastructure** (v0.4):

- Multi-vintage ACS fetcher for longitudinal demographic data
- Station ADA upgrade timeline construction
- Geographic panel dataset builder (tract x year) with treatment/control
  splitting
- Distance-based spatial weights matrix with PySAL bridge

**Helpers** (v0.4):

- Multi-borough snapshot iteration with independent caching
- Generic CSV export from frozen dataclasses with auto fieldnames
- Metadata and markdown report writing utilities

**10 public modules, 123 public symbols** across `models`, `io`, `analysis`,
`factors`, `helpers`, `export`, `pipeline`, `temporal`, and `cli`.

## Quickstart

```bash
pip install subway-access
```

For the full plotting + geographic + network stack:

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

## Factor pipeline

The composable factor pipeline lets you build custom classification models that
run in a single pass over every tract. Each `Factor` receives row-level context
(tract demographics, station data, catchments, and an extensible extras slot for
external data) and returns a typed value.

```python
from subway_access.factors import (
    CoverageFactor,
    FactorContext,
    GapScoreFactor,
    NearestStationDistanceFactor,
    NeedScoreFactor,
    Pipeline,
    ReliabilityWeightedCoverageFactor,
    StationCountFactor,
)

# Compose a pipeline from built-in factors.
pipe = (
    Pipeline()
    .add(NeedScoreFactor())
    .add(CoverageFactor())
    .add(GapScoreFactor())
    .add(NearestStationDistanceFactor())
    .add(StationCountFactor())
)

# Build contexts from a loaded snapshot.
contexts = [
    FactorContext(tract=t, stations=snapshot.stations, catchments=catchments)
    for t in snapshot.demographics.tracts
]

# Run all factors across all tracts.
result = pipe.run(contexts)
result.to_records()  # tuple of dicts
result.to_dataframe()  # pandas DataFrame (optional dep)
```

Custom factors are simple subclasses:

```python
from subway_access.factors import Factor, FactorContext


class HousingCostFactor(Factor):
    name = "median_rent"
    dtype = "float"

    def __init__(self, rents: dict[str, float]) -> None:
        self._rents = rents

    def compute(self, context: FactorContext) -> float:
        return self._rents.get(context.tract.tract_id, 0.0)
```

Add reliability weighting to distinguish nominal from effective coverage:

```python
# Build reliability scores from outage data.
reliability = analysis.compute_reliability(
    snapshot.stations, snapshot.outages, models.TimeWindow(days=365)
)
rel_scores = {r.station_id: r.reliability_score for r in reliability.records}

# Add reliability-weighted coverage to the pipeline.
pipe = pipe.add(ReliabilityWeightedCoverageFactor(rel_scores))
```

For a full worked example using the factor pipeline across all five boroughs
with geographic choropleths, diagnostic checks, and auto-generated reporting,
see
[`examples/accessibility-change-over-time/`](examples/accessibility-change-over-time/).

## Temporal panel

Build geographic panel datasets for difference-in-differences or spatial
autoregressive panel estimation:

```python
from subway_access.temporal import build_panel_dataset, build_upgrade_timeline

# Build an upgrade timeline from station data + known upgrade years.
timeline = build_upgrade_timeline(
    snapshot.stations,
    known_upgrades={"station_1": 2019, "station_2": 2021},
)

# Construct the panel (tract x year).
panel = build_panel_dataset(vintage_estimates, station_locations, timeline)
panel.treatment_group()  # tracts that gained accessibility
panel.control_group()  # tracts that did not
panel.to_dataframe()  # pandas DataFrame with (unit_id, period) index
```

The [accessibility-change-over-time](examples/accessibility-change-over-time/)
example builds a full 5-borough panel (2,317 tracts x 7 years = 16,219
observations) and produces a research report with treatment-vs-control balance
checks, spatial weights, and model specification.

## Examples

`examples/` follows a self-contained project pattern. Each folder has its own
`pyproject.toml`, `README.md`, `main.py`, and tracked `reports/` output.

- [`fetch-borough-snapshot/`](examples/fetch-borough-snapshot/) -- minimal data
  fetch
- [`borough-gap-analysis/`](examples/borough-gap-analysis/) -- gap scoring and
  visualization
- [`outage-reliability-report/`](examples/outage-reliability-report/) -- station
  reliability analysis
- [`multi-borough-access-profile/`](examples/multi-borough-access-profile/) --
  cross-borough comparison
- [`network-access-comparison/`](examples/network-access-comparison/) --
  Euclidean vs OSM walking network
- [**`accessibility-change-over-time/`**](examples/accessibility-change-over-time/)
  -- full research pipeline with factor analysis, geographic maps, temporal
  panel, diagnostic checks, and auto-generated report
  ([sample report](examples/accessibility-change-over-time/reports/accessibility-change-report.md))
- [`factor-factory-rdd-walkthrough/`](examples/factor-factory-rdd-walkthrough/)
  -- minimal recipe: regression discontinuity at the 800 m ADA walk-radius
  threshold using `factor-factory` engines + `jellycell` tearsheets
- [`example-template/`](examples/example-template/) -- bootstrap template for
  new examples

## Extending with factor-factory (optional)

`subway-access` integrates with [`factor-factory`](https://github.com/random-walks/factor-factory)
--- a causal-inference engine registry --- and
[`jellycell`](https://github.com/random-walks/jellycell) for tearsheet
rendering, via the optional `[factor-factory]` and `[tearsheets]` extras:

```bash
pip install "subway-access[factor-factory,tearsheets]"
```

This unlocks the `subway_access.reporting` module (lazy-imports; a plain
`pip install subway-access` leaves the library fully usable without these
deps) and an "Engine audit" appendix on the accessibility case study that
cross-checks the headline findings with five factor-factory engine fits:
two-way fixed-effects DiD (`did.twfe`), Sun-Abraham IW (`did.sa`), augmented
synthetic control (`scm.augmented`), regression discontinuity at the 800 m
walk radius (`rdd.rd_robust`), and Moran's *I* via the registry
(`spatial.morans_i`). Each fit emits a JSON artifact consumed by the
shipped jellycell `findings.md.j2` tearsheet template.

For the wiring pattern, see
[`docs/factor-factory-integration.md`](docs/factor-factory-integration.md)
and the minimal recipe in
[`examples/factor-factory-rdd-walkthrough/`](examples/factor-factory-rdd-walkthrough/).

## Methodology

The workflow is intentionally explicit and reproducible:

1. Select a study area through `nyc-geo-toolkit` (borough, community district,
   council district)
2. Fetch official MTA and Census sources into a local cache
3. Load cached files into typed, frozen in-memory datasets
4. Generate Euclidean walk catchments (800 m / 10-min default) or OSM network
   isochrones
5. Score tract centroids against accessible-station catchments via the factor
   pipeline
6. Compute tract need, rolling reliability, and station metrics
7. Optionally build a temporal panel for causal analysis
8. Export publishable GeoJSON, CSV, and markdown outputs

Euclidean access remains the documented baseline. The network comparison layer
shows how real walking routes change the coverage picture. The factor pipeline
and temporal panel support research-grade analysis on top of the same data
foundation.

## Documentation

- Hosted docs:
  [subway-access.readthedocs.io](https://subway-access.readthedocs.io/)
- Local preview: `make docs`
- Strict docs build: `make docs-build`

Quick links: [Home](https://subway-access.readthedocs.io/en/latest/),
[Getting Started](https://subway-access.readthedocs.io/en/latest/getting-started/),
[CLI Reference](https://subway-access.readthedocs.io/en/latest/cli/),
[Architecture](https://subway-access.readthedocs.io/en/latest/architecture/),
[Python API](https://subway-access.readthedocs.io/en/latest/api/),
[Contributing](https://subway-access.readthedocs.io/en/latest/contributing/),
[Releasing](https://subway-access.readthedocs.io/en/latest/releasing/),
[Changelog](https://subway-access.readthedocs.io/en/latest/changelog/)

## Development

```bash
make install      # full contributor environment with all extras
make test         # pytest suite
make lint         # ruff + mypy + public API audit
make check        # lint + tests (pre-push gate)
make docs-build   # strict mkdocs build
make ci           # full local CI equivalent
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

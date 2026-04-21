# Getting Started

This guide shows the fastest path to the current `subway-access` workflow.

## Install

```bash
pip install subway-access
```

For the full plotting + network layer:

```bash
pip install "subway-access[all]"
```

For local development:

```bash
make install-dev
```

## Fetch a real snapshot

```bash
subway-access fetch-snapshot --geography borough --value Manhattan --cache-dir cache/manhattan
```

This writes a reusable local cache bundle.

## Analyze the cached snapshot

```bash
subway-access analyze-snapshot --cache-dir cache/manhattan --output-dir artifacts/manhattan
```

## Use the Python API

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

## Add The Network Layer

The advanced path builds on the same cached snapshot:

1. fetch or reuse the official MTA + ACS cache
2. build or reuse a cached OSM walking graph for the same study area
3. compare Euclidean coverage to network-based accessibility

## Current methodology

The current flow is intentionally explicit and reproducible:

1. select a real study area through `nyc-geo-toolkit`
2. fetch official MTA and Census records into a local cache
3. load those cached records back into typed in-memory datasets
4. generate Euclidean walk catchments from a fixed walking speed
5. optionally compare that baseline against cached OSM walking graphs
6. compute need, reliability, and gap metrics

This is a documented first pass, not a claim of full routing realism.

## Research workflow (temporal panel + causal estimators)

On top of the baseline snapshot/score flow, `subway-access` ships a
research-oriented surface for _changes over time_ — how accessibility, gap, and
coverage evolve as stations gain elevators year-over-year. The core primitives
live in [`subway_access.temporal`](api.md#temporal):

```python
from subway_access.temporal import (
    build_panel_dataset,
    build_upgrade_timeline,
    build_distance_weights,
)

# Build a (tract × year) panel from cached snapshots + known upgrade years.
timeline = build_upgrade_timeline(
    snapshot.stations,
    known_upgrades={"S1": 2019, "S2": 2021, ...},  # station_id -> upgrade year
)
panel = build_panel_dataset(
    vintage_estimates,  # dict[int, dict[tract_id, dict[field, value]]]
    station_locations,  # dict[station_id, (lat, lon)]
    timeline,
    catchment_radius_meters=800.0,  # 0.5-mile walk radius
)
treatment_obs = panel.treatment_group()
control_obs = panel.control_group()
```

From there you can either:

- run a **hand-rolled DiD / OLS / Moran's _I_** pipeline (no optional extras —
  `numpy` suffices), or
- plug the panel into [**factor-factory**](factor-factory-integration.md) for
  peer-reviewed causal estimators (TWFE, Sun-Abraham, synthetic-control, RDD,
  spatial autocorrelation) behind a single `Panel` + `Engine` contract, and
  render
  [**jellycell**](factor-factory-integration.md#7-lightweight-tearsheets-via-jellycell-v14)
  tearsheets from the results.

The full worked example is
[`examples/accessibility-change-over-time/`](https://github.com/random-walks/subway-access/tree/main/examples/accessibility-change-over-time)
— a real research artifact with a 48 KB APA-formatted case study, 15 figures, 6
tables, and an engine-audit appendix. Minimal RDD recipe:
[`examples/factor-factory-rdd-walkthrough/`](https://github.com/random-walks/subway-access/tree/main/examples/factor-factory-rdd-walkthrough).

For the integration details see
[factor-factory integration](factor-factory-integration.md).

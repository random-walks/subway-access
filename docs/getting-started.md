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

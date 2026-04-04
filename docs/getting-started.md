# Getting Started

This guide shows the fastest path to the current `subway-access` workflow.

## Install

```bash
pip install subway-access
```

For local development:

```bash
make install-dev
```

## Run the packaged demo

```bash
subway-access demo --output-dir demo-output --minutes 10
```

This writes:

- `demo-output/catchments.geojson`
- `demo-output/accessibility-gaps.csv`
- `demo-output/station-metrics.csv`

## Use the Python API

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

The implemented `0.1` flow is intentionally simple and reproducible:

1. load stations and ADA status
2. generate circular walk catchments from a fixed walking speed
3. test tract centroids against those catchments
4. compute a need score from disability, senior, and poverty rates
5. compute rolling reliability from outage history
6. label uncovered high-need tracts as accessibility gaps

This is a documented first pass, not a claim of full routing realism.

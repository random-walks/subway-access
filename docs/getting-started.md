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

## Use the Python API

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

The implemented `0.1` flow is intentionally simple and reproducible:

1. load stations and ADA status
2. generate circular walk catchments from a fixed walking speed
3. test tract centroids against those catchments
4. compute a need score from disability, senior, and poverty rates
5. label uncovered high-need tracts as accessibility gaps

This is a documented first pass, not a claim of full routing realism.

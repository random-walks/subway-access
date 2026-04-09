# Usage

## Real-data workflow

`subway-access` ships a two-step CLI workflow built on live MTA and Census data:

### 1. Fetch a study-area snapshot

```bash
subway-access fetch-snapshot --geography borough --value Manhattan --cache-dir cache/manhattan
```

This fetches official MTA stations, ADA status, elevator availability history,
equipment assets, street entrances, and ACS tract demographics into a reusable
local cache.

### 2. Analyze the cached snapshot

```bash
subway-access analyze-snapshot --cache-dir cache/manhattan --output-dir artifacts/manhattan
```

The command writes:

- `catchments.geojson`
- `accessibility-gaps.csv`
- `station-metrics.csv`

You can change the walk threshold and reliability window:

```bash
subway-access analyze-snapshot --cache-dir cache/manhattan --output-dir artifacts/manhattan --minutes 10 --reliability-window-days 365
```

## Python API

```python
from pathlib import Path
from subway_access import analysis, models, pipeline

snapshot = pipeline.fetch_study_area_snapshot(
    models.AccessibilityQuery(geography="borough", value="Manhattan"),
    cache_dir=Path("cache/manhattan"),
)
catchments = analysis.generate_catchments(
    snapshot.stations, models.CatchmentRequest(minutes=10),
)
scores = analysis.score_accessibility(
    snapshot.stations, catchments, snapshot.demographics,
)
reliability = analysis.compute_reliability(
    snapshot.stations, snapshot.outages, models.TimeWindow(days=30),
)
gaps = analysis.analyze_gaps(scores)
```

## Current methodology

- Euclidean walking-radius catchments as the documented baseline
- OSM-network walk isochrones available for comparison
- tract access based on tract centroids
- need score computed via composable factor pipeline (disability, senior,
  poverty rates)
- gap score is the need score for uncovered tracts, `0` for covered tracts
- rolling station reliability scored from public elevator availability history
- station metrics combine coverage, need, and reliability into a single export

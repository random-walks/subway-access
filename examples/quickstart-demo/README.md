# Quickstart Demo

This is the smallest end-to-end `subway-access` example.

It uses only packaged sample data and writes:

- `artifacts/catchments.geojson`
- `artifacts/accessibility-gaps.csv`
- `artifacts/station-metrics.csv`
- `reports/quickstart-demo-tearsheet.md`

## Run

```bash
uv sync
uv run python main.py
```

## What it shows

- subpackage-first imports with `subway_access.analysis`, `subway_access.export`,
  `subway_access.models`, and `subway_access.samples`
- a full sample-backed workflow from station loading through reliability scoring
- report generation without notebooks

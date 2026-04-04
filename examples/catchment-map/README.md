# Catchment Map

This example is aimed at map producers who want ready-to-drop GeoJSON.

It writes both polygon catchments and point-based station metrics so a consumer
can style service areas and station summaries separately.

## Run

```bash
uv sync
uv run python main.py
```

## Outputs

- `artifacts/catchments.geojson`
- `artifacts/station-metrics.geojson`
- `reports/catchment-map-tearsheet.md`

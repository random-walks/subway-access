# Network Access Comparison

This example compares the Euclidean first-pass model against a real OSM walking
network for a smaller NYC study area.

## Run

```bash
uv sync
uv run python main.py
```

Tracked `reports/` refresh on every run by default. To skip:

```bash
uv run python main.py --no-publish-report
```

## Outputs

- `artifacts/euclidean-catchments.geojson`
- `artifacts/network-catchments.geojson`
- `artifacts/network-access-comparison.csv`
- `reports/network-access-comparison-tearsheet.md`
- `reports/figures/coverage-change-counts.png`
- `reports/figures/travel-time-scatter.png`
- `reports/figures/top-network-penalties.png`

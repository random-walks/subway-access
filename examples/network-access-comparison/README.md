# Network Access Comparison

This example compares the Euclidean first-pass model against a real OSM walking
network for a smaller NYC study area.

## Run

```bash
uv sync
uv run python main.py
```

To update the tracked report:

```bash
uv run python main.py --publish-report
```

## Outputs

- `artifacts/euclidean-catchments.geojson`
- `artifacts/network-catchments.geojson`
- `artifacts/network-access-comparison.csv`
- `reports/network-access-comparison-tearsheet.md` when `--publish-report` is used
- `reports/figures/coverage-change-counts.png`
- `reports/figures/travel-time-scatter.png`
- `reports/figures/top-network-penalties.png`

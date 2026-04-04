# Borough Gap Analysis

This example turns a real borough snapshot into a gap-analysis tearsheet.

It reuses the official-data cache pattern and then exports real borough-scale
gap outputs for a selected study area.

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

- `artifacts/catchments.geojson`
- `artifacts/borough-accessibility-gaps.csv`
- `reports/borough-gap-analysis-tearsheet.md` when `--publish-report` is used
- `reports/figures/top-gap-tracts.png`
- `reports/figures/need-vs-travel.png`
- `reports/figures/travel-minutes-histogram.png`

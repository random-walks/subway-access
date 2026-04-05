# Multi-Borough Access Profile

This advanced EDA example compares borough-wide accessibility and reliability
patterns across Manhattan, Brooklyn, and Queens using official cached subway
snapshots.

## Run

```bash
uv sync
uv run python main.py
```

To refresh the cached borough snapshots:

```bash
uv run python main.py --refresh
```

Tracked `reports/` (including figures) refresh on every run by default. To skip:

```bash
uv run python main.py --no-publish-report
```

## Outputs

- `artifacts/borough-profile.csv`
- `reports/multi-borough-access-profile-tearsheet.md`
- `reports/figures/coverage-rate-by-borough.png`
- `reports/figures/uncovered-population-by-borough.png`
- `reports/figures/accessible-station-share-by-borough.png`
- `reports/figures/mean-reliability-by-borough.png`

# Fetch Borough Snapshot

This example shows the recommended real-data consumer pattern for
`subway-access`:

1. select a real study area through `nyc-geo-toolkit`
2. fetch official MTA and Census data
3. save a local snapshot under `cache/`
4. reuse that cache on later runs unless `--refresh` is passed
5. write artifact metadata every run so the snapshot is easy to audit later

## Run

```bash
uv sync
uv run python main.py
```

To force a fresh snapshot:

```bash
uv run python main.py --refresh
```

To update the tracked report:

```bash
uv run python main.py --publish-report
```

## Outputs

- `cache/<study-area>/...` local official-data snapshot files
- `artifacts/fetch-metadata.json`
- `artifacts/fetch-summary.md`
- `reports/fetch-borough-snapshot-tearsheet.md`
- `reports/figures/accessibility-status.png`
- `reports/figures/top-routes.png`
- `reports/figures/station-structures.png`

# Outage Reliability Report

This example uses the public elevator and escalator availability history to
build a rolling station reliability report for a selected study area.

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

- `artifacts/station-reliability.csv`
- `reports/outage-reliability-report-tearsheet.md`
- `reports/figures/lowest-reliability-stations.png`
- `reports/figures/scheduled-vs-unscheduled.png`
- `reports/figures/availability-distribution.png`

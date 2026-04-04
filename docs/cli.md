# CLI Reference

The installed `subway-access` command now exposes a two-step real-data
workflow.

## `subway-access fetch-snapshot`

Fetch and cache a real public-data study-area snapshot:

```bash
subway-access fetch-snapshot --geography borough --value Manhattan --cache-dir cache/manhattan
```

Arguments:

- `--geography`: boundary layer such as `borough`, `community_district`, or `council_district`
- `--value`: boundary value normalized through `nyc-geo-toolkit`
- `--cache-dir`: directory where the snapshot cache files will be written
- `--availability-months`: number of months of public availability history to fetch
- `--refresh`: force a fresh snapshot
- `--skip-gtfs-archive`: do not cache the raw GTFS subway archive alongside the normalized snapshot

## `subway-access analyze-snapshot`

Analyze a previously fetched snapshot:

```bash
subway-access analyze-snapshot --cache-dir cache/manhattan --output-dir artifacts/manhattan
```

Arguments:

- `--cache-dir`: directory containing a fetched snapshot bundle
- `--output-dir`: directory where the analysis outputs will be written
- `--minutes`: positive integer walking threshold for the first-pass catchment
- `--reliability-window-days`: rolling outage window used for reliability scoring

Outputs:

- `catchments.geojson`
- `accessibility-gaps.csv`
- `station-metrics.csv`

## Exit behavior

- invalid arguments return a CLI error with exit code `2`
- successful runs return `0`
- invalid values for catchment or reliability windows return a CLI error with exit code `2`

# CLI Reference

The installed `subway-access` command currently exposes one implemented workflow.

## `subway-access demo`

Run the packaged fixture-backed analysis flow:

```bash
subway-access demo --output-dir demo-output --minutes 10
```

Arguments:

- `--output-dir`: directory where the GeoJSON and CSV outputs will be written
- `--minutes`: positive integer walking threshold for the first-pass catchment

Outputs:

- `catchments.geojson`
- `accessibility-gaps.csv`

## Exit behavior

- invalid arguments return a CLI error with exit code `2`
- successful runs return `0`
- unimplemented future workflows are intentionally not exposed through the CLI yet

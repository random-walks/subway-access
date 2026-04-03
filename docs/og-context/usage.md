# Usage

## Implemented v0.1 demo workflow

`subway-access` now ships one real, deterministic workflow built around packaged
fixture data:

1. load a small GTFS-like station table
2. load station-level ADA status
3. generate Euclidean first-pass catchments
4. join tract centroids with demographic rates
5. compute a tract-level accessibility gap output
6. export catchments as GeoJSON and gaps as CSV

Run it with:

```bash
python -m subway_access demo --output-dir demo-output
```

You can also change the first-pass walk threshold:

```bash
python -m subway_access demo --output-dir demo-output --minutes 10
```

The command writes:

- `catchments.geojson`
- `accessibility-gaps.csv`

## Current methodology

The implemented v0.1 slice intentionally uses the simplest honest method from
the roadmap:

- station coverage is based on a Euclidean walking-radius approximation
- tract access is based on tract centroids
- need score is the mean of disability, senior, and poverty rates
- gap score is the need score for uncovered tracts and `0` for covered tracts

This is a documented first pass, not a claim of full routing realism.

## Still planned later

The following surfaces remain explicit placeholders and raise
`NotImplementedError`:

- outage loading
- pedestrian network loading
- reliability computation
- station metrics export

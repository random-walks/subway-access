# About the data

This example pulls **all public layers** exposed by `subway-access` across **every NYC borough**:
MTA station catalog, normalized station and accessibility CSVs, **subway entrance/exit points** (Open NY),
optional **GTFS-Pathways** rows when the static zip includes them, equipment assets, elevator/escalator
availability history, outage-style rollups from that history, ACS tract demographics, one **GTFS static**
subway zip (downloaded for the first borough only), and—by default—an **OSM walking graph** per borough
cached beside each snapshot.

Expect **large downloads**, **long runtimes** (especially OSM), and **gigabytes** under `cache/` when you
run the full five-borough workflow.

## Run

```bash
uv sync
uv run python main.py
```

Faster iteration (one borough, no OSM graph):

```bash
uv run python main.py --boroughs Manhattan --skip-walk-graphs
```

Skip updating tracked `reports/`:

```bash
uv run python main.py --no-publish-report
```

Skip tract choropleth maps (still builds bar/histogram figures):

```bash
uv run python main.py --skip-choropleth
```

## Choropleth maps

The report adds **census tract choropleths** of ACS disability rate on **real tract boundaries**
from [`nyc-geo-toolkit`](https://pypi.org/project/nyc-geo-toolkit/) (`load_nyc_census_tracts`), merged
with the same tract-level values already in each borough snapshot. You get:

- one **citywide** map (`choropleth-disability-nyc.png`)
- one map **per borough** in the run (`choropleth-disability-<slug>.png`)

Census **tracts** are demographic areas used with ACS data — they are not subway tracks, line paths, or
ridership entry counts.

Plots use **GeoPandas** + **Matplotlib** (installed with the toolkit stack).

## Station + equipment maps

The report also writes **point maps** on each borough outline (`study-area.geojson`). By default,
each map has a **faint ACS disability choropleth** underlay (same tract polygons and `vmax` as the
standalone choropleth figures), then the study-area outline, then points.

- **GTFS** `stops.txt` **parent** stations (`location_type=1`) as dots colored by ADA status from the
  snapshot (joined on `gtfs_stop_id`). The MTA feed often gives one coordinate per complex; platform
  child stops duplicate that point, so this is not a street-entrance map.
- **Elevator / escalator** locations from the MTA equipment API (`georeference` GeoJSON points).

Filenames: `map-stations-equipment-nyc.png` and `map-stations-equipment-<slug>.png`. Public
**turnstile / ridership** data is not part of the snapshot bundle.

When **`entrances.geojson`** is present, the example also writes:

- **`map-combined-stations-entrances-nyc.png`** (and **`map-combined-stations-entrances-<slug>.png`** per borough): MTA catalog centroids as **stars (★)** and Open NY entrances as **dots (●)**, same ADA colors for both, plus equipment.
- **`map-zoom-grand-army-plaza-detail.png`** (only when **Brooklyn** is in the run): ~520 m zoom near the 2/3 **Grand Army Plaza** complex — **OpenStreetMap** basemap (via `contextily`), tract disability (ACS) overlay, **lines** from each entrance to its catalog stop when `gtfs_stop_id` matches, larger scatter markers for entrances/stations/equipment (EPSG:3857).
- **`map-library-header-horizontal.png`** (Brooklyn + entrances): a **wide horizontal** banner (~3.2 km × 720 m) over **Atlantic / Downtown Brooklyn / Fort Greene** — dense lines, visible tract-level disability variation, OSM underneath, **large title**, **colorbar**, and **two legends** (symbols + ADA). The canonical copy committed for **docs + PyPI** lives at repo root **`docs/images/subway-access-hero.png`** (refresh by copying this file over after a run).

## Open NY entrance charts

When `entrances.geojson` is present, the report also adds Matplotlib figures that are **about the
entrance layer** (not just mixed into the big “stations + tracts + entrances” bar):

- `entrances-per-gtfs-stop-distribution.png` — histogram of entrance counts per GTFS parent stop
- `entrances-ada-status-counts.png` — ADA status at each entrance (via `gtfs_stop_id` join to the catalog)
- `entrances-per-station-ratio-by-borough.png` — Open NY entrance count ÷ MTA catalog station count per borough
- `entrances-open-ny-type-top.png` — top raw `entrance_type` labels from Open NY

Use `--skip-entrance-figures` to omit these (faster iteration).

## Flags

| Flag | Purpose |
| --- | --- |
| `--boroughs` | Comma-separated list (default: all five). The **first** listed borough receives the GTFS archive. |
| `--skip-walk-graphs` | Do not download OSM `walk.graphml` per borough. |
| `--skip-choropleth` | Skip GeoPandas tract choropleth figures (faster). |
| `--skip-station-maps` | Skip GTFS station + equipment point maps (requires `gtfs_subway.zip`). |
| `--skip-entrance-figures` | Skip Open NY entrance summary charts (per-stop, ADA, types, ratio). |
| `--graph-buffer-meters` | Buffer around the borough polygon for OSM (default `250`). |
| `--availability-months` | Lookback for MTA availability API (default `12`). |
| `--refresh` | Re-fetch even when cache files exist. |
| `--cache-dir` | Root for `cache/<borough-slug>/` (default `./cache`). |

## Outputs

- **Ignored** `cache/<borough-slug>/`: snapshot CSV/JSON/GeoJSON, `entrances.geojson`, optional
  `gtfs-pathways.json`, optional `gtfs_subway.zip`, OSM graph files.
- **Ignored** `artifacts/tract-sample-seed.csv`: tiny reproducible tract sample from the EDA step.
- **Tracked** `reports/about-the-data-tearsheet.md` and `reports/figures/*.png`: data catalogue, bar/histogram
  charts, optional tract choropleths, and optional GTFS station + equipment point maps.

Background on sources is summarized in the tearsheet and aligns with the package’s
[`docs/og-context/data-sources.md`](../../docs/og-context/data-sources.md) narrative.

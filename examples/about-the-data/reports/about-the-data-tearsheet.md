# About the data

This example downloads the maximum **public** `subway-access` snapshot bundle for each NYC borough: MTA station catalog (filtered in memory), GTFS-derived station rows, **subway entrance/exit points** (Open NY), optional **GTFS-Pathways** rows when present in the static zip, accessibility rows, equipment assets, elevator/escalator availability history, outage-style rollups, ACS tract demographics, and optionally a cached **OpenStreetMap** walking graph per borough.

**Census tracts** (used for choropleths and need scores elsewhere in the package) are U.S. Census statistical areas for demographics — they are **not** subway tracks, line geometry, or turnstile entry counts.

Caches live under `cache/<borough-slug>/` (gitignored). The GTFS subway zip is fetched **once** (first borough only) to avoid duplicate large downloads.

## Boroughs in this run

- Manhattan
- Brooklyn
- Queens
- Bronx
- Staten Island

## Catalogue

| Borough | Stations | Entrances | Tracts | GTFS pw | GTFS loc | Outage rows | Availability rows | OSM nodes | OSM edges | Cache size |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Manhattan | 151 | 869 | 309 | 0 | 0 | 3845 | 3845 | 37090 | 118058 | 58.3 MiB |
| Brooklyn | 169 | 580 | 800 | 0 | 0 | 1255 | 1255 | 71674 | 230396 | 93.2 MiB |
| Queens | 82 | 354 | 723 | 0 | 0 | 1047 | 1047 | 127034 | 411328 | 162.8 MiB |
| Bronx | 70 | 251 | 360 | 0 | 0 | 618 | 618 | 40598 | 123974 | 52.6 MiB |
| Staten Island | 21 | 66 | 125 | 0 | 0 | 0 | 0 | 59612 | 169770 | 70.8 MiB |

## Aggregated source layers (metadata)

| Source key | Origin | Rows (summed across boroughs) |
| --- | --- | ---: |
| `acs_tract_demographics` | https://api.census.gov/data/2023/acs/acs5 and https://api.census.gov/data/2023/acs/acs5/subject | 2317 |
| `mta_availability_history` | https://data.ny.gov/resource/rc78-7x78.json | 6765 |
| `mta_equipment_assets` | https://data.ny.gov/resource/94fv-bak7.json | 736 |
| `mta_station_catalog` | https://data.ny.gov/resource/39hk-dx4f.json | 496 |
| `mta_subway_entrances` | https://data.ny.gov/resource/i9wp-a4ja.json | 2120 |

## Figures

### Snapshot scale by borough

![Record counts](./figures/record-counts-by-borough.png)

### Sampled disability rate distribution

![Disability rate sample](./figures/sampled-disability-rate.png)

### Open NY entrances — distribution and joins

**Per GTFS parent stop:** histogram of how many street-level entrance/exit points share the same `gtfs_stop_id` (after study-area filter).

![Entrances per GTFS stop](./figures/entrances-per-gtfs-stop-distribution.png)

**ADA at each entrance:** station-level ADA from the MTA catalog, applied to every Open NY point via `gtfs_stop_id`.

![ADA status at entrances](./figures/entrances-ada-status-counts.png)

**Density:** mean Open NY entrance count divided by MTA catalog station count (per borough).

![Entrances per station ratio](./figures/entrances-per-station-ratio-by-borough.png)

**Raw `entrance_type` labels** from the dataset (top categories).

![Entrance types](./figures/entrances-open-ny-type-top.png)

### NYC disability rate (tract choropleth)

Tract polygons come from [`nyc-geo-toolkit`](https://pypi.org/project/nyc-geo-toolkit/) (`load_nyc_census_tracts`). Values are ACS disability rates merged from each borough snapshot's demographics layer.

![NYC choropleth](./figures/choropleth-disability-nyc.png)

### Manhattan (tract choropleth)

![Manhattan choropleth](./figures/choropleth-disability-manhattan.png)

### Brooklyn (tract choropleth)

![Brooklyn choropleth](./figures/choropleth-disability-brooklyn.png)

### Queens (tract choropleth)

![Queens choropleth](./figures/choropleth-disability-queens.png)

### Bronx (tract choropleth)

![Bronx choropleth](./figures/choropleth-disability-bronx.png)

### Staten Island (tract choropleth)

![Staten Island choropleth](./figures/choropleth-disability-staten-island.png)

### Entrances (Open NY) or GTFS parents, plus vertical equipment (MTA assets)

Each map includes a **faint ACS disability choropleth** underlay (same tract geometries and color scale as the standalone choropleth figures), then the study-area outline, then points. When the snapshot includes **`entrances.geojson`**, maps use **street-level** entrance/exit coordinates from Open NY (`i9wp-a4ja`), colored by ADA status via `gtfs_stop_id` join. If that layer is empty, the example falls back to GTFS **parent** stops (`stops.txt`, `location_type=1`). **Elevator and escalator** points use georeferences from the MTA equipment API. **Ridership / turnstile entries** are not in this bundle.

![NYC stations + equipment](./figures/map-stations-equipment-nyc.png)

### Manhattan (stations + equipment)

![Manhattan map](./figures/map-stations-equipment-manhattan.png)

### Brooklyn (stations + equipment)

![Brooklyn map](./figures/map-stations-equipment-brooklyn.png)

### Queens (stations + equipment)

![Queens map](./figures/map-stations-equipment-queens.png)

### Bronx (stations + equipment)

![Bronx map](./figures/map-stations-equipment-bronx.png)

### Staten Island (stations + equipment)

![Staten Island map](./figures/map-stations-equipment-staten-island.png)

### MTA catalog + Open NY entrances (combined)

**Stars (★)** are MTA catalog station centroids; **circles (●)** are street-level Open NY entrance/exit points — both colored by the same station ADA label (via `gtfs_stop_id`). Equipment overlays unchanged.

![NYC combined](./figures/map-combined-stations-entrances-nyc.png)

### Manhattan (catalog ★ + entrances ● + equipment)

![Manhattan combined](./figures/map-combined-stations-entrances-manhattan.png)

### Brooklyn (catalog ★ + entrances ● + equipment)

![Brooklyn combined](./figures/map-combined-stations-entrances-brooklyn.png)

### Queens (catalog ★ + entrances ● + equipment)

![Queens combined](./figures/map-combined-stations-entrances-queens.png)

### Bronx (catalog ★ + entrances ● + equipment)

![Bronx combined](./figures/map-combined-stations-entrances-bronx.png)

### Staten Island (catalog ★ + entrances ● + equipment)

![Staten Island combined](./figures/map-combined-stations-entrances-staten-island.png)

### Grand Army Plaza (Brooklyn) — zoom

Roughly **520 m** around the 2/3 complex, drawn in **Web Mercator (EPSG:3857)** so street geometry matches OpenStreetMap. **OSM Mapnik** basemap (roads/sidewalks as raster), **tract polygons** colored by ACS disability rate (same merge as choropleths), **lines** from each Open NY entrance to its MTA catalog stop when `gtfs_stop_id` matches, plus elevator/escalator assets.

![Grand Army Plaza zoom](./figures/map-zoom-grand-army-plaza-detail.png)

### Horizontal banner (README / PyPI header image)

Wide **~3.2 km × 720 m** view centered on **Atlantic / Downtown Brooklyn / Fort Greene** (many subway lines; tracts show ACS disability variation). Same layers as the zoom maps: OSM roads, tract **viridis** choropleth with **colorbar**, entrance→station links, large title and legends — intended for copying into project README or PyPI.

![Library header horizontal](./figures/map-library-header-horizontal.png)

## Artifacts

After a run, see `artifacts/tract-sample-seed.csv` for a small reproducible tract sample (same random seed as the histogram).

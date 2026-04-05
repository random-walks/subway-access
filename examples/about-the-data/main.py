"""NYC-wide snapshot download and data-catalogue report for subway-access."""

from __future__ import annotations

import argparse
from pathlib import Path

import analysis_logic
import download_logic

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"
ARTIFACTS_DIR = ROOT / "artifacts"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download public MTA, Census, and (by default) OSM layers for every NYC "
            "borough and write a data-catalogue tearsheet."
        ),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=CACHE_DIR,
        help="Root directory for per-borough snapshot caches (ignored by git).",
    )
    parser.add_argument(
        "--boroughs",
        type=str,
        default="",
        help=(
            "Comma-separated borough names (default: all five). "
            "Example: Manhattan,Brooklyn. The first borough listed receives the "
            "GTFS static archive download."
        ),
    )
    parser.add_argument("--availability-months", type=int, default=12)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force re-fetch even when snapshot files already exist.",
    )
    parser.add_argument(
        "--skip-walk-graphs",
        action="store_true",
        help="Skip OSM walking-graph downloads (faster, less disk).",
    )
    parser.add_argument(
        "--graph-buffer-meters",
        type=int,
        default=250,
        help="Buffer around borough boundary when downloading OSM graphs.",
    )
    parser.add_argument(
        "--no-publish-report",
        action="store_true",
        help="Skip writing tracked reports/ and figures/ (faster local iteration).",
    )
    parser.add_argument(
        "--skip-choropleth",
        action="store_true",
        help="Skip tract choropleth maps (uses nyc-geo-toolkit census tract geometries).",
    )
    parser.add_argument(
        "--skip-station-maps",
        action="store_true",
        help="Skip GTFS station + MTA equipment point maps (needs gtfs_subway.zip in cache).",
    )
    parser.add_argument(
        "--skip-entrance-figures",
        action="store_true",
        help="Skip Open NY entrance summary charts (per-stop, ADA, types, ratio).",
    )
    return parser


def _format_bytes(num: int) -> str:
    if num < 1024:
        return f"{num} B"
    if num < 1024**2:
        return f"{num / 1024:.1f} KiB"
    if num < 1024**3:
        return f"{num / 1024**2:.1f} MiB"
    return f"{num / 1024**3:.2f} GiB"


def write_report(
    *,
    boroughs: tuple[str, ...],
    summary: analysis_logic.CatalogueSummary,
    bar_chart: Path,
    hist_chart: Path,
    choropleth: analysis_logic.ChoroplethPaths | None,
    station_maps: analysis_logic.StationMapPaths | None,
    entrance_figures: analysis_logic.EntranceLayerPaths | None,
) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# About the data",
        "",
        "This example downloads the maximum **public** `subway-access` snapshot bundle "
        "for each NYC borough: MTA station catalog (filtered in memory), GTFS-derived "
        "station rows, **subway entrance/exit points** (Open NY), optional **GTFS-Pathways** "
        "rows when present in the static zip, accessibility rows, equipment assets, "
        "elevator/escalator availability history, outage-style rollups, ACS tract "
        "demographics, and optionally a cached **OpenStreetMap** walking graph per borough.",
        "",
        "**Census tracts** (used for choropleths and need scores elsewhere in the package) "
        "are U.S. Census statistical areas for demographics — they are **not** subway "
        "tracks, line geometry, or turnstile entry counts.",
        "",
        "Caches live under `cache/<borough-slug>/` (gitignored). The GTFS subway zip is "
        "fetched **once** (first borough only) to avoid duplicate large downloads.",
        "",
        "## Boroughs in this run",
        "",
        "- " + "\n- ".join(boroughs),
        "",
        "## Catalogue",
        "",
        "| Borough | Stations | Entrances | Tracts | GTFS pw | GTFS loc | Outage rows | "
        "Availability rows | OSM nodes | OSM edges | Cache size |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary.rows:
        nodes = "—" if row.walk_nodes is None else str(row.walk_nodes)
        edges = "—" if row.walk_edges is None else str(row.walk_edges)
        lines.append(
            f"| {row.borough} | {row.station_count} | {row.entrance_count} | "
            f"{row.tract_count} | {row.gtfs_pathway_rows} | {row.gtfs_location_rows} | "
            f"{row.outage_count} | {row.availability_rows} | {nodes} | {edges} | "
            f"{_format_bytes(row.cache_bytes)} |"
        )
    lines.extend(
        [
            "",
            "## Aggregated source layers (metadata)",
            "",
            "| Source key | Origin | Rows (summed across boroughs) |",
            "| --- | --- | ---: |",
        ]
    )
    for name, url, count in summary.sources:
        lines.append(f"| `{name}` | {url} | {count} |")
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "### Snapshot scale by borough",
            "",
            f"![Record counts](./figures/{bar_chart.name})",
            "",
            "### Sampled disability rate distribution",
            "",
            f"![Disability rate sample](./figures/{hist_chart.name})",
            "",
        ]
    )
    if entrance_figures is not None:
        lines.extend(
            [
                "### Open NY entrances — distribution and joins",
                "",
                "**Per GTFS parent stop:** histogram of how many street-level entrance/exit points "
                "share the same `gtfs_stop_id` (after study-area filter).",
                "",
                f"![Entrances per GTFS stop](./figures/{entrance_figures.per_stop_distribution.name})",
                "",
                "**ADA at each entrance:** station-level ADA from the MTA catalog, applied to every "
                "Open NY point via `gtfs_stop_id`.",
                "",
                f"![ADA status at entrances](./figures/{entrance_figures.ada_by_entrance.name})",
                "",
                "**Density:** mean Open NY entrance count divided by MTA catalog station count "
                "(per borough).",
                "",
                f"![Entrances per station ratio](./figures/{entrance_figures.ratio_by_borough.name})",
                "",
                "**Raw `entrance_type` labels** from the dataset (top categories).",
                "",
                f"![Entrance types](./figures/{entrance_figures.entrance_types_top.name})",
                "",
            ]
        )
    if choropleth is not None:
        lines.extend(
            [
                "### NYC disability rate (tract choropleth)",
                "",
                "Tract polygons come from [`nyc-geo-toolkit`](https://pypi.org/project/nyc-geo-toolkit/) "
                "(`load_nyc_census_tracts`). Values are ACS disability rates merged from each borough "
                "snapshot's demographics layer.",
                "",
                f"![NYC choropleth](./figures/{choropleth.nyc.name})",
                "",
            ]
        )
        for boro_name, boro_path in choropleth.by_borough:
            lines.extend(
                [
                    f"### {boro_name} (tract choropleth)",
                    "",
                    f"![{boro_name} choropleth](./figures/{boro_path.name})",
                    "",
                ]
            )
    if station_maps is not None:
        lines.extend(
            [
                "### Entrances (Open NY) or GTFS parents, plus vertical equipment (MTA assets)",
                "",
                "Each map includes a **faint ACS disability choropleth** underlay (same tract "
                "geometries and color scale as the standalone choropleth figures), then the "
                "study-area outline, then points. When the snapshot includes **`entrances.geojson`**, "
                "maps use **street-level** entrance/exit coordinates from Open NY (`i9wp-a4ja`), "
                "colored by ADA status via `gtfs_stop_id` join. If that layer is empty, the example "
                "falls back to GTFS **parent** stops (`stops.txt`, `location_type=1`). **Elevator and "
                "escalator** points use georeferences from the MTA equipment API. "
                "**Ridership / turnstile entries** are not in this bundle.",
                "",
                f"![NYC stations + equipment](./figures/{station_maps.nyc.name})",
                "",
            ]
        )
        for boro_name, boro_path in station_maps.by_borough:
            lines.extend(
                [
                    f"### {boro_name} (stations + equipment)",
                    "",
                    f"![{boro_name} map](./figures/{boro_path.name})",
                    "",
                ]
            )
        if station_maps.combined_nyc is not None:
            lines.extend(
                [
                    "### MTA catalog + Open NY entrances (combined)",
                    "",
                    "**Stars (★)** are MTA catalog station centroids; **circles (●)** are street-level "
                    "Open NY entrance/exit points — both colored by the same station ADA label "
                    "(via `gtfs_stop_id`). Equipment overlays unchanged.",
                    "",
                    f"![NYC combined](./figures/{station_maps.combined_nyc.name})",
                    "",
                ]
            )
            if station_maps.combined_by_borough:
                for boro_name, boro_path in station_maps.combined_by_borough:
                    lines.extend(
                        [
                            f"### {boro_name} (catalog ★ + entrances ● + equipment)",
                            "",
                            f"![{boro_name} combined](./figures/{boro_path.name})",
                            "",
                        ]
                    )
        if station_maps.grand_army_plaza_zoom is not None:
            lines.extend(
                [
                    "### Grand Army Plaza (Brooklyn) — zoom",
                    "",
                    "Roughly **520 m** around the 2/3 complex, drawn in **Web Mercator (EPSG:3857)** "
                    "so street geometry matches OpenStreetMap. **OSM Mapnik** basemap (roads/sidewalks "
                    "as raster), **tract polygons** colored by ACS disability rate (same merge as "
                    "choropleths), **lines** from each Open NY entrance to its MTA catalog stop when "
                    "`gtfs_stop_id` matches, plus elevator/escalator assets.",
                    "",
                    f"![Grand Army Plaza zoom](./figures/{station_maps.grand_army_plaza_zoom.name})",
                    "",
                ]
            )
        if station_maps.library_header_horizontal is not None:
            lines.extend(
                [
                    "### Horizontal banner (README / PyPI header image)",
                    "",
                    "Wide **~3.2 km x 720 m** view centered on **Atlantic / Downtown Brooklyn / Fort Greene** "
                    "(many subway lines; tracts show ACS disability variation). Same layers as the zoom "
                    "maps: OSM roads, tract **viridis** choropleth with **colorbar**, entrance→station "
                    "links, large title and legends — intended for copying into project README or PyPI.",
                    "",
                    f"![Library header horizontal](./figures/{station_maps.library_header_horizontal.name})",
                    "",
                ]
            )
    lines.extend(
        [
            "## Artifacts",
            "",
            "After a run, see `artifacts/tract-sample-seed.csv` for a small reproducible "
            "tract sample (same random seed as the histogram).",
            "",
        ]
    )
    path = REPORTS_DIR / "about-the-data-tearsheet.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    args = build_parser().parse_args()
    boroughs = download_logic.parse_borough_list(args.boroughs or None)
    cache_root = args.cache_dir.expanduser().resolve()

    print("about-the-data: downloading borough snapshots…")
    download_logic.download_borough_snapshots(
        cache_root=cache_root,
        boroughs=boroughs,
        refresh=args.refresh,
        availability_months=args.availability_months,
    )
    if not args.skip_walk_graphs:
        print("about-the-data: downloading OSM walking graphs (per borough)…")
        download_logic.download_walk_graphs(
            cache_root=cache_root,
            boroughs=boroughs,
            refresh=args.refresh,
            buffer_meters=args.graph_buffer_meters,
        )
    else:
        print("about-the-data: skipped walk graphs (--skip-walk-graphs).")

    print("about-the-data: building catalogue and figures…")
    summary = analysis_logic.build_catalogue(cache_root, boroughs)
    bar_chart, hist_chart = analysis_logic.sample_eda_figures(
        cache_root,
        boroughs,
        figures_dir=FIGURES_DIR,
        artifacts_dir=ARTIFACTS_DIR,
    )

    choropleth_paths: analysis_logic.ChoroplethPaths | None = None
    if not args.skip_choropleth:
        print("about-the-data: tract choropleth maps (nyc-geo-toolkit geometries)…")
        choropleth_paths = analysis_logic.choropleth_disability_figures(
            cache_root,
            boroughs,
            figures_dir=FIGURES_DIR,
        )
    else:
        print("about-the-data: skipped choropleth maps (--skip-choropleth).")

    entrance_paths: analysis_logic.EntranceLayerPaths | None = None
    if not args.skip_entrance_figures:
        print("about-the-data: Open NY entrance summary charts…")
        entrance_paths = analysis_logic.entrance_layer_figures(
            cache_root,
            boroughs,
            figures_dir=FIGURES_DIR,
        )
        if entrance_paths is None:
            print("about-the-data: skipped entrance charts (no cached entrances).")
    else:
        print("about-the-data: skipped entrance figures (--skip-entrance-figures).")

    station_map_paths: analysis_logic.StationMapPaths | None = None
    if not args.skip_station_maps:
        print("about-the-data: GTFS station + equipment point maps…")
        station_map_paths = analysis_logic.station_equipment_map_figures(
            cache_root,
            boroughs,
            figures_dir=FIGURES_DIR,
        )
        if station_map_paths is None:
            print(
                "about-the-data: skipped station maps (no gtfs_subway.zip under "
                f"{download_logic.borough_cache_dir(cache_root, boroughs[0])}).",
            )
    else:
        print("about-the-data: skipped station maps (--skip-station-maps).")

    report_path: Path | None = None
    if not args.no_publish_report:
        report_path = write_report(
            boroughs=boroughs,
            summary=summary,
            bar_chart=bar_chart,
            hist_chart=hist_chart,
            choropleth=choropleth_paths,
            station_maps=station_map_paths,
            entrance_figures=entrance_paths,
        )

    print("about-the-data: done.")
    print(f"  Boroughs: {', '.join(boroughs)}")
    print(f"  Bar chart: {bar_chart}")
    print(f"  Histogram: {hist_chart}")
    if choropleth_paths is not None:
        print(f"  NYC choropleth: {choropleth_paths.nyc}")
        for name, path in choropleth_paths.by_borough:
            print(f"  {name} choropleth: {path}")
    if station_map_paths is not None:
        print(f"  NYC station map: {station_map_paths.nyc}")
        for name, path in station_map_paths.by_borough:
            print(f"  {name} station map: {path}")
        if station_map_paths.combined_nyc is not None:
            print(f"  NYC combined (★+●): {station_map_paths.combined_nyc}")
            if station_map_paths.combined_by_borough:
                for name, path in station_map_paths.combined_by_borough:
                    print(f"  {name} combined: {path}")
        if station_map_paths.grand_army_plaza_zoom is not None:
            print(f"  Grand Army Plaza zoom: {station_map_paths.grand_army_plaza_zoom}")
        if station_map_paths.library_header_horizontal is not None:
            print(
                f"  Library header (horizontal): {station_map_paths.library_header_horizontal}"
            )
    if entrance_paths is not None:
        print(f"  Entrances per stop: {entrance_paths.per_stop_distribution}")
        print(f"  Entrances ADA: {entrance_paths.ada_by_entrance}")
        print(f"  Entrances / station ratio: {entrance_paths.ratio_by_borough}")
        print(f"  Entrance types: {entrance_paths.entrance_types_top}")
    if report_path is not None:
        print(f"  Tearsheet: {report_path}")
    else:
        print("  Skipped tearsheet (--no-publish-report).")


if __name__ == "__main__":
    main()

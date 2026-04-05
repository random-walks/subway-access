"""Read-only catalogue and light EDA over cached borough snapshots."""

from __future__ import annotations

import csv
import io
import json
import random
import zipfile
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

import download_logic
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import colors
from matplotlib.cm import ScalarMappable
from matplotlib.lines import Line2D
from matplotlib.ticker import StrMethodFormatter
from mpl_toolkits.axes_grid1 import make_axes_locatable
from nyc_geo_toolkit import load_nyc_census_tracts
from shapely.geometry import LineString, Point, box, shape
from shapely.ops import unary_union

from subway_access import analysis as sa_analysis
from subway_access import pipeline

try:
    import contextily as ctx
except ImportError:
    ctx = None  # type: ignore[assignment,misc]

if TYPE_CHECKING:
    from pathlib import Path

plt.switch_backend("Agg")

_ADA_COLORS: dict[str, str] = {
    "accessible": "#2ca02c",
    "partially_accessible": "#e6ab02",
    "not_accessible": "#d62728",
    "unknown": "#7f7f7f",
}


@dataclass(frozen=True, slots=True)
class BoroughCatalogueRow:
    borough: str
    cache_dir: str
    station_count: int
    tract_count: int
    entrance_count: int
    gtfs_pathway_rows: int
    gtfs_location_rows: int
    outage_count: int
    availability_rows: int
    walk_nodes: int | None
    walk_edges: int | None
    cache_bytes: int


@dataclass(frozen=True, slots=True)
class CatalogueSummary:
    rows: tuple[BoroughCatalogueRow, ...]
    sources: tuple[tuple[str, str, int], ...]


# Labels on census-tract features from ``nyc_geo_toolkit`` (``borough`` property).
_TOOLKIT_BOROUGH_BY_NAME: dict[str, str] = {
    "Manhattan": "MANHATTAN",
    "Brooklyn": "BROOKLYN",
    "Queens": "QUEENS",
    "Bronx": "BRONX",
    "Staten Island": "STATEN ISLAND",
}


@dataclass(frozen=True, slots=True)
class ChoroplethPaths:
    """Paths to disability-rate choropleth maps (tract polygons from nyc-geo-toolkit)."""

    nyc: Path
    by_borough: tuple[tuple[str, Path], ...]


@dataclass(frozen=True, slots=True)
class StationMapPaths:
    """Paths to GTFS station + MTA equipment point maps (borough study-area outlines)."""

    nyc: Path
    by_borough: tuple[tuple[str, Path], ...]
    combined_nyc: Path | None = None
    combined_by_borough: tuple[tuple[str, Path], ...] | None = None
    grand_army_plaza_zoom: Path | None = None
    library_header_horizontal: Path | None = None


# Grand Army Plaza (2/3) — zoom center in Brooklyn (lon, lat), buffer in meters.
_GRAND_ARMY_PLAZA_LON = -73.96435
_GRAND_ARMY_PLAZA_LAT = 40.67125
_GRAND_ARMY_PLAZA_BUFFER_M = 520.0

# Wide README/PyPI-style banner: Atlantic / Downtown Brooklyn / Fort Greene (many lines, tract spread).
_LIB_HEADER_LON = -73.9755
_LIB_HEADER_LAT = 40.6840
_LIB_HEADER_WIDTH_M = 3200.0
_LIB_HEADER_HEIGHT_M = 720.0


@dataclass(frozen=True, slots=True)
class EntranceLayerPaths:
    """Paths to charts that summarize Open NY entrance rows (per stop, ADA, types)."""

    per_stop_distribution: Path
    ada_by_entrance: Path
    ratio_by_borough: Path
    entrance_types_top: Path


def _dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total += child.stat().st_size
            except OSError:
                continue
    return total


def _walk_graph_stats(cache_dir: Path) -> tuple[int | None, int | None]:
    metadata_path = cache_dir / "walk-graph-metadata.json"
    if not metadata_path.exists():
        return None, None
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None
    return int(payload.get("node_count", 0)), int(payload.get("edge_count", 0))


def build_catalogue(
    cache_root: Path,
    boroughs: tuple[str, ...],
) -> CatalogueSummary:
    """Load each cached snapshot and summarize sizes and source metadata."""
    cache_root = cache_root.expanduser().resolve()
    rows: list[BoroughCatalogueRow] = []
    source_keys: dict[tuple[str, str], int] = {}

    for borough in boroughs:
        bdir = download_logic.borough_cache_dir(cache_root, borough)
        snapshot = pipeline.load_cached_snapshot(bdir)
        walk_nodes, walk_edges = _walk_graph_stats(bdir)
        pw_rows, loc_rows = sa_analysis.pathways_and_locations_counts(
            snapshot.gtfs_pathways
        )
        rows.append(
            BoroughCatalogueRow(
                borough=borough,
                cache_dir=str(bdir),
                station_count=len(snapshot.stations.stations),
                tract_count=len(snapshot.demographics.tracts),
                entrance_count=len(snapshot.entrances.entrances),
                gtfs_pathway_rows=pw_rows,
                gtfs_location_rows=loc_rows,
                outage_count=len(snapshot.outages.records),
                availability_rows=next(
                    (
                        m.record_count
                        for m in snapshot.metadata
                        if m.name == "mta_availability_history"
                    ),
                    0,
                ),
                walk_nodes=walk_nodes,
                walk_edges=walk_edges,
                cache_bytes=_dir_size(bdir),
            )
        )
        for meta in snapshot.metadata:
            key = (meta.name, str(meta.source_url))
            source_keys[key] = source_keys.get(key, 0) + meta.record_count

    sources = tuple(
        (name, url, count) for (name, url), count in sorted(source_keys.items())
    )
    return CatalogueSummary(rows=tuple(rows), sources=sources)


def _study_area_union(bdir: Path):
    payload = json.loads((bdir / "study-area.geojson").read_text(encoding="utf-8"))
    geoms = [shape(f["geometry"]) for f in payload.get("features", [])]
    if not geoms:
        message = f"No features in study-area.geojson under {bdir}."
        raise ValueError(message)
    return unary_union(geoms)


def _nyc_choropleth_base_with_vmax(
    cache_root: Path,
    boroughs: tuple[str, ...],
) -> tuple[gpd.GeoDataFrame, float]:
    """Full toolkit tract polygons + disability merge (same as choropleth figures) and shared vmax."""

    geoid_to_rate: dict[str, float] = {}
    for borough in boroughs:
        bdir = download_logic.borough_cache_dir(cache_root, borough)
        snapshot = pipeline.load_cached_snapshot(bdir)
        for tract in snapshot.demographics.tracts:
            geoid_to_rate[tract.tract_id] = tract.disability_rate

    fc = load_nyc_census_tracts()
    rows: list[dict[str, object]] = []
    for feature in fc.features:
        props = feature.properties
        geoid = str(props.get("geoid") or getattr(feature, "geography_value", ""))
        borough_code = str(props.get("borough", ""))
        geom = shape(feature.geometry)
        rows.append({"geoid": geoid, "borough": borough_code, "geometry": geom})

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    gdf["disability_rate"] = gdf["geoid"].map(geoid_to_rate)
    rate_series = gdf["disability_rate"].dropna()
    vmax = float(rate_series.max()) if len(rate_series) else 0.1
    vmax = max(0.05, min(vmax * 1.05, 0.55))
    return gdf, vmax


def _choropleth_slice_for_boundary(
    full_gdf: gpd.GeoDataFrame,
    boundary_geom,
) -> gpd.GeoDataFrame | None:
    """Tracts whose geometry intersects the study-area boundary (for map underlays)."""

    sub = full_gdf[full_gdf.intersects(boundary_geom)].copy()
    if sub.empty:
        return None
    return sub


def _plot_faint_choropleth_underlay(
    axes,
    underlay: gpd.GeoDataFrame,
    vmax: float,
) -> None:
    """Faint viridis tract layer (same scale as standalone choropleth figures)."""

    underlay.plot(
        ax=axes,
        column="disability_rate",
        cmap="viridis",
        alpha=0.28,
        vmin=0.0,
        vmax=vmax,
        missing_kwds={"color": "#e0e0e0", "alpha": 0.35},
        edgecolor="white",
        linewidth=0.08,
        zorder=0,
        legend=False,
    )


def _load_gtfs_parent_stops(zip_path: Path) -> gpd.GeoDataFrame:
    """GTFS parent stations (``location_type=1``) as point geometries."""

    with zipfile.ZipFile(zip_path) as zf:
        text = zf.read("stops.txt").decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    records: list[dict[str, object]] = []
    for row in rows:
        if row.get("location_type") != "1":
            continue
        records.append(
            {
                "gtfs_stop_id": str(row["stop_id"]).strip(),
                "stop_name": str(row.get("stop_name") or "").strip(),
                "geometry": Point(
                    float(row["stop_lon"]),
                    float(row["stop_lat"]),
                ),
            }
        )
    return gpd.GeoDataFrame(records, crs="EPSG:4326")


def _load_equipment_points(assets_path: Path) -> gpd.GeoDataFrame:
    """Elevator / escalator assets with GeoJSON ``georeference`` points."""

    raw = json.loads(assets_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    records: list[dict[str, object]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        geo = row.get("georeference")
        if not isinstance(geo, dict) or geo.get("type") != "Point":
            continue
        coords = geo.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        kind = str(row.get("elevator_or_escalator") or "").strip().lower()
        records.append(
            {
                "equipment_code": str(row.get("equipment_code") or "").strip(),
                "kind": kind,
                "geometry": Point(lon, lat),
            }
        )
    if not records:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    return gpd.GeoDataFrame(records, crs="EPSG:4326")


def _entrances_gdf(
    cache_root: Path,
    boroughs: tuple[str, ...],
) -> gpd.GeoDataFrame:
    """Open NY entrance points with ADA status joined on ``gtfs_stop_id``."""

    ada_map = _ada_by_gtfs_stop_id(cache_root, boroughs)
    records: list[dict[str, object]] = []
    for borough in boroughs:
        bdir = download_logic.borough_cache_dir(cache_root, borough)
        snapshot = pipeline.load_cached_snapshot(bdir)
        for ent in snapshot.entrances.entrances:
            gid = ent.gtfs_stop_id
            ada = ada_map.get(gid, "unknown") if gid else "unknown"
            records.append(
                {
                    "geometry": Point(ent.longitude, ent.latitude),
                    "ada_status": str(ada),
                    "entrance_type": ent.entrance_type,
                    "gtfs_stop_id": str(gid).strip() if gid else "",
                }
            )
    if not records:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    return gpd.GeoDataFrame(records, crs="EPSG:4326")


def _ada_by_gtfs_stop_id(
    cache_root: Path,
    boroughs: tuple[str, ...],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for borough in boroughs:
        bdir = download_logic.borough_cache_dir(cache_root, borough)
        snapshot = pipeline.load_cached_snapshot(bdir)
        for st in snapshot.stations.stations:
            gid = st.gtfs_stop_id
            if gid:
                mapping[gid] = str(st.ada_status)
    return mapping


def _station_catalog_gdf(
    cache_root: Path,
    boroughs: tuple[str, ...],
) -> gpd.GeoDataFrame:
    """MTA catalog station centroids (one row per station in the snapshot)."""

    records: list[dict[str, object]] = []
    for borough in boroughs:
        bdir = download_logic.borough_cache_dir(cache_root, borough)
        snapshot = pipeline.load_cached_snapshot(bdir)
        records.extend(
            {
                "geometry": Point(st.longitude, st.latitude),
                "gtfs_stop_id": str(st.gtfs_stop_id).strip() if st.gtfs_stop_id else "",
                "ada_status": str(st.ada_status),
                "name": st.name,
            }
            for st in snapshot.stations.stations
        )
    if not records:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    return gpd.GeoDataFrame(records, crs="EPSG:4326")


def _geodesic_buffer_polygon(lon: float, lat: float, buffer_meters: float):
    """Circle in WGS84 approximated via Web Mercator buffer."""

    g = gpd.GeoDataFrame({"geometry": [Point(lon, lat)]}, crs="EPSG:4326")
    g = g.to_crs("EPSG:3857")
    buffered = g.geometry.iloc[0].buffer(buffer_meters)
    return gpd.GeoSeries([buffered], crs="EPSG:3857").to_crs("EPSG:4326").iloc[0]


def _geodesic_bbox_polygon(lon: float, lat: float, width_m: float, height_m: float):
    """Axis-aligned rectangle in Web Mercator (wide = east-west span), returned in EPSG:4326."""

    g = gpd.GeoDataFrame({"geometry": [Point(lon, lat)]}, crs="EPSG:4326").to_crs(
        "EPSG:3857"
    )
    gx, gy = g.geometry.iloc[0].x, g.geometry.iloc[0].y
    half_w, half_h = width_m / 2.0, height_m / 2.0
    rect = box(gx - half_w, gy - half_h, gx + half_w, gy + half_h)
    return gpd.GeoSeries([rect], crs="EPSG:3857").to_crs("EPSG:4326").iloc[0]


def _brooklyn_tracts_in_zoom(
    cache_root: Path,
    zoom_poly,
) -> gpd.GeoDataFrame | None:
    """Census tract polygons from nyc-geo-toolkit intersecting ``zoom_poly``, ACS disability merged."""

    bdir = download_logic.borough_cache_dir(cache_root, "Brooklyn")
    snapshot = pipeline.load_cached_snapshot(bdir)
    geoid_to_rate: dict[str, float] = {}
    for tract in snapshot.demographics.tracts:
        geoid_to_rate[tract.tract_id] = tract.disability_rate

    fc = load_nyc_census_tracts()
    rows: list[dict[str, object]] = []
    for feature in fc.features:
        props = feature.properties
        geoid = str(props.get("geoid") or getattr(feature, "geography_value", ""))
        if str(props.get("borough", "")) != "BROOKLYN":
            continue
        geom = shape(feature.geometry)
        if not geom.intersects(zoom_poly):
            continue
        rate = geoid_to_rate.get(geoid)
        if rate is None:
            continue
        rows.append({"geometry": geom, "geoid": geoid, "disability_rate": rate})
    if not rows:
        return None
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


def _plot_combined_entrances_stations_map(
    *,
    boundary_geom,
    catalog: gpd.GeoDataFrame,
    entrances: gpd.GeoDataFrame,
    equipment: gpd.GeoDataFrame,
    path: Path,
    title: str,
    choropleth_underlay: gpd.GeoDataFrame | None = None,
    choropleth_vmax: float | None = None,
) -> None:
    """MTA catalog centroids (stars) + Open NY entrances (circles) + equipment."""

    boundary = gpd.GeoDataFrame({"geometry": [boundary_geom]}, crs="EPSG:4326")
    figure, axes = plt.subplots(figsize=(12, 11))
    if choropleth_underlay is not None and not choropleth_underlay.empty:
        _plot_faint_choropleth_underlay(
            axes,
            choropleth_underlay,
            0.45 if choropleth_vmax is None else choropleth_vmax,
        )
    boundary.plot(
        ax=axes,
        facecolor="none",
        edgecolor="#333333",
        linewidth=0.9,
        zorder=1,
    )

    for status in (
        "accessible",
        "partially_accessible",
        "not_accessible",
        "unknown",
    ):
        sub = catalog[catalog["ada_status"] == status]
        if sub.empty:
            continue
        color = _ADA_COLORS[status]
        sub.plot(
            ax=axes,
            color=color,
            marker="*",
            markersize=110,
            linewidth=0,
            zorder=4,
        )

    for status in (
        "accessible",
        "partially_accessible",
        "not_accessible",
        "unknown",
    ):
        sub = entrances[entrances["ada_status"] == status]
        if sub.empty:
            continue
        color = _ADA_COLORS[status]
        ms = 7 if len(entrances) > 2500 else 9 if len(entrances) > 1200 else 10
        sub.plot(
            ax=axes,
            color=color,
            marker="o",
            markersize=ms,
            linewidth=0,
            zorder=5,
        )

    if not equipment.empty:
        elev = equipment[equipment["kind"] == "elevator"]
        esc = equipment[equipment["kind"] == "escalator"]
        if not elev.empty:
            elev.plot(
                ax=axes,
                color="#1f1f1f",
                markersize=6,
                marker="o",
                linewidth=0,
                zorder=6,
            )
        if not esc.empty:
            esc.plot(
                ax=axes,
                color="#6a3d9a",
                markersize=7,
                marker="s",
                linewidth=0,
                zorder=6,
            )

    legend_handles: list[Line2D] = [
        Line2D(
            [0],
            [0],
            marker="*",
            linestyle="",
            color="#333333",
            label="MTA catalog station (★ = ADA color)",
            markersize=12,
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            color="#333333",
            label="Open NY entrance (● = ADA color)",
            markersize=8,
        ),
    ]
    legend_handles.extend(
        [
            Line2D(
                [0],
                [0],
                marker="o",
                linestyle="",
                color=_ADA_COLORS[status],
                label=f"Entrance - {status.replace('_', ' ')}",
                markersize=8,
            )
            for status in (
                "accessible",
                "partially_accessible",
                "not_accessible",
                "unknown",
            )
        ]
    )
    if not equipment.empty:
        legend_handles.append(
            Line2D(
                [0],
                [0],
                marker="o",
                linestyle="",
                color="#1f1f1f",
                label="Elevator (asset)",
                markersize=5,
            )
        )
        legend_handles.append(
            Line2D(
                [0],
                [0],
                marker="s",
                linestyle="",
                color="#6a3d9a",
                label="Escalator (asset)",
                markersize=6,
            )
        )

    axes.set_title(title, fontsize=11)
    axes.set_axis_off()
    axes.set_aspect("equal")
    axes.legend(handles=legend_handles, loc="lower left", fontsize=7.5, framealpha=0.94)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_grand_army_plaza_zoom(
    *,
    cache_root: Path,
    equipment_brooklyn: gpd.GeoDataFrame,
    path: Path,
) -> None:
    """Zoom: Web Mercator + optional OSM basemap; tract disability; links; large scatter markers.

    Plotting in EPSG:4326 with ``aspect=equal`` distorts east-west vs north-south scale at NYC
    latitudes, so entrances no longer line up with real geometry. Everything is drawn in
    **EPSG:3857** so positions match streets when a basemap is used.
    """

    zoom_poly = _geodesic_buffer_polygon(
        _GRAND_ARMY_PLAZA_LON,
        _GRAND_ARMY_PLAZA_LAT,
        _GRAND_ARMY_PLAZA_BUFFER_M,
    )
    crs_wm = "EPSG:3857"
    catalog = _station_catalog_gdf(cache_root, ("Brooklyn",)).to_crs(crs_wm)
    entrances = _entrances_gdf(cache_root, ("Brooklyn",)).to_crs(crs_wm)

    zoom_poly_wm = (
        gpd.GeoDataFrame({"geometry": [zoom_poly]}, crs="EPSG:4326")
        .to_crs(crs_wm)
        .geometry.iloc[0]
    )

    # ``intersects`` keeps entrances on the study-area edge; ``within`` can drop boundary points.
    catalog_z = catalog[catalog.intersects(zoom_poly_wm)].copy()
    entrances_z = entrances[entrances.intersects(zoom_poly_wm)].copy()
    equipment_wm = (
        equipment_brooklyn.to_crs(crs_wm)
        if not equipment_brooklyn.empty
        else equipment_brooklyn
    )
    equipment_z = (
        equipment_wm[equipment_wm.intersects(zoom_poly_wm)].copy()
        if not equipment_wm.empty
        else equipment_wm
    )

    tracts_gdf = _brooklyn_tracts_in_zoom(cache_root, zoom_poly)
    tracts_wm: gpd.GeoDataFrame | None = None
    if tracts_gdf is not None and not tracts_gdf.empty:
        tracts_wm = tracts_gdf.to_crs(crs_wm)

    minx, miny, maxx, maxy = zoom_poly_wm.bounds
    pad_x = (maxx - minx) * 0.06
    pad_y = (maxy - miny) * 0.06

    figure, axes = plt.subplots(figsize=(11, 10))
    axes.set_xlim(minx - pad_x, maxx + pad_x)
    axes.set_ylim(miny - pad_y, maxy + pad_y)

    if ctx is not None:
        try:
            ctx.add_basemap(
                axes,
                crs=crs_wm,
                source=ctx.providers.OpenStreetMap.Mapnik,
                alpha=0.92,
                zorder=0,
                attribution_size=6,
            )
        except (OSError, RuntimeError, ValueError):
            gpd.GeoDataFrame({"geometry": [zoom_poly_wm]}, crs=crs_wm).plot(
                ax=axes,
                color="#f2f2f2",
                edgecolor="#666666",
                linewidth=1.0,
                zorder=0,
            )
    else:
        gpd.GeoDataFrame({"geometry": [zoom_poly_wm]}, crs=crs_wm).plot(
            ax=axes,
            color="#f2f2f2",
            edgecolor="#666666",
            linewidth=1.0,
            zorder=0,
        )

    gpd.GeoDataFrame({"geometry": [zoom_poly_wm]}, crs=crs_wm).plot(
        ax=axes,
        facecolor="none",
        edgecolor="#222222",
        linewidth=1.4,
        zorder=1,
    )

    if tracts_wm is not None and not tracts_wm.empty:
        vmax = max(0.08, float(tracts_wm["disability_rate"].max()) * 1.08)
        tracts_wm.plot(
            ax=axes,
            column="disability_rate",
            cmap="viridis",
            alpha=0.38,
            edgecolor="white",
            linewidth=0.25,
            legend=True,
            legend_kwds={"label": "ACS disability rate (tract)"},
            vmin=0.0,
            vmax=min(vmax, 0.45),
            zorder=2,
        )

    station_by_gtfs: dict[str, Point] = {}
    for _, row in catalog.iterrows():
        gid = str(row.get("gtfs_stop_id") or "").strip()
        if gid and row.geometry is not None:
            station_by_gtfs[gid] = row.geometry

    if "gtfs_stop_id" in entrances_z.columns:
        for _, ent in entrances_z.iterrows():
            gid = str(ent.get("gtfs_stop_id") or "").strip()
            if not gid or gid not in station_by_gtfs:
                continue
            line = LineString([ent.geometry, station_by_gtfs[gid]])
            xs, ys = line.xy
            axes.plot(
                xs,
                ys,
                color="#1a1a1a",
                linewidth=1.35,
                alpha=0.55,
                zorder=3,
                solid_capstyle="round",
            )

    # Scatter ``s`` is marker area in points² — much larger than GeoPandas default for zoom maps.
    _GAP_STAR_S = 520.0
    _GAP_ENTRANCE_S = 200.0
    _GAP_ELEV_S = 130.0
    _GAP_ESC_S = 140.0

    for status in (
        "accessible",
        "partially_accessible",
        "not_accessible",
        "unknown",
    ):
        sub = catalog_z[catalog_z["ada_status"] == status]
        if sub.empty:
            continue
        xs = sub.geometry.x
        ys = sub.geometry.y
        axes.scatter(
            xs,
            ys,
            c=_ADA_COLORS[status],
            s=_GAP_STAR_S,
            marker="*",
            edgecolors="#1f1f1f",
            linewidths=0.6,
            zorder=5,
        )

    for status in (
        "accessible",
        "partially_accessible",
        "not_accessible",
        "unknown",
    ):
        sub = entrances_z[entrances_z["ada_status"] == status]
        if sub.empty:
            continue
        xs = sub.geometry.x
        ys = sub.geometry.y
        axes.scatter(
            xs,
            ys,
            c=_ADA_COLORS[status],
            s=_GAP_ENTRANCE_S,
            marker="o",
            edgecolors="white",
            linewidths=1.0,
            zorder=6,
        )

    if not equipment_z.empty:
        elev = equipment_z[equipment_z["kind"] == "elevator"]
        esc = equipment_z[equipment_z["kind"] == "escalator"]
        if not elev.empty:
            axes.scatter(
                elev.geometry.x,
                elev.geometry.y,
                c="#0d0d0d",
                s=_GAP_ELEV_S,
                marker="o",
                edgecolors="white",
                linewidths=0.5,
                zorder=7,
            )
        if not esc.empty:
            axes.scatter(
                esc.geometry.x,
                esc.geometry.y,
                c="#6a3d9a",
                s=_GAP_ESC_S,
                marker="s",
                edgecolors="white",
                linewidths=0.5,
                zorder=7,
            )

    axes.set_title(
        "Grand Army Plaza area (Brooklyn): OSM basemap + tract disability + station/entrance links",
        fontsize=11,
    )
    axes.set_axis_off()
    # Web Mercator: x/y are both meters — force 1:1 so entrances align with the basemap.
    axes.set_aspect(1.0)

    note = (
        f"Projected EPSG:3857 (~{_GRAND_ARMY_PLAZA_BUFFER_M:.0f} m buffer); lines join entrances "
        "to MTA catalog stops via gtfs_stop_id. Basemap © OpenStreetMap contributors."
    )
    axes.text(
        0.02,
        0.02,
        note,
        transform=axes.transAxes,
        fontsize=7.5,
        verticalalignment="bottom",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.9},
    )

    figure.tight_layout()
    figure.savefig(path, dpi=200)
    plt.close(figure)


def _plot_library_header_horizontal(
    *,
    cache_root: Path,
    boroughs: tuple[str, ...],
    path: Path,
) -> bool:
    """Wide horizontal banner (README/PyPI): OSM + tract disability + entrances + catalog.

    Atlantic / Downtown Brooklyn / Fort Greene strip — dense subway coverage and tract spread.
    """

    bbox_4326 = _geodesic_bbox_polygon(
        _LIB_HEADER_LON,
        _LIB_HEADER_LAT,
        _LIB_HEADER_WIDTH_M,
        _LIB_HEADER_HEIGHT_M,
    )
    crs_wm = "EPSG:3857"
    bbox_wm = gpd.GeoSeries([bbox_4326], crs="EPSG:4326").to_crs(crs_wm).iloc[0]

    choro_full, vmax_ch = _nyc_choropleth_base_with_vmax(cache_root, boroughs)
    tract_slice = _choropleth_slice_for_boundary(choro_full, bbox_4326)
    if tract_slice is None or tract_slice.empty:
        return False

    tracts_wm = tract_slice.to_crs(crs_wm)

    catalog = _station_catalog_gdf(cache_root, boroughs).to_crs(crs_wm)
    entrances = _entrances_gdf(cache_root, boroughs).to_crs(crs_wm)
    catalog_b = catalog[catalog.intersects(bbox_wm)].copy()
    entrances_b = entrances[entrances.intersects(bbox_wm)].copy()

    station_by_gtfs: dict[str, Point] = {}
    for _, row in catalog.iterrows():
        gid = str(row.get("gtfs_stop_id") or "").strip()
        if gid and row.geometry is not None:
            station_by_gtfs[gid] = row.geometry

    minx, miny, maxx, maxy = bbox_wm.bounds
    pad_x = (maxx - minx) * 0.015
    pad_y = (maxy - miny) * 0.06

    fig, ax = plt.subplots(figsize=(20, 6.8), facecolor="white")
    ax.set_xlim(minx - pad_x, maxx + pad_x)
    ax.set_ylim(miny - pad_y, maxy + pad_y)

    if ctx is not None:
        try:
            ctx.add_basemap(
                ax,
                crs=crs_wm,
                source=ctx.providers.OpenStreetMap.Mapnik,
                alpha=0.92,
                zorder=0,
                attribution_size=5,
            )
        except (OSError, RuntimeError, ValueError):
            gpd.GeoDataFrame({"geometry": [bbox_wm]}, crs=crs_wm).plot(
                ax=ax,
                color="#f0f0f0",
                edgecolor="#999999",
                zorder=0,
            )

    tracts_wm.plot(
        ax=ax,
        column="disability_rate",
        cmap="viridis",
        alpha=0.42,
        vmin=0.0,
        vmax=vmax_ch,
        missing_kwds={"color": "#e0e0e0", "alpha": 0.35},
        edgecolor="white",
        linewidth=0.12,
        zorder=1,
        legend=False,
    )

    norm = colors.Normalize(vmin=0.0, vmax=vmax_ch)
    sm = ScalarMappable(norm=norm, cmap="viridis")
    sm.set_array([])
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3.2%", pad=0.18)
    cbar = fig.colorbar(sm, cax=cax)
    cbar.ax.tick_params(labelsize=12)
    cbar.set_label("ACS disability rate (tract)", fontsize=14, fontweight="bold")

    if "gtfs_stop_id" in entrances_b.columns:
        for _, ent in entrances_b.iterrows():
            gid = str(ent.get("gtfs_stop_id") or "").strip()
            if not gid or gid not in station_by_gtfs:
                continue
            line = LineString([ent.geometry, station_by_gtfs[gid]])
            xs, ys = line.xy
            ax.plot(
                xs,
                ys,
                color="#1a1a1a",
                linewidth=0.9,
                alpha=0.4,
                zorder=2,
                solid_capstyle="round",
            )

    for status in (
        "accessible",
        "partially_accessible",
        "not_accessible",
        "unknown",
    ):
        sub = catalog_b[catalog_b["ada_status"] == status]
        if sub.empty:
            continue
        ax.scatter(
            sub.geometry.x,
            sub.geometry.y,
            c=_ADA_COLORS[status],
            s=320,
            marker="*",
            edgecolors="#1a1a1a",
            linewidths=0.45,
            zorder=4,
        )

    for status in (
        "accessible",
        "partially_accessible",
        "not_accessible",
        "unknown",
    ):
        sub = entrances_b[entrances_b["ada_status"] == status]
        if sub.empty:
            continue
        ax.scatter(
            sub.geometry.x,
            sub.geometry.y,
            c=_ADA_COLORS[status],
            s=120,
            marker="o",
            edgecolors="white",
            linewidths=0.8,
            zorder=5,
        )

    ax.set_aspect(1.0)
    ax.set_axis_off()

    fig.text(
        0.5,
        0.97,
        "NYC subway accessibility snapshot: street entrances, stations, and neighborhood disability",
        ha="center",
        fontsize=20,
        fontweight="bold",
        color="#111111",
    )
    fig.text(
        0.5,
        0.935,
        "Open NY entrances (●) and MTA catalog stops (★) colored by ADA; tracts = ACS 5-year "
        "disability rate (same vmax as package choropleths)",
        ha="center",
        fontsize=12.5,
        color="#333333",
    )

    sym_handles = [
        Line2D(
            [0],
            [0],
            marker="*",
            linestyle="",
            color="#333333",
            label="MTA catalog station (★)",
            markersize=16,
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            color="#333333",
            label="Open NY entrance (●)",
            markersize=12,
        ),
    ]
    ada_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            color=_ADA_COLORS[s],
            label=s.replace("_", " ").title(),
            markersize=11,
        )
        for s in (
            "accessible",
            "partially_accessible",
            "not_accessible",
            "unknown",
        )
    ]
    leg_sym = fig.legend(
        handles=sym_handles,
        loc="lower left",
        bbox_to_anchor=(0.07, 0.02),
        fontsize=11,
        framealpha=0.96,
        title="Symbols",
        title_fontsize=12,
    )
    fig.add_artist(leg_sym)
    fig.legend(
        handles=ada_handles,
        loc="lower left",
        bbox_to_anchor=(0.34, 0.02),
        fontsize=10.5,
        framealpha=0.96,
        ncol=4,
        title="ADA at entrance (join via gtfs_stop_id)",
        title_fontsize=12,
    )

    fig.text(
        0.5,
        0.045,
        "Basemap © OpenStreetMap contributors  ·  Open NY · MTA · ACS  ·  subway-access snapshot  ·  EPSG:3857",
        ha="center",
        fontsize=10,
        color="#555555",
    )

    fig.subplots_adjust(left=0.05, right=0.91, top=0.88, bottom=0.13)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white", pad_inches=0.25)
    plt.close(fig)
    return True


def _plot_station_equipment_map(
    *,
    boundary_geom,
    stations: gpd.GeoDataFrame,
    equipment: gpd.GeoDataFrame,
    path: Path,
    title: str,
    choropleth_underlay: gpd.GeoDataFrame | None = None,
    choropleth_vmax: float | None = None,
) -> None:
    boundary = gpd.GeoDataFrame({"geometry": [boundary_geom]}, crs="EPSG:4326")
    figure, axes = plt.subplots(figsize=(12, 11))
    if choropleth_underlay is not None and not choropleth_underlay.empty:
        _plot_faint_choropleth_underlay(
            axes,
            choropleth_underlay,
            0.45 if choropleth_vmax is None else choropleth_vmax,
        )
    boundary.plot(
        ax=axes,
        facecolor="none",
        edgecolor="#333333",
        linewidth=0.9,
        zorder=1,
    )

    legend_handles: list[Line2D] = []
    n_pts = len(stations)
    if "entrance_type" in stations.columns:
        point_ms = 7 if n_pts > 2500 else 9 if n_pts > 1200 else 10
    else:
        point_ms = 14

    for status in (
        "accessible",
        "partially_accessible",
        "not_accessible",
        "unknown",
    ):
        sub = stations[stations["ada_status"] == status]
        if sub.empty:
            continue
        color = _ADA_COLORS[status]
        sub.plot(
            ax=axes,
            color=color,
            markersize=point_ms,
            linewidth=0,
            zorder=4,
        )
        legend_handles.append(
            Line2D(
                [0],
                [0],
                marker="o",
                linestyle="",
                color=color,
                label=status.replace("_", " "),
                markersize=8,
            )
        )

    if not equipment.empty:
        elev = equipment[equipment["kind"] == "elevator"]
        esc = equipment[equipment["kind"] == "escalator"]
        if not elev.empty:
            elev.plot(
                ax=axes,
                color="#1f1f1f",
                markersize=6,
                marker="o",
                linewidth=0,
                zorder=5,
            )
            legend_handles.append(
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    linestyle="",
                    color="#1f1f1f",
                    label="Elevator (asset)",
                    markersize=5,
                )
            )
        if not esc.empty:
            esc.plot(
                ax=axes,
                color="#6a3d9a",
                markersize=7,
                marker="s",
                linewidth=0,
                zorder=5,
            )
            legend_handles.append(
                Line2D(
                    [0],
                    [0],
                    marker="s",
                    linestyle="",
                    color="#6a3d9a",
                    label="Escalator (asset)",
                    markersize=6,
                )
            )

    axes.set_title(title, fontsize=11)
    axes.set_axis_off()
    axes.set_aspect("equal")

    if legend_handles:
        axes.legend(
            handles=legend_handles,
            loc="lower left",
            fontsize=8,
            framealpha=0.92,
        )

    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def station_equipment_map_figures(
    cache_root: Path,
    boroughs: tuple[str, ...],
    *,
    figures_dir: Path,
) -> StationMapPaths | None:
    """Map entrance points (Open NY) or GTFS parent stops + MTA equipment on borough outlines.

    When cached ``entrances.geojson`` has rows, those street-level points are plotted (ADA
    color from ``gtfs_stop_id`` join). Otherwise falls back to GTFS ``stops.txt`` parent
    stations (requires ``gtfs_subway.zip`` under the first borough cache).

    Public **turnstile / ridership entry** counts are not part of the snapshot bundle.
    """

    cache_root = cache_root.expanduser().resolve()
    figures_dir.mkdir(parents=True, exist_ok=True)
    gtfs_zip = (
        download_logic.borough_cache_dir(cache_root, boroughs[0]) / "gtfs_subway.zip"
    )

    borough_polys: list[tuple[str, object]] = []
    for borough in boroughs:
        bdir = download_logic.borough_cache_dir(cache_root, borough)
        borough_polys.append((borough, _study_area_union(bdir)))

    union = unary_union([p for _, p in borough_polys])

    entrance_gdf = _entrances_gdf(cache_root, boroughs)
    if entrance_gdf.empty and not gtfs_zip.exists():
        return None

    if not entrance_gdf.empty:
        stations_city = entrance_gdf[entrance_gdf.within(union)].copy()
    else:
        parents = _load_gtfs_parent_stops(gtfs_zip)
        ada_map = _ada_by_gtfs_stop_id(cache_root, boroughs)
        parents = parents.copy()
        parents["ada_status"] = parents["gtfs_stop_id"].map(ada_map).fillna("unknown")
        stations_city = parents[parents.within(union)].copy()

    equipment_frames: list[gpd.GeoDataFrame] = []
    for borough in boroughs:
        assets = (
            download_logic.borough_cache_dir(cache_root, borough)
            / "mta-equipment-assets.json"
        )
        if assets.exists():
            equipment_frames.append(_load_equipment_points(assets))
    if equipment_frames:
        equipment_all = gpd.GeoDataFrame(
            pd.concat(equipment_frames, ignore_index=True),
            crs="EPSG:4326",
        )
    else:
        equipment_all = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    equipment_city = (
        equipment_all[equipment_all.within(union)].copy()
        if not equipment_all.empty
        else equipment_all
    )

    use_open_entrances = not entrance_gdf.empty
    choro_full, vmax_ch = _nyc_choropleth_base_with_vmax(cache_root, boroughs)
    underlay_nyc = _choropleth_slice_for_boundary(choro_full, union)

    nyc_title = (
        "Open NY entrances (ADA color) + MTA elevator/escalator assets — run boroughs"
        if use_open_entrances
        else "GTFS parent stops (ADA color) + MTA elevator/escalator assets — run boroughs"
    )
    nyc_path = figures_dir / "map-stations-equipment-nyc.png"
    _plot_station_equipment_map(
        boundary_geom=union,
        stations=stations_city,
        equipment=equipment_city,
        path=nyc_path,
        title=nyc_title,
        choropleth_underlay=underlay_nyc,
        choropleth_vmax=vmax_ch,
    )

    borough_paths: list[tuple[str, Path]] = []
    for borough, poly in borough_polys:
        slug = download_logic.borough_slug(borough)
        path = figures_dir / f"map-stations-equipment-{slug}.png"
        if use_open_entrances:
            stations_b = entrance_gdf[entrance_gdf.within(poly)].copy()
        else:
            stations_b = parents[parents.within(poly)].copy()
        equipment_b = (
            equipment_all[equipment_all.within(poly)].copy()
            if not equipment_all.empty
            else equipment_all
        )
        boro_title = (
            f"{borough}: Open NY entrances + equipment assets"
            if use_open_entrances
            else f"{borough}: GTFS parent stops + equipment assets"
        )
        underlay_b = _choropleth_slice_for_boundary(choro_full, poly)
        _plot_station_equipment_map(
            boundary_geom=poly,
            stations=stations_b,
            equipment=equipment_b,
            path=path,
            title=boro_title,
            choropleth_underlay=underlay_b,
            choropleth_vmax=vmax_ch,
        )
        borough_paths.append((borough, path))

    combined_nyc_path: Path | None = None
    combined_borough_paths: tuple[tuple[str, Path], ...] | None = None
    gap_zoom_path: Path | None = None

    if use_open_entrances:
        catalog_all = _station_catalog_gdf(cache_root, boroughs)
        ent_union = entrance_gdf[entrance_gdf.within(union)].copy()
        cat_union = catalog_all[catalog_all.within(union)].copy()
        combined_nyc_path = figures_dir / "map-combined-stations-entrances-nyc.png"
        _plot_combined_entrances_stations_map(
            boundary_geom=union,
            catalog=cat_union,
            entrances=ent_union,
            equipment=equipment_city,
            path=combined_nyc_path,
            title=(
                "MTA catalog stations (★) + Open NY entrances (●) + MTA equipment — "
                "NYC (all run boroughs)"
            ),
            choropleth_underlay=underlay_nyc,
            choropleth_vmax=vmax_ch,
        )
        comb_list: list[tuple[str, Path]] = []
        for borough, poly in borough_polys:
            slug = download_logic.borough_slug(borough)
            cpath = figures_dir / f"map-combined-stations-entrances-{slug}.png"
            equip_b = (
                equipment_all[equipment_all.within(poly)].copy()
                if not equipment_all.empty
                else equipment_all
            )
            underlay_cb = _choropleth_slice_for_boundary(choro_full, poly)
            _plot_combined_entrances_stations_map(
                boundary_geom=poly,
                catalog=catalog_all[catalog_all.within(poly)].copy(),
                entrances=entrance_gdf[entrance_gdf.within(poly)].copy(),
                equipment=equip_b,
                path=cpath,
                title=f"{borough}: MTA catalog (★) + Open NY entrances (●) + equipment",
                choropleth_underlay=underlay_cb,
                choropleth_vmax=vmax_ch,
            )
            comb_list.append((borough, cpath))
        combined_borough_paths = tuple(comb_list)

    if "Brooklyn" in boroughs and use_open_entrances:
        brooklyn_assets = (
            download_logic.borough_cache_dir(cache_root, "Brooklyn")
            / "mta-equipment-assets.json"
        )
        equip_brooklyn = (
            _load_equipment_points(brooklyn_assets)
            if brooklyn_assets.exists()
            else gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        )
        gap_zoom_path = figures_dir / "map-zoom-grand-army-plaza-detail.png"
        _plot_grand_army_plaza_zoom(
            cache_root=cache_root,
            equipment_brooklyn=equip_brooklyn,
            path=gap_zoom_path,
        )

    library_header_path: Path | None = None
    if use_open_entrances and "Brooklyn" in boroughs:
        lib_path = figures_dir / "map-library-header-horizontal.png"
        if _plot_library_header_horizontal(
            cache_root=cache_root,
            boroughs=boroughs,
            path=lib_path,
        ):
            library_header_path = lib_path

    return StationMapPaths(
        nyc=nyc_path,
        by_borough=tuple(borough_paths),
        combined_nyc=combined_nyc_path,
        combined_by_borough=combined_borough_paths,
        grand_army_plaza_zoom=gap_zoom_path,
        library_header_horizontal=library_header_path,
    )


def sample_eda_figures(
    cache_root: Path,
    boroughs: tuple[str, ...],
    *,
    figures_dir: Path,
    artifacts_dir: Path,
    seed: int = 42,
    sample_n: int = 40,
) -> tuple[Path, Path]:
    """Random-sample tracts for a histogram and bar chart of row counts by borough."""
    rng = random.Random(seed)
    cache_root = cache_root.expanduser().resolve()
    figures_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    by_borough_stations: list[int] = []
    by_borough_tracts: list[int] = []
    by_borough_entrances: list[int] = []
    labels: list[str] = []
    disability_samples: list[float] = []

    for borough in boroughs:
        bdir = download_logic.borough_cache_dir(cache_root, borough)
        snapshot = pipeline.load_cached_snapshot(bdir)
        labels.append(borough.split()[0])
        by_borough_stations.append(len(snapshot.stations.stations))
        by_borough_tracts.append(len(snapshot.demographics.tracts))
        by_borough_entrances.append(len(snapshot.entrances.entrances))
        tracts = list(snapshot.demographics.tracts)
        if tracts:
            picked = rng.sample(tracts, min(sample_n, len(tracts)))
            disability_samples.extend(t.disability_rate for t in picked)

    bar_path = figures_dir / "record-counts-by-borough.png"
    figure, axes = plt.subplots(figsize=(12, 5.5))
    x = range(len(labels))
    width = 0.25
    axes.bar(
        [i - width for i in x],
        by_borough_stations,
        width,
        label="Stations (MTA catalog)",
        color="#4c78a8",
    )
    axes.bar(
        list(x),
        by_borough_tracts,
        width,
        label="Tracts (ACS)",
        color="#f58518",
    )
    axes.bar(
        [i + width for i in x],
        by_borough_entrances,
        width,
        label="Entrances (Open NY)",
        color="#54a24b",
    )
    axes.set_xticks(list(x))
    axes.set_xticklabels(labels, rotation=15, ha="right")
    axes.set_ylabel("Row count")
    axes.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    axes.set_title(
        "Snapshot scale by borough — stations vs census tracts vs street-level entrances"
    )
    axes.legend(loc="upper left", fontsize=9)
    figure.tight_layout()
    figure.savefig(bar_path, dpi=180)
    plt.close(figure)

    hist_path = figures_dir / "sampled-disability-rate.png"
    figure2, axes2 = plt.subplots(figsize=(8, 5))
    axes2.hist(disability_samples, bins=16, color="#72b7b2", edgecolor="white")
    axes2.set_xlabel("Disability rate (sampled tracts)")
    axes2.set_ylabel("Count")
    axes2.set_title("Distribution of sampled tract disability rates")
    figure2.tight_layout()
    figure2.savefig(hist_path, dpi=180)
    plt.close(figure2)

    sample_csv = artifacts_dir / "tract-sample-seed.csv"
    with sample_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["borough", "tract_id", "disability_rate", "poverty_rate"],
        )
        writer.writeheader()
        for borough in boroughs:
            bdir = download_logic.borough_cache_dir(cache_root, borough)
            snapshot = pipeline.load_cached_snapshot(bdir)
            tracts = list(snapshot.demographics.tracts)
            if not tracts:
                continue
            picked = rng.sample(tracts, min(5, len(tracts)))
            for t in picked:
                writer.writerow(
                    {
                        "borough": borough,
                        "tract_id": t.tract_id,
                        "disability_rate": f"{t.disability_rate:.4f}",
                        "poverty_rate": f"{t.poverty_rate:.4f}",
                    }
                )

    return bar_path, hist_path


def entrance_layer_figures(
    cache_root: Path,
    boroughs: tuple[str, ...],
    *,
    figures_dir: Path,
) -> EntranceLayerPaths | None:
    """Charts for Open NY entrance rows: per-GTFS-stop counts, ADA mix, types, borough ratios.

    Returns ``None`` when no cached entrances exist across the run.
    """

    cache_root = cache_root.expanduser().resolve()
    figures_dir.mkdir(parents=True, exist_ok=True)

    ada_map = _ada_by_gtfs_stop_id(cache_root, boroughs)
    per_stop: Counter[str] = Counter()
    ada_entrance_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    total_entrances = 0

    for borough in boroughs:
        bdir = download_logic.borough_cache_dir(cache_root, borough)
        snapshot = pipeline.load_cached_snapshot(bdir)
        ds = snapshot.entrances
        if not ds.entrances:
            continue
        per_stop.update(ds.count_by_gtfs_stop_id())
        for ent in ds.entrances:
            total_entrances += 1
            gid = ent.gtfs_stop_id
            status = ada_map.get(gid, "unknown") if gid else "unknown"
            ada_entrance_counts[status] += 1
            label = (ent.entrance_type or "").strip() or "(blank)"
            type_counts[label] += 1

    if total_entrances == 0:
        return None

    # --- Histogram: how many street entrances per GTFS parent stop (stations with ≥1 entrance)
    counts_per_station = list(per_stop.values())
    hist_path = figures_dir / "entrances-per-gtfs-stop-distribution.png"
    figure, axes = plt.subplots(figsize=(9, 5))
    if counts_per_station:
        max_c = max(counts_per_station)
        bins = min(35, max(8, max_c + 1))
        axes.hist(
            counts_per_station,
            bins=bins,
            color="#54a24b",
            edgecolor="white",
            linewidth=0.6,
        )
        axes.set_xlabel("Open NY entrance/exit count per GTFS parent stop")
        axes.set_ylabel("Number of parent stops")
        axes.set_title(
            "Street-level entrances per station (GTFS parent stops with ≥1 entrance in study area)"
        )
        axes.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    else:
        axes.text(
            0.5,
            0.55,
            "No entrances carry a non-empty gtfs_stop_id,\n"
            "so a per-parent-stop distribution cannot be built.",
            ha="center",
            va="center",
            fontsize=11,
        )
        axes.set_axis_off()
        axes.set_title("Entrances per GTFS parent stop (unavailable)")
    figure.tight_layout()
    figure.savefig(hist_path, dpi=180)
    plt.close(figure)

    # --- Bar: ADA status at each entrance point (join via gtfs_stop_id)
    ada_path = figures_dir / "entrances-ada-status-counts.png"
    figure2, axes2 = plt.subplots(figsize=(8, 4.8))
    order = ("accessible", "partially_accessible", "not_accessible", "unknown")
    labels_nice = [s.replace("_", " ").title() for s in order]
    values = [ada_entrance_counts.get(s, 0) for s in order]
    colors = [_ADA_COLORS[s] for s in order]
    bars = axes2.bar(
        labels_nice, values, color=colors, edgecolor="white", linewidth=0.6
    )
    axes2.set_ylabel("Entrance points")
    axes2.set_title("ADA status at each Open NY entrance (from station catalog join)")
    axes2.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    for bar, v in zip(bars, values, strict=True):
        if v > 0:
            axes2.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{v:,}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    figure2.tight_layout()
    figure2.savefig(ada_path, dpi=180)
    plt.close(figure2)

    # --- Bar: mean entrances per catalog station by borough
    ratio_path = figures_dir / "entrances-per-station-ratio-by-borough.png"
    figure3, axes3 = plt.subplots(figsize=(10, 5))
    short_labels: list[str] = []
    ratios: list[float] = []
    for borough in boroughs:
        bdir = download_logic.borough_cache_dir(cache_root, borough)
        snapshot = pipeline.load_cached_snapshot(bdir)
        n_st = len(snapshot.stations.stations)
        n_ent = len(snapshot.entrances.entrances)
        short_labels.append(borough.split()[0])
        ratios.append(n_ent / n_st if n_st else 0.0)
    x_pos = range(len(short_labels))
    axes3.bar(x_pos, ratios, color="#3b6ea5", edgecolor="white", linewidth=0.6)
    axes3.set_xticks(list(x_pos))
    axes3.set_xticklabels(short_labels, rotation=15, ha="right")
    axes3.set_ylabel("Mean entrances per MTA catalog station")
    axes3.set_title(
        "Open NY entrance count ÷ station catalog count (per borough study area)"
    )
    axes3.yaxis.set_major_formatter(StrMethodFormatter("{x:,.2f}"))
    figure3.tight_layout()
    figure3.savefig(ratio_path, dpi=180)
    plt.close(figure3)

    # --- Horizontal bar: top entrance_type labels from Open NY
    types_path = figures_dir / "entrances-open-ny-type-top.png"
    top_n = 15
    most_common = type_counts.most_common(top_n)
    figure4, axes4 = plt.subplots(figsize=(9, max(4.0, 0.35 * len(most_common) + 1.5)))
    types_labels = [t[0][:48] + ("…" if len(t[0]) > 48 else "") for t in most_common]
    types_vals = [t[1] for t in most_common]
    y_pos = range(len(types_labels))
    axes4.barh(
        list(y_pos), types_vals, color="#72b7b2", edgecolor="white", linewidth=0.5
    )
    axes4.set_yticks(list(y_pos))
    axes4.set_yticklabels(types_labels, fontsize=8)
    axes4.invert_yaxis()
    axes4.set_xlabel("Entrance points")
    axes4.set_title("Top Open NY entrance_type values (raw labels)")
    axes4.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    figure4.tight_layout()
    figure4.savefig(types_path, dpi=180)
    plt.close(figure4)

    return EntranceLayerPaths(
        per_stop_distribution=hist_path,
        ada_by_entrance=ada_path,
        ratio_by_borough=ratio_path,
        entrance_types_top=types_path,
    )


def choropleth_disability_figures(
    cache_root: Path,
    boroughs: tuple[str, ...],
    *,
    figures_dir: Path,
) -> ChoroplethPaths:
    """Map ACS disability rate onto real census tract boundaries (citywide + per borough).

    Uses ``nyc_geo_toolkit.load_nyc_census_tracts()`` for geometries and merges values
    from cached ``StudyAreaSnapshot`` demographics (read-only).
    """
    cache_root = cache_root.expanduser().resolve()
    figures_dir.mkdir(parents=True, exist_ok=True)

    geoid_to_rate: dict[str, float] = {}
    for borough in boroughs:
        bdir = download_logic.borough_cache_dir(cache_root, borough)
        snapshot = pipeline.load_cached_snapshot(bdir)
        for tract in snapshot.demographics.tracts:
            geoid_to_rate[tract.tract_id] = tract.disability_rate

    fc = load_nyc_census_tracts()
    rows: list[dict[str, object]] = []
    for feature in fc.features:
        props = feature.properties
        geoid = str(props.get("geoid") or getattr(feature, "geography_value", ""))
        borough_code = str(props.get("borough", ""))
        geom = shape(feature.geometry)
        rows.append({"geoid": geoid, "borough": borough_code, "geometry": geom})

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    gdf["disability_rate"] = gdf["geoid"].map(geoid_to_rate)

    rate_series = gdf["disability_rate"].dropna()
    vmax = float(rate_series.max()) if len(rate_series) else 0.1
    vmax = max(0.05, min(vmax * 1.05, 0.55))

    def _plot_tracts(sub: gpd.GeoDataFrame, path: Path, title: str) -> None:
        figure, axes = plt.subplots(figsize=(12, 11))
        sub.plot(
            column="disability_rate",
            ax=axes,
            cmap="viridis",
            legend=True,
            legend_kwds={"label": "Disability rate (ACS)"},
            missing_kwds={"color": "#e0e0e0"},
            vmin=0.0,
            vmax=vmax,
            edgecolor="white",
            linewidth=0.15,
        )
        axes.set_title(title)
        axes.set_axis_off()
        figure.tight_layout()
        figure.savefig(path, dpi=160)
        plt.close(figure)

    nyc_path = figures_dir / "choropleth-disability-nyc.png"
    _plot_tracts(
        gdf,
        nyc_path,
        "NYC census tracts: disability rate (snapshot tracts merged onto toolkit geometry)",
    )

    borough_paths: list[tuple[str, Path]] = []
    for borough in boroughs:
        toolkit_label = _TOOLKIT_BOROUGH_BY_NAME.get(borough)
        if toolkit_label is None:
            continue
        sub = gdf[gdf["borough"] == toolkit_label]
        if sub.empty:
            continue
        slug = download_logic.borough_slug(borough)
        path = figures_dir / f"choropleth-disability-{slug}.png"
        _plot_tracts(sub, path, f"{borough}: disability rate by census tract")
        borough_paths.append((borough, path))

    return ChoroplethPaths(nyc=nyc_path, by_borough=tuple(borough_paths))

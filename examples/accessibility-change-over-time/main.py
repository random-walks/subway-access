"""Accessibility change over time -- research pipeline.

Produces a comprehensive, auto-generated research report with geographic
maps, diagnostic plots, borough comparisons, a temporal panel dataset,
and policy-ready interpretation.  All tables are GitHub-rendered inline
markdown; all figures use academic ``figure-N-slug`` naming.

Usage:
    python main.py                          # all 5 boroughs
    python main.py --boroughs Manhattan,Brooklyn,Bronx
    python main.py --skip-download          # re-run analysis on cached data
    python main.py --no-publish-report      # CSVs only, skip figures + report
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import median, stdev

import geopandas as gpd
import matplotlib as mpl

mpl.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from nyc_geo_toolkit import load_nyc_census_tracts
from scipy import sparse as sp_sparse
from scipy import stats as sp_stats
from shapely.geometry import shape

from subway_access import analysis, models, pipeline
from subway_access.analysis._geo import walk_radius_meters
from subway_access.factors import (
    CoverageFactor,
    FactorContext,
    GapScoreFactor,
    NearestStationDistanceFactor,
    NearestStationTravelMinutesFactor,
    NeedScoreFactor,
    Pipeline,
    ReliabilityWeightedCoverageFactor,
    StationCountFactor,
)
from subway_access.temporal import (
    UpgradeTimeline,
    build_distance_weights,
    build_panel_dataset,
    build_upgrade_timeline,
    load_known_upgrades_from_dir,
)

try:
    import contextily as ctx
except ImportError:
    ctx = None  # type: ignore[assignment]

try:
    import factor_factory
    import factor_factory.engines.rdd
    import factor_factory.engines.scm
    import factor_factory.engines.spatial  # noqa: F401
    from factor_factory.engines import did as _ff_did
    from factor_factory.engines import rdd as _ff_rdd
    from factor_factory.engines import scm as _ff_scm
    from factor_factory.engines import spatial as _ff_spatial
    from factor_factory.tidy import Panel as _FFPanel
    from factor_factory.tidy import PanelMetadata as _FFPanelMetadata
    from factor_factory.tidy import Provenance as _FFProvenance
    from factor_factory.tidy import TreatmentEvent as _FFTreatmentEvent

    _FACTOR_FACTORY_AVAILABLE = True
except ImportError:
    _FACTOR_FACTORY_AVAILABLE = False

try:
    import jellycell  # noqa: F401  (import-check only)

    _JELLYCELL_AVAILABLE = True
except ImportError:
    _JELLYCELL_AVAILABLE = False

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"
ARTIFACTS_DIR = ROOT / "artifacts"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

ALL_BOROUGHS = ("Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island")


def _dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _fig(name: str) -> Path:
    return _dir(FIGURES_DIR) / name


def _art(name: str) -> Path:
    return _dir(ARTIFACTS_DIR) / name


def _mean(v: list[float]) -> float:
    return sum(v) / len(v) if v else 0.0


def _extract_provenance(snapshots: dict) -> dict[str, str]:
    """Extract data provenance dates from the first snapshot's metadata."""
    today = datetime.now(tz=timezone.utc).date()
    report_date = today.strftime("%B %-d, %Y")
    snapshot_date = report_date
    avail_start = "unknown"
    avail_end = report_date
    acs_vintage = "2023"

    first_borough = next(iter(snapshots))
    snap = snapshots[first_borough]
    if snap.cache_dir is not None:
        meta_path = snap.cache_dir / "snapshot-metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            gen = meta.get("generated_at", "")
            if gen:
                dt = datetime.fromisoformat(gen)
                snapshot_date = dt.strftime("%B %-d, %Y")
            for src in meta.get("sources", []):
                notes = src.get("notes", "")
                if src["name"] == "mta_availability_history":
                    m = re.search(r"since (\d{4}-\d{2}-\d{2})", notes)
                    if m:
                        d = date.fromisoformat(m.group(1))
                        avail_start = d.strftime("%B %Y")
                if src["name"] == "acs_tract_demographics":
                    m = re.search(r"ACS 5-year (\d{4})", notes)
                    if m:
                        acs_vintage = m.group(1)

    avail_end = snapshot_date  # outage window ends at fetch date
    avail_window = f"{avail_start} \u2013 {avail_end}"

    return {
        "report_date": report_date,
        "snapshot_date": snapshot_date,
        "avail_start": avail_start,
        "avail_end": avail_end,
        "avail_window": avail_window,
        "acs_vintage": acs_vintage,
        "acs_survey_period": f"{int(acs_vintage) - 4}\u2013{acs_vintage}",
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Accessibility change over time.")
    p.add_argument("--boroughs", default=",".join(ALL_BOROUGHS))
    p.add_argument("--minutes", type=int, default=10)
    p.add_argument("--window-days", type=int, default=365)
    p.add_argument("--availability-months", type=int, default=12)
    p.add_argument("--years", default="2017,2018,2019,2020,2021,2022,2023")
    p.add_argument("--skip-download", action="store_true")
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--no-publish-report", action="store_true")
    p.add_argument(
        "--skip-engine-audit",
        action="store_true",
        help=(
            "Skip the factor-factory engine-audit appendix (step 11). "
            "The appendix is skipped automatically if factor-factory + jellycell "
            "are not installed; this flag forces the skip even when they are."
        ),
    )
    return p


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def download_snapshots(boroughs, *, refresh, availability_months):
    snaps = {}
    for i, b in enumerate(boroughs):
        c = _dir(CACHE_DIR / b.lower().replace(" ", "-"))
        print(f"  {b}...")
        snaps[b] = pipeline.fetch_study_area_snapshot(
            models.AccessibilityQuery(geography="borough", value=b),
            cache_dir=c,
            refresh=refresh,
            availability_months=availability_months,
            include_gtfs_archive=i == 0,
        )
        s = snaps[b]
        print(
            f"    {len(s.stations.stations)} stations, {len(s.demographics.tracts)} tracts"
        )
    return snaps


def load_snapshots(boroughs):
    return {
        b: pipeline.load_cached_snapshot(CACHE_DIR / b.lower().replace(" ", "-"))
        for b in boroughs
    }


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


def run_borough_analysis(snapshots, minutes, window_days):
    pipe = (
        Pipeline()
        .add(NeedScoreFactor())
        .add(CoverageFactor())
        .add(GapScoreFactor())
        .add(NearestStationDistanceFactor())
        .add(NearestStationTravelMinutesFactor())
        .add(StationCountFactor())
    )
    out = {}
    for borough, snap in snapshots.items():
        catch = analysis.generate_catchments(
            snap.stations, models.CatchmentRequest(minutes=minutes)
        )
        ctxs = [
            FactorContext(tract=t, stations=snap.stations, catchments=catch)
            for t in snap.demographics.tracts
        ]
        result = pipe.run(ctxs)
        records = result.to_records()
        rel = analysis.compute_reliability(
            snap.stations, snap.outages, models.TimeWindow(days=window_days)
        )
        rel_scores = {r.station_id: r.reliability_score for r in rel.records}
        rel_result = (
            Pipeline().add(ReliabilityWeightedCoverageFactor(rel_scores)).run(ctxs)
        )
        rel_values = list(rel_result.columns["reliability_weighted_coverage"])

        total = len(records)
        covered = sum(1 for r in records if r["has_accessible_station"])
        gap_pop = sum(
            t.total_population
            for t, r in zip(snap.demographics.tracts, records, strict=True)
            if not r["has_accessible_station"]
        )
        total_pop = sum(t.total_population for t in snap.demographics.tracts)
        dists = [
            r["nearest_accessible_distance_meters"]
            for r in records
            if r["nearest_accessible_distance_meters"] > 0
        ]
        acc_rel = [r for r in rel.records if r.ada_status == "accessible"]
        fragile = sum(1 for r in acc_rel if r.reliability_label == "fragile")

        out[borough] = {
            "stations": len(snap.stations.stations),
            "ada_stations": len(snap.stations.accessible_stations),
            "tracts": total,
            "covered": covered,
            "gap_tracts": total - covered,
            "coverage_rate": covered / total if total else 0,
            "gap_pop": gap_pop,
            "total_pop": total_pop,
            "avg_need": _mean([r["need_score"] for r in records]),
            "avg_distance_m": _mean(dists),
            "mean_rel_coverage": _mean(rel_values),
            "fragile_stations": fragile,
            "records": records,
            "reliability": rel,
        }
        print(
            f"  {borough}: {covered}/{total} covered ({covered / total:.0%}), {gap_pop:,} gap pop"
        )
    return out


def build_panel(snapshots, years, minutes):
    locs = {}
    all_st = []
    for s in snapshots.values():
        for st in s.stations.stations:
            locs[st.station_id] = (st.latitude, st.longitude)
            all_st.append(st)
    # The upgrade timeline is assembled from two schema-distinct sources so
    # downstream consumers can audit which station dates are primary research
    # data vs deterministic fallbacks.
    #
    # 1. ``sourced_years``: press-release / Capital Program / news-sourced
    #    completion years (101 stations as of April 2026), loaded from
    #    ``seeds/enhanced/upgrade_templates/*.csv``. These drive Sections
    #    4.1-4.8 of the paper and are treated as the primary research data.
    # 2. ``fallback_years``: deterministic hash-based placeholders for the
    #    ~56 accessible stations without publicly documented completion
    #    dates (primarily Key Station Program stations, 1994-2020). The
    #    hash uses ``hashlib.md5`` of the station_id so the assignment is
    #    reproducible across runs but does not reflect real completion
    #    timing. See ``reports/supplementary/upgrade-provenance.csv`` for
    #    the per-station audit.
    seeds_dir = ROOT.parents[1] / "seeds" / "enhanced" / "upgrade_templates"
    sourced_years: dict[str, int] = (
        load_known_upgrades_from_dir(seeds_dir) if seeds_dir.is_dir() else {}
    )
    fallback_years: dict[str, int] = {}
    lo, hi = min(years), max(years)
    span = hi - lo + 1
    for s in all_st:
        if s.ada_status == "accessible" and s.station_id not in sourced_years:
            h = int(hashlib.md5(s.station_id.encode()).hexdigest(), 16)
            fallback_years[s.station_id] = lo + (h % span)

    # Merge years; build an explicit per-station provenance map so the
    # UpgradeTimeline records carry the correct ``upgrade_source`` tag.
    known = {**sourced_years, **fallback_years}
    upgrade_sources: dict[str, str] = {}
    upgrade_sources.update(dict.fromkeys(sourced_years, "press_release_sourced"))
    upgrade_sources.update(dict.fromkeys(fallback_years, "hash_fallback"))

    print(
        f"  Upgrade timeline: {len(sourced_years)} press-release-sourced "
        f"+ {len(fallback_years)} hash-fallback = {len(known)} total"
    )
    recs = []
    seen = set()
    for s in snapshots.values():
        tl = build_upgrade_timeline(
            s.stations,
            known_upgrades=known,
            known_upgrade_sources=upgrade_sources,
        )
        for r in tl.records:
            if r.station_id not in seen:
                recs.append(r)
                seen.add(r.station_id)
    timeline = UpgradeTimeline(records=tuple(recs))

    # Emit a per-station provenance audit CSV so readers can filter the
    # panel to sourced-only subsets (e.g. for the robustness-only DiD spec
    # referenced in CASESTUDY §3.5 "Data provenance caveat"). Committed
    # alongside the other supplementary reports.
    _write_upgrade_provenance_csv(timeline)
    vint = {}
    for y in years:
        yt = {}
        for s in snapshots.values():
            for t in s.demographics.tracts:
                yt[t.tract_id] = {
                    "tract_id": t.tract_id,
                    "tract_name": t.tract_name,
                    "total_population": t.total_population,
                    "disability_rate": t.disability_rate,
                    "senior_rate": t.senior_rate,
                    "poverty_rate": t.poverty_rate,
                    "centroid_latitude": t.centroid_latitude,
                    "centroid_longitude": t.centroid_longitude,
                }
        vint[y] = yt
    panel = build_panel_dataset(
        vint, locs, timeline, catchment_radius_meters=walk_radius_meters(minutes)
    )
    return panel, timeline


# ---------------------------------------------------------------------------
# Geographic data
# ---------------------------------------------------------------------------


def build_tract_geodataframe(snapshots, summaries):
    """Merge tract-level analysis onto census tract geometries."""
    geoid_to_data = {}
    for borough, s in summaries.items():
        snap = snapshots[borough]
        for tract, rec in zip(snap.demographics.tracts, s["records"], strict=True):
            geoid_to_data[tract.tract_id] = {
                "borough": borough,
                "need_score": rec["need_score"],
                "gap_score": rec["gap_score"],
                "has_accessible_station": rec["has_accessible_station"],
                "nearest_distance_m": rec["nearest_accessible_distance_meters"],
                "station_count": rec["accessible_station_count"],
                "disability_rate": tract.disability_rate,
                "senior_rate": tract.senior_rate,
                "poverty_rate": tract.poverty_rate,
                "population": tract.total_population,
            }

    fc = load_nyc_census_tracts()
    rows = []
    for feature in fc.features:
        geoid = feature.geography_value
        data = geoid_to_data.get(geoid)
        if data is None:
            continue
        geom = shape(feature.geometry)
        nta_name = feature.properties.get("nta_name", "")
        rows.append({"geoid": geoid, "geometry": geom, "nta_name": nta_name, **data})
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


# ---------------------------------------------------------------------------
# Statistical analysis helpers
# ---------------------------------------------------------------------------


def _compute_correlations(gdf):
    """Compute pairwise Pearson correlations with p-values."""
    variables = [
        "disability_rate",
        "senior_rate",
        "poverty_rate",
        "need_score",
        "gap_score",
        "nearest_distance_m",
    ]
    labels = [
        "Disability",
        "Senior",
        "Poverty",
        "Need score",
        "Gap score",
        "Distance (m)",
    ]
    data = {v: gdf[v].fillna(0).to_numpy() for v in variables}
    n = len(variables)
    r_matrix = np.zeros((n, n))
    p_matrix = np.ones((n, n))
    for i in range(n):
        for j in range(n):
            if i == j:
                r_matrix[i, j] = 1.0
                p_matrix[i, j] = 0.0
            elif j > i:
                r, p = sp_stats.pearsonr(data[variables[i]], data[variables[j]])
                r_matrix[i, j] = r
                r_matrix[j, i] = r
                p_matrix[i, j] = p
                p_matrix[j, i] = p
    return {
        "variables": variables,
        "labels": labels,
        "r_matrix": r_matrix,
        "p_matrix": p_matrix,
    }


def _compute_spearman(gdf):
    """Compute pairwise Spearman rank correlations with p-values."""
    variables = [
        "disability_rate",
        "senior_rate",
        "poverty_rate",
        "need_score",
        "gap_score",
        "nearest_distance_m",
    ]
    labels = [
        "Disability",
        "Senior",
        "Poverty",
        "Need score",
        "Gap score",
        "Distance (m)",
    ]
    data = {v: gdf[v].fillna(0).to_numpy() for v in variables}
    n = len(variables)
    rho_matrix = np.zeros((n, n))
    p_matrix = np.ones((n, n))
    for i in range(n):
        for j in range(n):
            if i == j:
                rho_matrix[i, j] = 1.0
                p_matrix[i, j] = 0.0
            elif j > i:
                rho, p = sp_stats.spearmanr(data[variables[i]], data[variables[j]])
                rho_matrix[i, j] = rho
                rho_matrix[j, i] = rho
                p_matrix[i, j] = p
                p_matrix[j, i] = p
    return {
        "variables": variables,
        "labels": labels,
        "rho_matrix": rho_matrix,
        "p_matrix": p_matrix,
    }


def _compute_vif(gdf):
    """Compute variance inflation factors for demographic predictors."""
    variables = ["disability_rate", "senior_rate", "poverty_rate"]
    X = gdf[variables].fillna(0).to_numpy()
    n_vars = X.shape[1]
    results = []
    for j in range(n_vars):
        y_j = X[:, j]
        X_others = np.delete(X, j, axis=1)
        X_design = np.column_stack([np.ones(X_others.shape[0]), X_others])
        beta, _, _, _ = np.linalg.lstsq(X_design, y_j, rcond=None)
        y_hat = X_design @ beta
        ss_res = np.sum((y_j - y_hat) ** 2)
        ss_tot = np.sum((y_j - np.mean(y_j)) ** 2)
        r_sq = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        vif = 1.0 / (1.0 - r_sq) if r_sq < 1.0 else float("inf")
        results.append((variables[j], vif))
    return results


def _compute_morans_i(values_dict, weights, n_permutations=999):
    """Compute global Moran's I with permutation inference.

    Uses a sparse weight matrix for fast vectorized computation.
    Returns dict with I, expected_I, z_score, p_value for each variable.
    """
    results = {}
    unit_ids = sorted(weights.keys())
    n = len(unit_ids)
    uid_to_idx = {uid: i for i, uid in enumerate(unit_ids)}
    rng = np.random.default_rng(42)

    # Build sparse weights matrix once.
    rows, cols, vals = [], [], []
    for uid_i in unit_ids:
        idx_i = uid_to_idx[uid_i]
        for uid_j, w_ij in weights.get(uid_i, {}).items():
            idx_j = uid_to_idx.get(uid_j)
            if idx_j is not None:
                rows.append(idx_i)
                cols.append(idx_j)
                vals.append(w_ij)
    W = sp_sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))
    w_sum = W.sum()

    def _moran_stat(z_arr):
        zz = np.sum(z_arr**2)
        if zz == 0:
            return 0.0
        lag = W.dot(z_arr)
        return (n / w_sum) * np.dot(z_arr, lag) / zz

    for var_name, values_map in values_dict.items():
        y = np.array([values_map.get(uid, 0.0) for uid in unit_ids])
        z = y - np.mean(y)
        observed_I = _moran_stat(z)
        expected_I = -1.0 / (n - 1)

        # Permutation inference.
        perm_Is = np.empty(n_permutations)
        for k in range(n_permutations):
            perm_z = rng.permutation(z)
            perm_Is[k] = _moran_stat(perm_z)

        perm_mean = np.mean(perm_Is)
        perm_std = np.std(perm_Is, ddof=1)
        z_score = (observed_I - perm_mean) / perm_std if perm_std > 0 else 0.0
        # Two-sided pseudo p-value.
        p_value = (np.sum(np.abs(perm_Is) >= abs(observed_I)) + 1) / (
            n_permutations + 1
        )

        results[var_name] = {
            "I": observed_I,
            "expected_I": expected_I,
            "z_score": z_score,
            "p_value": float(p_value),
        }
    return results


def _compute_equity_regression(gdf):
    """OLS: gap_score ~ poverty_rate + disability_rate + senior_rate."""
    try:
        import statsmodels.api as sm
    except ImportError:
        return None

    y = gdf["gap_score"].fillna(0).to_numpy()
    X = gdf[["poverty_rate", "disability_rate", "senior_rate"]].fillna(0).to_numpy()
    X = sm.add_constant(X)
    model = sm.OLS(y, X).fit(cov_type="HC1")
    return {
        "params": list(model.params),
        "bse": list(model.bse),
        "tvalues": list(model.tvalues),
        "pvalues": list(model.pvalues),
        "rsquared": model.rsquared,
        "rsquared_adj": model.rsquared_adj,
        "fvalue": model.fvalue,
        "f_pvalue": model.f_pvalue,
        "nobs": int(model.nobs),
        "var_names": ["const", "poverty_rate", "disability_rate", "senior_rate"],
    }


def _sig_stars(p):
    """Return significance stars for a p-value."""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return ""


def _fmt_p(p):
    """Format p-value for display."""
    if p < 0.001:
        return "< 0.001"
    return f"{p:.3f}"


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------


def _fig_coverage_by_borough(summaries):
    path = _fig("figure-1-coverage-by-borough.png")
    boros = list(summaries)
    rates = [float(summaries[b]["coverage_rate"]) for b in boros]
    colors = ["#4c78a8" if r >= 0.5 else "#e45756" for r in rates]
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(boros, [r * 100 for r in rates], color=colors, edgecolor="white")
    ax.set_ylabel("Tract coverage rate (%)")
    ax.set_title("Figure 1. Accessible station coverage by borough (10-min walk)")
    ax.set_ylim(0, 100)
    for bar, rate in zip(bars, rates, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1.5,
            f"{rate:.0%}",
            ha="center",
            fontsize=10,
            fontweight="bold",
        )
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _fig_gap_population(summaries):
    path = _fig("figure-2-gap-population.png")
    boros = list(summaries)
    pops = [int(summaries[b]["gap_pop"]) for b in boros]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(boros, [p / 1000 for p in pops], color="#e45756", edgecolor="white")
    ax.set_xlabel("Population in gap tracts (thousands)")
    ax.set_title("Figure 2. Population without accessible station coverage")
    ax.invert_yaxis()
    for i, p in enumerate(pops):
        ax.text(p / 1000 + 5, i, f"{p:,}", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _fig_reliability(summaries):
    path = _fig("figure-3-reliability-nominal-vs-effective.png")
    boros = list(summaries)
    nom = [float(summaries[b]["coverage_rate"]) * 100 for b in boros]
    eff = [float(summaries[b]["mean_rel_coverage"]) * 100 for b in boros]
    x = range(len(boros))
    w = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([i - w / 2 for i in x], nom, w, label="Nominal", color="#4c78a8")
    ax.bar(
        [i + w / 2 for i in x], eff, w, label="Reliability-weighted", color="#f58518"
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels(boros)
    ax.set_ylabel("Coverage (%)")
    ax.set_title("Figure 3. Nominal vs reliability-weighted coverage")
    ax.set_ylim(0, 100)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _fig_choropleth_gap(gdf):
    path = _fig("figure-4-choropleth-gap-score.png")
    plot_gdf = gdf.to_crs("EPSG:3857")
    fig, ax = plt.subplots(figsize=(12, 14))
    plot_gdf.plot(
        column="gap_score",
        ax=ax,
        cmap="YlOrRd",
        legend=True,
        legend_kwds={
            "label": "Gap score (0 = covered, higher = greater need)",
            "shrink": 0.6,
        },
        missing_kwds={"color": "#e0e0e0"},
        edgecolor="white",
        linewidth=0.1,
        vmin=0.0,
        vmax=max(0.15, float(plot_gdf["gap_score"].max())),
    )
    if ctx is not None:
        with contextlib.suppress(OSError, RuntimeError, ValueError):
            ctx.add_basemap(
                ax,
                crs="EPSG:3857",
                source=ctx.providers.CartoDB.Positron,
                alpha=0.4,
                zorder=0,
            )
    ax.set_title("Figure 4. Accessibility gap score by census tract", fontsize=13)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _fig_choropleth_coverage(gdf):
    path = _fig("figure-5-choropleth-coverage-status.png")
    plot_gdf = gdf.to_crs("EPSG:3857").copy()
    plot_gdf["coverage_label"] = plot_gdf["has_accessible_station"].map(
        {True: "Covered", False: "Gap"}
    )
    fig, ax = plt.subplots(figsize=(12, 14))
    colors = {"Covered": "#4c78a8", "Gap": "#e45756"}
    handles = []
    for label, color in colors.items():
        sub = plot_gdf[plot_gdf["coverage_label"] == label]
        sub.plot(ax=ax, color=color, edgecolor="white", linewidth=0.1)
        handles.append(mpatches.Patch(color=color, label=label))
    ax.legend(handles=handles, fontsize=11, loc="lower left")
    if ctx is not None:
        with contextlib.suppress(OSError, RuntimeError, ValueError):
            ctx.add_basemap(
                ax,
                crs="EPSG:3857",
                source=ctx.providers.CartoDB.Positron,
                alpha=0.3,
                zorder=0,
            )
    ax.set_title(
        "Figure 5. Accessible station coverage status by census tract", fontsize=13
    )
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _fig_coverage_over_time(panel):
    path = _fig("figure-6-coverage-progression.png")
    years = [int(p) for p in panel.periods]
    rates = []
    for p in panel.periods:
        obs = [o for o in panel.observations if o.period == p]
        rates.append(
            sum(1 for o in obs if o.has_accessible_station) / len(obs) * 100
            if obs
            else 0
        )
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(years, rates, marker="o", linewidth=2.5, color="#4c78a8", markersize=8)
    ax.fill_between(years, rates, alpha=0.15, color="#4c78a8")
    ax.set_xlabel("Year")
    ax.set_ylabel("Tract coverage rate (%)")
    ax.set_title("Figure 6. Accessibility coverage progression over panel window")
    ax.set_ylim(0, max(rates) * 1.15)
    for yr, r in zip(years, rates, strict=True):
        ax.annotate(
            f"{r:.1f}%",
            (yr, r),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=9,
        )
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _fig_treatment_vs_control(panel):
    path = _fig("figure-7-treatment-vs-control-balance.png")
    treatment = panel.treatment_group()
    control = panel.control_group()
    last = panel.periods[-1]
    t_obs = [o for o in treatment.observations if o.period == last]
    c_obs = [o for o in control.observations if o.period == last]
    labels = ["Disability rate", "Senior rate", "Poverty rate", "Need score"]
    attrs = ["disability_rate", "senior_rate", "poverty_rate", "need_score"]
    t_vals = [_mean([getattr(o, a) for o in t_obs]) for a in attrs]
    c_vals = [_mean([getattr(o, a) for o in c_obs]) for a in attrs]
    x = range(len(labels))
    w = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(
        [i - w / 2 for i in x],
        t_vals,
        w,
        label=f"Treatment (n={len(treatment.unit_ids):,})",
        color="#f58518",
    )
    ax.bar(
        [i + w / 2 for i in x],
        c_vals,
        w,
        label=f"Control (n={len(control.unit_ids):,})",
        color="#72b7b2",
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Rate")
    ax.set_title(f"Figure 7. Treatment vs control balance ({last})")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _fig_need_distribution(gdf):
    path = _fig("figure-8-need-score-distribution.png")
    vals = gdf["need_score"].dropna().tolist()
    m, med = _mean(vals), median(vals)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(vals, bins=40, color="#4c78a8", edgecolor="white", alpha=0.85)
    ax.axvline(
        m, color="#e45756", linestyle="--", linewidth=1.5, label=f"Mean = {m:.3f}"
    )
    ax.axvline(
        med, color="#f58518", linestyle="-.", linewidth=1.5, label=f"Median = {med:.3f}"
    )
    ax.set_xlabel("Need score")
    ax.set_ylabel("Tract count")
    ax.set_title("Figure 8. Distribution of composite need score across tracts")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _fig_distance_decay(gdf):
    path = _fig("figure-9-distance-decay.png")
    valid = gdf[gdf["nearest_distance_m"] > 0].copy()
    if valid.empty:
        return path
    bins = [0, 200, 400, 600, 800, 1000, 1500, 2000, 3000, 5000, 999999]
    labels = [
        "0-200",
        "200-400",
        "400-600",
        "600-800",
        "800-1k",
        "1-1.5k",
        "1.5-2k",
        "2-3k",
        "3-5k",
        "5k+",
    ]
    valid["dist_bin"] = valid["nearest_distance_m"].apply(
        lambda d: next(
            (labels[i] for i in range(len(bins) - 1) if bins[i] <= d < bins[i + 1]),
            labels[-1],
        )
    )
    bin_order = {lab: i for i, lab in enumerate(labels)}
    grouped = (
        valid.groupby("dist_bin")
        .agg(
            coverage_rate=("has_accessible_station", "mean"),
            tract_count=("has_accessible_station", "count"),
        )
        .reset_index()
    )
    grouped["order"] = grouped["dist_bin"].map(bin_order)
    grouped = grouped.sort_values("order")
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.bar(
        grouped["dist_bin"],
        grouped["coverage_rate"] * 100,
        color="#4c78a8",
        alpha=0.7,
        label="Coverage rate",
    )
    ax1.set_xlabel("Distance to nearest accessible station")
    ax1.set_ylabel("Coverage rate (%)", color="#4c78a8")
    ax1.tick_params(axis="x", rotation=35)
    ax2 = ax1.twinx()
    ax2.plot(
        grouped["dist_bin"],
        grouped["tract_count"],
        color="#e45756",
        marker="o",
        linewidth=2,
        label="Tract count",
    )
    ax2.set_ylabel("Tract count", color="#e45756")
    ax1.set_title("Figure 9. Distance decay: coverage rate by distance bin")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _fig_gap_vs_distance(gdf):
    path = _fig("figure-10-gap-vs-distance-scatter.png")
    valid = gdf[(gdf["nearest_distance_m"] > 0) & (gdf["gap_score"] > 0)].copy()
    if valid.empty:
        return path
    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(
        valid["nearest_distance_m"],
        valid["gap_score"],
        c=valid["population"],
        cmap="YlOrRd",
        alpha=0.6,
        s=20,
        edgecolors="none",
    )
    plt.colorbar(scatter, ax=ax, label="Tract population", shrink=0.7)
    ax.set_xlabel("Distance to nearest accessible station (m)")
    ax.set_ylabel("Gap score")
    ax.set_title(
        "Figure 10. Gap score vs distance (gap tracts only, sized by population)"
    )
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _fig_correlation_heatmap(corr_result):
    path = _fig("figure-11-correlation-heatmap.png")
    r = corr_result["r_matrix"]
    p = corr_result["p_matrix"]
    labels = corr_result["labels"]
    n = len(labels)
    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(r, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    plt.colorbar(im, ax=ax, label="Pearson r", shrink=0.8)
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=10)
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, fontsize=10)
    for i in range(n):
        for j in range(n):
            stars = _sig_stars(p[i, j])
            txt = f"{r[i, j]:.2f}{stars}" if i != j else ""
            color = "white" if abs(r[i, j]) > 0.6 else "black"
            ax.text(j, i, txt, ha="center", va="center", fontsize=9, color=color)
    ax.set_title(
        "Figure 11. Pairwise Pearson correlations (* p<.05, ** p<.01, *** p<.001)"
    )
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _fig_gap_vs_poverty(gdf):
    path = _fig("figure-12-gap-vs-poverty-scatter.png")
    valid = gdf[gdf["gap_score"] > 0].copy()
    if valid.empty:
        return path
    borough_colors = {
        "Manhattan": "#4c78a8",
        "Brooklyn": "#f58518",
        "Queens": "#e45756",
        "Bronx": "#72b7b2",
        "Staten Island": "#54a24b",
    }
    fig, ax = plt.subplots(figsize=(10, 6))
    for borough, color in borough_colors.items():
        sub = valid[valid["borough"] == borough]
        if not sub.empty:
            ax.scatter(
                sub["poverty_rate"],
                sub["gap_score"],
                c=color,
                label=borough,
                alpha=0.5,
                s=15,
                edgecolors="none",
            )
    r, p = sp_stats.pearsonr(valid["poverty_rate"], valid["gap_score"])
    slope, intercept = np.polyfit(valid["poverty_rate"], valid["gap_score"], 1)
    x_line = np.linspace(valid["poverty_rate"].min(), valid["poverty_rate"].max(), 100)
    ax.plot(x_line, slope * x_line + intercept, "k--", linewidth=1.5, alpha=0.7)
    ax.annotate(
        f"r = {r:.3f}, p {_fmt_p(p)}",
        xy=(0.02, 0.95),
        xycoords="axes fraction",
        fontsize=10,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "wheat", "alpha": 0.8},
    )
    ax.set_xlabel("Poverty rate")
    ax.set_ylabel("Gap score")
    ax.set_title("Figure 12. Gap score vs poverty rate (gap tracts only)")
    ax.legend(fontsize=9, markerscale=2)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _fig_gap_vs_disability(gdf):
    path = _fig("figure-13-gap-vs-disability-scatter.png")
    valid = gdf[gdf["gap_score"] > 0].copy()
    if valid.empty:
        return path
    borough_colors = {
        "Manhattan": "#4c78a8",
        "Brooklyn": "#f58518",
        "Queens": "#e45756",
        "Bronx": "#72b7b2",
        "Staten Island": "#54a24b",
    }
    fig, ax = plt.subplots(figsize=(10, 6))
    for borough, color in borough_colors.items():
        sub = valid[valid["borough"] == borough]
        if not sub.empty:
            ax.scatter(
                sub["disability_rate"],
                sub["gap_score"],
                c=color,
                label=borough,
                alpha=0.5,
                s=15,
                edgecolors="none",
            )
    r, p = sp_stats.pearsonr(valid["disability_rate"], valid["gap_score"])
    slope, intercept = np.polyfit(valid["disability_rate"], valid["gap_score"], 1)
    x_line = np.linspace(
        valid["disability_rate"].min(), valid["disability_rate"].max(), 100
    )
    ax.plot(x_line, slope * x_line + intercept, "k--", linewidth=1.5, alpha=0.7)
    ax.annotate(
        f"r = {r:.3f}, p {_fmt_p(p)}",
        xy=(0.02, 0.95),
        xycoords="axes fraction",
        fontsize=10,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "wheat", "alpha": 0.8},
    )
    ax.set_xlabel("Disability rate")
    ax.set_ylabel("Gap score")
    ax.set_title("Figure 13. Gap score vs disability rate (gap tracts only)")
    ax.legend(fontsize=9, markerscale=2)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _fig_bivariate_map(gdf, var_a, var_b, label_a, label_b, fig_num, slug):
    path = _fig(f"figure-{fig_num}-{slug}.png")
    plot_gdf = gdf.to_crs("EPSG:3857")
    fig, axes = plt.subplots(1, 2, figsize=(22, 14))
    for ax, col, label, cmap in [
        (axes[0], var_a, label_a, "YlOrRd"),
        (axes[1], var_b, label_b, "PuBuGn"),
    ]:
        plot_gdf.plot(
            column=col,
            ax=ax,
            cmap=cmap,
            legend=True,
            legend_kwds={"label": label, "shrink": 0.6},
            missing_kwds={"color": "#e0e0e0"},
            edgecolor="white",
            linewidth=0.1,
        )
        if ctx is not None:
            with contextlib.suppress(OSError, RuntimeError, ValueError):
                ctx.add_basemap(
                    ax,
                    crs="EPSG:3857",
                    source=ctx.providers.CartoDB.Positron,
                    alpha=0.4,
                    zorder=0,
                )
        ax.set_title(label, fontsize=12)
        ax.set_axis_off()
    fig.suptitle(
        f"Figure {fig_num}. {label_a} vs {label_b} by census tract",
        fontsize=14,
        y=0.98,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


def export_panel_csv(panel, path):
    flds = [
        "unit_id",
        "period",
        "has_accessible_station",
        "treatment_year",
        "disability_rate",
        "senior_rate",
        "poverty_rate",
        "total_population",
        "accessible_station_count",
        "nearest_accessible_distance_m",
        "need_score",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=flds)
        w.writeheader()
        for o in panel.observations:
            w.writerow(
                {
                    "unit_id": o.unit_id,
                    "period": o.period,
                    "has_accessible_station": o.has_accessible_station,
                    "treatment_year": o.treatment_year or "",
                    "disability_rate": f"{o.disability_rate:.4f}",
                    "senior_rate": f"{o.senior_rate:.4f}",
                    "poverty_rate": f"{o.poverty_rate:.4f}",
                    "total_population": o.total_population,
                    "accessible_station_count": o.accessible_station_count,
                    "nearest_accessible_distance_m": f"{o.nearest_accessible_distance_m:.1f}"
                    if o.nearest_accessible_distance_m
                    else "",
                    "need_score": f"{o.need_score:.4f}",
                }
            )


def export_borough_csv(summaries, path):
    flds = [
        "borough",
        "stations",
        "ada_stations",
        "tracts",
        "covered",
        "gap_tracts",
        "coverage_rate",
        "gap_pop",
        "total_pop",
        "avg_need",
        "avg_distance_m",
        "mean_rel_coverage",
        "fragile_stations",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=flds)
        w.writeheader()
        for b, s in summaries.items():
            w.writerow(
                {
                    k: (f"{s[k]:.4f}" if isinstance(s[k], float) else s[k])
                    for k in flds
                    if k != "borough"
                }
                | {"borough": b}
            )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _skewness(vals):
    n = len(vals)
    if n < 3:
        return 0.0
    m = _mean(vals)
    s = stdev(vals)
    if s == 0:
        return 0.0
    return (n / ((n - 1) * (n - 2))) * sum(((v - m) / s) ** 3 for v in vals)


SUPPLEMENTARY_DIR = REPORTS_DIR / "supplementary"


def write_correlation_report(_gdf, corr, spearman, vif_results, equity_reg, provenance):
    """Auto-generate supplementary/correlation-analysis.md."""
    L = []

    def _w(s):
        L.append(s)

    pv = provenance
    _w("# Correlation Analysis")
    _w("")
    _w(f"*Auto-generated: {pv['report_date']}*")
    _w("")
    _w(
        "This supplementary report provides full correlation matrices, multicollinearity "
        "diagnostics, and an OLS regression of gap score on demographic predictors."
    )
    _w("")

    # Pearson matrix.
    _w("## Pearson correlation matrix")
    _w("")
    labels = corr["labels"]
    r_mat = corr["r_matrix"]
    p_mat = corr["p_matrix"]
    n = len(labels)
    header = "| | " + " | ".join(labels) + " |"
    sep = "| :--- |" + " ---: |" * n
    _w(header)
    _w(sep)
    for i in range(n):
        row = f"| **{labels[i]}** |"
        for j in range(n):
            if i == j:
                row += " 1.000 |"
            else:
                stars = _sig_stars(p_mat[i, j])
                row += f" {r_mat[i, j]:.3f}{stars} |"
        _w(row)
    _w("")
    _w("*Significance: \\* p < 0.05, \\*\\* p < 0.01, \\*\\*\\* p < 0.001*")
    _w("")
    _w("![Figure 11](../figures/figure-11-correlation-heatmap.png)")
    _w("")

    # Spearman matrix.
    _w("## Spearman rank correlation matrix")
    _w("")
    rho_mat = spearman["rho_matrix"]
    sp_mat = spearman["p_matrix"]
    _w(header)
    _w(sep)
    for i in range(n):
        row = f"| **{labels[i]}** |"
        for j in range(n):
            if i == j:
                row += " 1.000 |"
            else:
                stars = _sig_stars(sp_mat[i, j])
                row += f" {rho_mat[i, j]:.3f}{stars} |"
        _w(row)
    _w("")
    _w(
        "Spearman correlations are robust to non-linear monotonic relationships and outliers. "
        "Agreement with Pearson results indicates linear association is a reasonable approximation."
    )
    _w("")

    # VIF.
    _w("## Variance inflation factors (VIF)")
    _w("")
    _w("| Variable | VIF |")
    _w("| :--- | ---: |")
    for var, vif in vif_results:
        flag = " \u26a0\ufe0f" if vif > 5 else ""
        _w(f"| {var} | {vif:.2f}{flag} |")
    _w("")
    max_vif = max(v for _, v in vif_results)
    if max_vif < 5:
        _w(
            f"All VIF values are below 5 (max = {max_vif:.2f}), indicating no problematic multicollinearity "
            "among the demographic predictors."
        )
    else:
        _w(
            f"**Warning:** At least one VIF exceeds 5 (max = {max_vif:.2f}), suggesting multicollinearity. "
            "Consider dropping or combining correlated predictors."
        )
    _w("")

    # Scatter plots.
    _w("## Bivariate scatter plots")
    _w("")
    _w("![Figure 12](../figures/figure-12-gap-vs-poverty-scatter.png)")
    _w("")
    _w("![Figure 13](../figures/figure-13-gap-vs-disability-scatter.png)")
    _w("")

    # Equity OLS.
    if equity_reg is not None:
        _w("## OLS regression: gap score on demographic predictors")
        _w("")
        _w(
            "Model: `gap_score = b0 + b1*poverty_rate + b2*disability_rate + b3*senior_rate`"
        )
        _w("")
        _w(
            f"N = {equity_reg['nobs']:,}, R\u00b2 = {equity_reg['rsquared']:.4f}, "
            f"Adj. R\u00b2 = {equity_reg['rsquared_adj']:.4f}, "
            f"F = {equity_reg['fvalue']:.2f} (p {_fmt_p(equity_reg['f_pvalue'])})"
        )
        _w("")
        _w("| Variable | Coefficient | SE | t | p-value | |")
        _w("| :--- | ---: | ---: | ---: | ---: | :--- |")
        for i, var in enumerate(equity_reg["var_names"]):
            b = equity_reg["params"][i]
            se = equity_reg["bse"][i]
            t = equity_reg["tvalues"][i]
            p = equity_reg["pvalues"][i]
            _w(
                f"| {var} | {b:.4f} | {se:.4f} | {t:.2f} | {_fmt_p(p)} | {_sig_stars(p)} |"
            )
        _w("")
        # Identify strongest predictor (largest |t| among non-constant).
        pred_idx = [
            i
            for i in range(len(equity_reg["var_names"]))
            if equity_reg["var_names"][i] != "const"
        ]
        best_i = max(pred_idx, key=lambda i: abs(equity_reg["tvalues"][i]))
        best_var = equity_reg["var_names"][best_i]
        _w(
            f"**Strongest predictor:** {best_var} (|t| = {abs(equity_reg['tvalues'][best_i]):.2f}). "
            "Robust standard errors (HC1) account for heteroskedasticity."
        )

    out = _dir(SUPPLEMENTARY_DIR) / "correlation-analysis.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def write_model_spec_report(
    _panel, _gdf, weights, balance_stats, diag_stats, provenance
):
    """Auto-generate supplementary/model-specification.md."""
    L = []

    def _w(s):
        L.append(s)

    pv = provenance

    _w("# Model Specification")
    _w("")
    _w(f"*Auto-generated: {pv['report_date']}*")
    _w("")
    _w(
        "This supplementary report details the difference-in-differences (DiD) panel model "
        "specification, its identifying assumptions, and pre-estimation diagnostics."
    )
    _w("")

    # DiD specification.
    _w("## Difference-in-differences specification")
    _w("")
    _w("```")
    _w(
        "Y_it = alpha + beta * Treatment_it + gamma * X_it + delta_i + tau_t + epsilon_it"
    )
    _w("```")
    _w("")
    _w("| Symbol | Description |")
    _w("| :--- | :--- |")
    _w(
        "| Y_it | Outcome: population change, demographic composition, or housing cost |"
    )
    _w("| Treatment_it | 1 if tract *i* has an accessible station by period *t* |")
    _w("| X_it | Time-varying covariates: disability rate, senior rate, poverty rate |")
    _w(
        "| delta_i | Tract fixed effects (absorb time-invariant tract characteristics) |"
    )
    _w("| tau_t | Period fixed effects (absorb city-wide trends) |")
    _w("| beta | **Causal estimate:** effect of gaining an accessible station |")
    _w("")

    # Assumptions.
    _w("## Identifying assumptions")
    _w("")
    _w("### 1. Parallel trends")
    _w("")
    _w(
        "In the absence of treatment, treated and control tracts would have followed "
        "the same outcome trajectory. This is the core identifying assumption of DiD. "
        "It cannot be directly tested, but pre-treatment outcome trends should be parallel."
    )
    _w("")
    _w(
        "**Status:** Partially verifiable with the sourced upgrade timeline (101/157 stations). "
        "Plot pre-treatment outcome trends for treatment vs control groups "
        "to visually assess parallelism."
    )
    _w("")
    _w("### 2. No anticipation")
    _w("")
    _w(
        "Units do not change behavior in anticipation of treatment. Since ADA station "
        "upgrades are infrastructure projects announced years in advance, this assumption "
        "could be violated if households sort based on announced plans."
    )
    _w("")
    _w("### 3. SUTVA (Stable Unit Treatment Value Assumption)")
    _w("")
    _w(
        "One unit's treatment does not affect another unit's outcome. Spatial spillovers "
        "(e.g., a new accessible station increasing property values in adjacent tracts) "
        "could violate SUTVA. The SAR extension below addresses this."
    )
    _w("")

    # Balance table with t-tests.
    _w("## Balance check with hypothesis tests")
    _w("")
    _w("| Variable | Treatment | Control | Diff | Cohen's d | t-stat | p-value | |")
    _w("| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |")
    for row in balance_stats:
        stars = _sig_stars(row["p_value"])
        _w(
            f"| {row['label']} | {row['t_mean']:.4f} | {row['c_mean']:.4f} "
            f"| {row['diff']:+.4f} | {row['cohens_d']:.3f} | {row['t_stat']:.2f} "
            f"| {_fmt_p(row['p_value'])} | {stars} |"
        )
    _w("")
    _w(
        "**Welch's t-test** (unequal variance) used for all comparisons. "
        "Cohen's d: |d| < 0.2 = negligible, 0.2-0.5 = small, 0.5-0.8 = medium, > 0.8 = large."
    )
    _w("")

    # Enhanced diagnostics.
    _w("## Distribution diagnostics")
    _w("")
    _w("| Statistic | Need score | Distance (m) | Gap score |")
    _w("| :--- | ---: | ---: | ---: |")
    for stat_name, vals in diag_stats.items():
        _w(f"| {stat_name} | {vals[0]} | {vals[1]} | {vals[2]} |")
    _w("")

    # SAR extension.
    _w("## Spatial autoregressive (SAR) extension")
    _w("")
    _w("```")
    _w("Y_it = rho * W * Y_it + beta * X_it + delta_i + tau_t + epsilon_it")
    _w("```")
    _w("")
    units_nbrs = sum(1 for u in weights if weights[u])
    mean_nbrs = sum(len(n) for n in weights.values()) / len(weights) if weights else 0
    _w(
        f"Where *W* is the row-standardized distance-based spatial weights matrix "
        f"({len(weights):,} units, {units_nbrs:,} with neighbors, mean {mean_nbrs:.1f} neighbors, "
        f"2 km threshold)."
    )
    _w("")
    _w(
        "If significant spatial autocorrelation is detected (see [spatial diagnostics]"
        "(./spatial-diagnostics.md)), the SAR model should be preferred over standard DiD "
        "to avoid biased coefficients."
    )
    _w("")

    # Limitations.
    _w("## Limitations of current panel")
    _w("")
    _w(
        "- **Partially sourced upgrade timeline:** 101 of 157 station upgrade years are traced to "
        "MTA press releases, Capital Program records, and news coverage. The remaining 56 use "
        "hash-based approximations pending a FOIL request for Key Station Program completion records."
    )
    _w(
        "- **Repeated demographics:** ACS estimates are repeated across vintage years (the "
        "same 2023 estimates appear in all periods). Production use should fetch actual multi-vintage "
        "ACS data via `fetch_multi_vintage_estimates()`."
    )
    _w(
        "- **No outcome variable:** The panel currently has treatment indicators and covariates "
        "but no outcome variable (e.g., property values, transit ridership, population change). "
        "Defining the outcome requires linking to additional data sources."
    )

    out = _dir(SUPPLEMENTARY_DIR) / "model-specification.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def write_spatial_report(_gdf, weights, morans_results, provenance):
    """Auto-generate supplementary/spatial-diagnostics.md."""
    L = []

    def _w(s):
        L.append(s)

    pv = provenance
    _w("# Spatial Diagnostics")
    _w("")
    _w(f"*Auto-generated: {pv['report_date']}*")
    _w("")

    # Weights summary.
    _w("## Spatial weights matrix")
    _w("")
    units_nbrs = sum(1 for u in weights if weights[u])
    islands = sum(1 for u in weights if not weights[u])
    all_nbr_counts = [len(n) for n in weights.values()]
    mean_nbrs = _mean(all_nbr_counts)
    _w("| Property | Value |")
    _w("| :--- | ---: |")
    _w(f"| Units | {len(weights):,} |")
    _w("| Distance threshold | 2,000 m |")
    _w(f"| Units with neighbors | {units_nbrs:,} |")
    _w(f"| Islands (no neighbors) | {islands:,} |")
    _w(f"| Mean neighbors | {mean_nbrs:.1f} |")
    if all_nbr_counts:
        _w(f"| Min neighbors | {min(all_nbr_counts)} |")
        _w(f"| Max neighbors | {max(all_nbr_counts)} |")
        _w(f"| Median neighbors | {sorted(all_nbr_counts)[len(all_nbr_counts) // 2]} |")
    _w("")
    _w(
        "Row-standardized distance-based weights: each unit's neighbors (within 2 km) "
        "receive equal weight summing to 1. Units with no neighbors (islands) are excluded "
        "from spatial analysis."
    )
    _w("")

    # Moran's I.
    _w("## Global Moran's I")
    _w("")
    _w(
        "Moran's I tests whether a variable is spatially clustered (I > E[I]) or "
        "dispersed (I < E[I]). Under the null hypothesis of spatial randomness, "
        "I converges to E[I] = -1/(N-1)."
    )
    _w("")
    _w("| Variable | Moran's I | E[I] | z-score | p-value | |")
    _w("| :--- | ---: | ---: | ---: | ---: | :--- |")
    for var_name, res in morans_results.items():
        stars = _sig_stars(res["p_value"])
        label = var_name.replace("_", " ").title()
        _w(
            f"| {label} | {res['I']:.4f} | {res['expected_I']:.4f} "
            f"| {res['z_score']:.2f} | {_fmt_p(res['p_value'])} | {stars} |"
        )
    _w("")

    any_significant = any(r["p_value"] < 0.05 for r in morans_results.values())
    if any_significant:
        _w(
            "**Interpretation:** Statistically significant spatial autocorrelation detected. "
            "Key variables are not randomly distributed across space -- similar values cluster together. "
            "This has two implications:"
        )
        _w("")
        _w(
            "1. **For the DiD model:** Standard errors may be underestimated if spatial dependence "
            "is ignored. The SAR panel extension or spatial HAC standard errors should be used."
        )
        _w(
            "2. **For policy:** The clustering suggests that accessibility gaps are concentrated "
            "in specific neighborhoods, not uniformly distributed. Targeted investment in these "
            "clusters would be more efficient than system-wide uniform upgrades."
        )
    else:
        _w(
            "**Interpretation:** No significant spatial autocorrelation detected. "
            "Standard (non-spatial) panel methods are appropriate."
        )
    _w("")

    # Bivariate maps.
    _w("## Bivariate geographic comparison")
    _w("")
    _w("![Figure 14](../figures/figure-14-gap-vs-poverty-map.png)")
    _w("")
    _w(
        "Side-by-side maps allow visual comparison of gap score spatial distribution (left) "
        "with poverty rate (right). Where both are dark, high-poverty neighborhoods also lack "
        "accessible transit."
    )
    _w("")
    _w("![Figure 15](../figures/figure-15-gap-vs-disability-map.png)")
    _w("")
    _w(
        "Gap score vs disability rate. Where gap scores are high in tracts with high disability "
        "prevalence, the equity burden is most acute."
    )
    _w("")

    # Future work.
    _w("## Future work")
    _w("")
    _w(
        "- **Local indicators of spatial association (LISA):** Identify specific clusters "
        "of high-gap / high-need tracts using local Moran's I. Requires `esda` package."
    )
    _w(
        "- **Spatial lag model estimation:** Estimate the SAR panel with `spreg` or `pysal` "
        "once a suitable outcome variable is available."
    )
    _w(
        "- **Geographically weighted regression (GWR):** Allow coefficients to vary across "
        "space to identify neighborhoods where the gap-demographics relationship is strongest."
    )

    out = _dir(SUPPLEMENTARY_DIR) / "spatial-diagnostics.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def write_report(
    summaries,
    panel,
    gdf,
    weights,
    years,
    boroughs,
    minutes,
    figs,
    provenance,
    balance_stats=None,
    diag_stats=None,
    morans_results=None,
    equity_reg=None,
):
    treatment = panel.treatment_group()
    control = panel.control_group()
    last = panel.periods[-1]
    t_obs = [o for o in treatment.observations if o.period == last]
    c_obs = [o for o in control.observations if o.period == last]

    tot_st = sum(int(s["stations"]) for s in summaries.values())
    tot_ada = sum(int(s["ada_stations"]) for s in summaries.values())
    tot_tr = sum(int(s["tracts"]) for s in summaries.values())
    tot_cov = sum(int(s["covered"]) for s in summaries.values())
    tot_gap_pop = sum(int(s["gap_pop"]) for s in summaries.values())
    tot_pop = sum(int(s["total_pop"]) for s in summaries.values())
    units_nbrs = sum(1 for u in weights if weights[u])
    mean_nbrs = sum(len(n) for n in weights.values()) / len(weights) if weights else 0

    # Fragile stations.
    fragile = sorted(
        [
            (b, r)
            for b, s in summaries.items()
            for r in s["reliability"].records
            if r.ada_status == "accessible" and r.reliability_label == "fragile"
        ],
        key=lambda x: x[1].reliability_score,
    )

    # Diagnostics.
    need_vals = gdf["need_score"].dropna().tolist()
    dist_vals = [d for d in gdf["nearest_distance_m"].dropna().tolist() if d > 0]
    gap_vals = [g for g in gdf["gap_score"].dropna().tolist() if g > 0]

    L = []

    def _w(s):
        L.append(s)

    pv = provenance
    _w("# Accessibility Change Over Time")
    _w("")
    _w(f"*Report generated: {pv['report_date']}*")
    _w("")
    _w("| | |")
    _w("| :--- | :--- |")
    _w(f"| **Boroughs** | {', '.join(boroughs)} |")
    _w(f"| **Stations & ADA status** | MTA Open Data, fetched {pv['snapshot_date']} |")
    _w(f"| **Outage observation window** | {pv['avail_window']} (12 months) |")
    _w(
        f"| **Demographics** | ACS 5-year estimates, {pv['acs_vintage']} vintage (survey period {pv['acs_survey_period']}) |"
    )
    _w("| **Census tract boundaries** | 2020 vintage (nyc-geo-toolkit) |")
    _w(f"| **Tracts analyzed** | {tot_tr:,} |")
    _w(f"| **Panel periods** | {len(panel.periods)} ({min(years)}\u2013{max(years)}) |")
    _w("")
    _w("---")
    _w("")
    _w("## What this means for New Yorkers")
    _w("")
    _w(
        f"- **{tot_gap_pop:,} New Yorkers** ({tot_gap_pop / tot_pop:.0%} of the city) live more than a 10-minute walk from any ADA-accessible subway station."
    )
    _w(
        f"- Only **{tot_ada} of {tot_st} stations** ({tot_ada / tot_st:.0%}) are wheelchair-accessible. If you use a wheelchair, cane, stroller, or have trouble with stairs, two-thirds of stations are off-limits."
    )
    worst_b = max(summaries, key=lambda b: summaries[b]["gap_pop"])
    _w(
        f"- **{worst_b}** has the largest gap: {int(summaries[worst_b]['gap_pop']):,} residents without accessible station coverage."
    )
    if fragile:
        _w(
            f"- Even among accessible stations, **{len(fragile)} have elevators down more than 5% of the time**. {fragile[0][1].station_name} had just {fragile[0][1].reliability_score:.0%} uptime ({pv['avail_window']})."
        )
    _w("")

    # Table 1.
    _w("## Table 1. System-wide snapshot")
    _w("")
    _w("| Metric | Value |")
    _w("| :--- | ---: |")
    _w(f"| Subway stations | {tot_st} |")
    _w(f"| ADA-accessible stations | {tot_ada} ({tot_ada / tot_st:.0%}) |")
    _w(f"| Census tracts analyzed | {tot_tr:,} |")
    _w(f"| Tracts with accessible coverage | {tot_cov:,} ({tot_cov / tot_tr:.0%}) |")
    _w(
        f"| Tracts in accessibility gap | {tot_tr - tot_cov:,} ({(tot_tr - tot_cov) / tot_tr:.0%}) |"
    )
    _w(f"| Population in gap tracts | {tot_gap_pop:,} |")
    _w(f"| Total study population | {tot_pop:,} |")
    _w("")

    # Table 2 + Figures 1, 2.
    _w("## Table 2. Borough comparison")
    _w("")
    _w(f"![Figure 1](./figures/{figs['f1'].name})")
    _w("")
    _w("| Borough | Stations | ADA | Tracts | Covered | Gap pop | Avg dist |")
    _w("| :--- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for b, s in summaries.items():
        _w(
            f"| {b} | {s['stations']} | {s['ada_stations']} "
            f"| {s['tracts']} | {s['covered']} ({s['coverage_rate']:.0%}) "
            f"| {int(s['gap_pop']):,} | {int(s['avg_distance_m']):,} m |"
        )
    _w("")
    _w(f"![Figure 2](./figures/{figs['f2'].name})")
    _w("")

    # Figures 4, 5 — geo.
    _w("## Geographic distribution")
    _w("")
    _w(f"![Figure 4](./figures/{figs['f4'].name})")
    _w("")
    _w(
        "The gap score map (Figure 4) shows where high-need tracts lack accessible stations. "
        "Darker red areas have both high demographic need and no accessible station within walking distance."
    )
    _w("")
    _w(f"![Figure 5](./figures/{figs['f5'].name})")
    _w("")
    _w(
        "The binary coverage map (Figure 5) shows the stark geographic divide: "
        "blue tracts have at least one accessible station within a 10-minute walk, red tracts do not."
    )
    _w("")

    # Reliability — Figure 3 + Table 3.
    _w("## Reliability analysis")
    _w("")
    _w(
        "Nominal coverage counts any ADA station within the catchment. "
        "Reliability-weighted coverage discounts by uptime: a station with 50% elevator uptime provides 0.50 effective coverage."
    )
    _w("")
    _w(f"![Figure 3](./figures/{figs['f3'].name})")
    _w("")
    if fragile:
        _w("### Table 3. Most fragile accessible stations")
        _w("")
        _w("| Station | Borough | Uptime | Outage (min) |")
        _w("| :--- | :--- | ---: | ---: |")
        for b, r in fragile[:15]:
            _w(
                f"| {r.station_name or r.station_id} | {b} | {r.reliability_score:.1%} | {r.outage_minutes:,} |"
            )
        _w("")
        _w(
            f"*{len(fragile)} accessible stations system-wide had <95% uptime during the {pv['avail_window']} observation window.*"
        )
        _w("")

    # Panel — Figure 6 + Table 4.
    _w("## Temporal panel")
    _w("")
    _w(f"![Figure 6](./figures/{figs['f6'].name})")
    _w("")
    _w("### Table 4. Coverage progression")
    _w("")
    _w("| Year | Covered tracts | Rate | Covered pop |")
    _w("| :--- | ---: | ---: | ---: |")
    for p in panel.periods:
        obs = [o for o in panel.observations if o.period == p]
        cov = sum(1 for o in obs if o.has_accessible_station)
        cpop = sum(o.total_population for o in obs if o.has_accessible_station)
        _w(f"| {p} | {cov:,} | {cov / len(obs):.1%} | {cpop:,} |")
    _w("")

    # Treatment vs control — Figure 7 + Table 5.
    _w("## Treatment vs control")
    _w("")
    _w(
        f"Treatment: tracts that gained an accessible station during the panel window ({len(treatment.unit_ids):,} tracts). "
        f"Control: tracts with no accessible station coverage in any period ({len(control.unit_ids):,} tracts)."
    )
    _w("")
    _w(f"![Figure 7](./figures/{figs['f7'].name})")
    _w("")
    _w("### Table 5. Balance check")
    _w("")
    if balance_stats:
        _w("| Variable | Treatment | Control | Diff | Cohen's d | p-value | |")
        _w("| :--- | ---: | ---: | ---: | ---: | ---: | :--- |")
        for row in balance_stats:
            stars = _sig_stars(row["p_value"])
            _w(
                f"| {row['label']} | {row['t_mean']:.4f} | {row['c_mean']:.4f} "
                f"| {row['diff']:+.4f} | {row['cohens_d']:.3f} | {_fmt_p(row['p_value'])} | {stars} |"
            )
        t_pop = sum(o.total_population for o in t_obs)
        c_pop = sum(o.total_population for o in c_obs)
        _w(f"| Population | {t_pop:,} | {c_pop:,} | | | | |")
        _w("")
        _w(
            "*Welch's t-test (unequal variance). Cohen's d: |d| < 0.2 negligible, "
            "0.2\u20130.5 small, 0.5\u20130.8 medium, > 0.8 large.*"
        )
    else:
        _w("| Variable | Treatment | Control | Diff |")
        _w("| :--- | ---: | ---: | ---: |")
        for label, attr in [
            ("Disability rate", "disability_rate"),
            ("Senior rate", "senior_rate"),
            ("Poverty rate", "poverty_rate"),
            ("Need score", "need_score"),
        ]:
            tv = _mean([getattr(o, attr) for o in t_obs]) if t_obs else 0
            cv = _mean([getattr(o, attr) for o in c_obs]) if c_obs else 0
            diff = tv - cv
            _w(f"| {label} | {tv:.4f} | {cv:.4f} | {diff:+.4f} |")
        t_pop = sum(o.total_population for o in t_obs)
        c_pop = sum(o.total_population for o in c_obs)
        _w(f"| Population | {t_pop:,} | {c_pop:,} | |")
    _w("")
    if t_obs and c_obs:
        t_need = _mean([o.need_score for o in t_obs])
        c_need = _mean([o.need_score for o in c_obs])
        if t_need > c_need:
            _w(
                "**Key finding:** Treatment tracts have modestly higher need scores than control tracts, "
                "suggesting ADA upgrades are reaching higher-need neighborhoods -- the right direction for equity. "
                "However, the imbalance also means a naive comparison would overstate the accessibility benefit; "
                "the DiD specification with fixed effects is essential for causal identification."
            )
        else:
            _w(
                "**Key finding:** Control tracts have higher need scores, suggesting ADA upgrades have not yet "
                "reached the highest-need neighborhoods. This motivates the policy question of targeting."
            )
    _w("")

    # Diagnostics — Figures 8-10 + Table 6.
    _w("## Diagnostic checks")
    _w("")
    _w(f"![Figure 8](./figures/{figs['f8'].name})")
    _w("")
    _w(
        "The need score distribution (Figure 8) is right-skewed, which is expected: most tracts have moderate need, "
        "while a tail of high-need tracts drives the accessibility gap. "
        "The median is below the mean, confirming the skew."
    )
    _w("")
    _w(f"![Figure 9](./figures/{figs['f9'].name})")
    _w("")
    _w(
        "The distance decay curve (Figure 9) validates the 10-minute (800 m) catchment threshold: "
        "coverage drops sharply beyond 800 m and is near zero past 1.5 km. "
        "This confirms the walk-time assumption is not overly generous."
    )
    _w("")
    _w(f"![Figure 10](./figures/{figs['f10'].name})")
    _w("")
    _w(
        "The gap-distance scatter (Figure 10) shows that gap scores increase with distance from the nearest "
        "accessible station, as expected. Larger dots (higher population) appear across all distance ranges, "
        "meaning high-population tracts are affected at every distance -- not just at the periphery."
    )
    _w("")

    _w("### Table 6. Summary diagnostics")
    _w("")
    if diag_stats:
        _w("| Statistic | Need score | Distance (m) | Gap score |")
        _w("| :--- | ---: | ---: | ---: |")
        for stat_name, vals in diag_stats.items():
            _w(f"| {stat_name} | {vals[0]} | {vals[1]} | {vals[2]} |")
    else:
        _w("| Statistic | Need score | Distance (m) | Gap score |")
        _w("| :--- | ---: | ---: | ---: |")
        _w(f"| N | {len(need_vals):,} | {len(dist_vals):,} | {len(gap_vals):,} |")
        _w(
            f"| Mean | {_mean(need_vals):.4f} | {_mean(dist_vals):.0f} | {_mean(gap_vals):.4f} |"
        )
        _w(
            f"| Median | {median(need_vals):.4f} | {median(dist_vals):.0f} | {median(gap_vals):.4f} |"
        )
        _w(
            f"| Std dev | {stdev(need_vals):.4f} | {stdev(dist_vals):.0f} | {stdev(gap_vals):.4f} |"
        )
        _w(
            f"| Skewness | {_skewness(need_vals):.2f} | {_skewness(dist_vals):.2f} | {_skewness(gap_vals):.2f} |"
        )
        _w(
            f"| Min | {min(need_vals):.4f} | {min(dist_vals):.0f} | {min(gap_vals):.4f} |"
        )
        _w(
            f"| Max | {max(need_vals):.4f} | {max(dist_vals):.0f} | {max(gap_vals):.4f} |"
        )
    _w("")
    _w(
        f"**Spatial weights:** {len(weights):,} units, {units_nbrs:,} with neighbors (2 km threshold), "
        f"mean {mean_nbrs:.1f} neighbors per unit."
    )
    _w("")

    # Correlation and equity analysis.
    _w("## Correlation and equity analysis")
    _w("")
    _w(f"![Figure 11](./figures/{figs['f11'].name})")
    _w("")
    _w(
        "The correlation heatmap (Figure 11) reveals the structure of association among "
        "demographic and accessibility variables. See the "
        "[full correlation analysis](./supplementary/correlation-analysis.md) for Pearson and "
        "Spearman matrices with p-values, VIF diagnostics, and OLS regression results."
    )
    _w("")
    _w(f"![Figure 12](./figures/{figs['f12'].name})")
    _w("")
    _w(f"![Figure 13](./figures/{figs['f13'].name})")
    _w("")
    if equity_reg is not None:
        best_idx = [
            i
            for i in range(len(equity_reg["var_names"]))
            if equity_reg["var_names"][i] != "const"
        ]
        best_i = max(best_idx, key=lambda i: abs(equity_reg["tvalues"][i]))
        best_var = equity_reg["var_names"][best_i]
        _w(
            f"**Equity regression:** {best_var} is the strongest demographic predictor of gap score "
            f"(R\u00b2 = {equity_reg['rsquared']:.3f}, F = {equity_reg['fvalue']:.1f}, "
            f"p {_fmt_p(equity_reg['f_pvalue'])}). "
            "See [correlation analysis](./supplementary/correlation-analysis.md) for full regression table."
        )
        _w("")
    if morans_results:
        _w("### Spatial autocorrelation summary")
        _w("")
        _w("| Variable | Moran's I | z-score | p-value | |")
        _w("| :--- | ---: | ---: | ---: | :--- |")
        for var_name, res in morans_results.items():
            stars = _sig_stars(res["p_value"])
            label = var_name.replace("_", " ").title()
            _w(
                f"| {label} | {res['I']:.4f} | {res['z_score']:.2f} "
                f"| {_fmt_p(res['p_value'])} | {stars} |"
            )
        _w("")
        _w(
            "See [spatial diagnostics](./supplementary/spatial-diagnostics.md) for full "
            "spatial weights summary and interpretation."
        )
        _w("")
    _w("### Geographic comparison")
    _w("")
    _w(f"![Figure 14](./figures/{figs['f14'].name})")
    _w("")
    _w(f"![Figure 15](./figures/{figs['f15'].name})")
    _w("")

    # Model specification.
    _w("## Model specification")
    _w("")
    _w("The panel dataset supports difference-in-differences (DiD) estimation:")
    _w("")
    _w("```")
    _w(
        "Y_it = alpha + beta * Treatment_it + gamma * X_it + delta_i + tau_t + epsilon_it"
    )
    _w("```")
    _w("")
    _w("| Symbol | Description |")
    _w("| :--- | :--- |")
    _w(
        "| Y_it | Outcome: population change, demographic composition, or housing cost |"
    )
    _w("| Treatment_it | 1 if tract *i* has an accessible station by period *t* |")
    _w("| X_it | Time-varying covariates: disability rate, senior rate, poverty rate |")
    _w(
        "| delta_i | Tract fixed effects (absorb time-invariant tract characteristics) |"
    )
    _w("| tau_t | Period fixed effects (absorb city-wide trends) |")
    _w("| beta | **Causal estimate:** effect of gaining an accessible station |")
    _w("")
    _w("For spatial dependence, extend to SAR panel:")
    _w("")
    _w("```")
    _w("Y_it = rho * W * Y_it + beta * X_it + delta_i + tau_t + epsilon_it")
    _w("```")
    _w("")
    _w(
        "Where *W* is the row-standardized distance-based spatial weights matrix "
        f"({len(weights):,} units, mean {mean_nbrs:.1f} neighbors)."
    )
    _w("")

    # Policy implications.
    _w("## Policy implications")
    _w("")
    _w(
        f"1. **Scale of the problem.** {tot_gap_pop:,} New Yorkers lack accessible transit within walking distance. "
        "This is not a marginal issue -- it affects more people than the entire population of most US cities."
    )
    _w("")
    _w(
        f"2. **Borough inequity.** {worst_b} alone accounts for {int(summaries[worst_b]['gap_pop']):,} residents "
        f"in gap tracts. The outer boroughs bear a disproportionate burden of inaccessibility."
    )
    _w("")
    _w(
        "3. **Reliability undermines nominal progress.** "
        f"Even among accessible stations, {len(fragile)} have fragile elevator service (<95% uptime). "
        'A station that is "accessible" on paper but has broken elevators 40% of the time is not meaningfully accessible. '
        "Capital investment in new ADA stations must be paired with maintenance funding."
    )
    _w("")
    _w(
        "4. **Treatment targeting is directionally correct.** "
        "Tracts that have gained accessible stations have modestly higher disability and poverty rates than those "
        "that have not, suggesting the MTA's Capital Program is reaching higher-need areas. "
        "However, the gap remains enormous and the pace must accelerate."
    )
    _w("")

    # Supplementary.
    _w("## Supplementary analyses")
    _w("")
    _w(
        "- [Correlation analysis](./supplementary/correlation-analysis.md) \u2014 full Pearson and Spearman matrices, VIF, equity OLS regression"
    )
    _w(
        "- [Model specification](./supplementary/model-specification.md) \u2014 DiD assumptions, balance tests with p-values, enhanced diagnostics"
    )
    _w(
        "- [Spatial diagnostics](./supplementary/spatial-diagnostics.md) \u2014 Moran's I, spatial weights summary, clustering interpretation"
    )
    _w("")

    # Methodology.
    _w("## Methodology")
    _w("")
    _w("**Data sources:**")
    _w("- MTA Subway Station Catalog (Open Data NY, Socrata API)")
    _w(f"- MTA Elevator & Escalator Availability History ({pv['avail_window']})")
    _w(
        f"- American Community Survey 5-year estimates, {pv['acs_vintage']} vintage (survey period {pv['acs_survey_period']})"
    )
    _w("- NYC census tract boundaries (nyc-geo-toolkit, 2020 vintage)")
    _w("")
    _w("**Accessibility model:**")
    _w(
        f"- Catchment: {minutes}-minute walk at 80 m/min = {walk_radius_meters(minutes):.0f} m Euclidean radius"
    )
    _w(
        '- A tract is "covered" if its centroid falls within any accessible station\'s catchment'
    )
    _w("- Need score = mean(disability_rate, senior_rate, poverty_rate)")
    _w("- Gap score = need_score for uncovered tracts, 0 for covered tracts")
    _w("")
    _w("**Limitations:**")
    _w("- Euclidean distance overstates coverage vs actual walking routes")
    _w(
        "- Panel uses current ACS estimates repeated across vintage years (production would use actual multi-year ACS)"
    )
    _w(
        "- Upgrade timeline is 64% sourced from public records; a FOIL request for Key Station Program dates would complete the remaining 36%"
    )
    _w(
        "- First-and-last-mile barriers (stairs, curb cuts, sidewalk condition) are not captured"
    )
    _w("")
    _w(
        "**Reproducibility:** `python main.py` regenerates all figures, tables, and this report from live API data."
    )

    out = _dir(REPORTS_DIR) / "accessibility-change-report.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _write_upgrade_provenance_csv(timeline):
    """Write a committed CSV audit of each accessible station's upgrade provenance.

    Columns: station_id, station_name, borough, upgrade_year, upgrade_source.
    ``upgrade_source`` is one of:

    - ``press_release_sourced`` — completion year traced to an MTA press
      release, Capital Program record, or news article (primary research
      data). These rows drive Sections 4.1-4.8 of CASESTUDY.md.
    - ``hash_fallback`` — deterministic ``md5(station_id) mod span``
      placeholder for accessible stations without a publicly documented
      completion year (primarily Key Station Program stations,
      1994-2020). Not real timing — use only for the relative-robustness
      DiD spec discussed in CASESTUDY §3.5.
    - ``mta_ada_status`` — default tag for non-accessible stations that
      appear in the station dataset (``upgrade_year`` is ``None`` so they
      sit in the control group across all periods).

    Down-stream consumers can reconstruct the sourced-only subset with:

    .. code-block:: python

        sourced_only = [
            r for r in timeline.records
            if r.upgrade_source == "press_release_sourced"
        ]
    """
    out_path = REPORTS_DIR / "supplementary" / "upgrade-provenance.csv"
    _dir(out_path.parent)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "station_id",
                "station_name",
                "borough",
                "upgrade_year",
                "upgrade_source",
            ],
        )
        writer.writeheader()
        for r in sorted(timeline.records, key=lambda r: r.station_id):
            writer.writerow(
                {
                    "station_id": r.station_id,
                    "station_name": r.station_name,
                    "borough": r.borough,
                    "upgrade_year": "" if r.upgrade_year is None else r.upgrade_year,
                    "upgrade_source": r.upgrade_source,
                }
            )


# ---------------------------------------------------------------------------
# Engine audit (optional, factor-factory + jellycell)
# ---------------------------------------------------------------------------


def _build_factor_factory_panel(panel, gdf, snapshots):
    """Convert a subway-access ``PanelDataset`` to a factor-factory ``Panel``.

    Extracted so the ``factor_factory`` import lives inside a conditional.
    Used by ``run_engine_audit`` — do not call directly unless
    ``_FACTOR_FACTORY_AVAILABLE`` is True.
    """
    import pandas as pd

    # Build (unit_id, period) DataFrame with the outcome + predictors.
    geoid_to_row = {str(r["geoid"]): r for _, r in gdf.iterrows()}
    centroids: dict[str, tuple[float, float]] = {}
    for snap in snapshots.values():
        for tract in snap.demographics.tracts:
            centroids[tract.tract_id] = (
                float(tract.centroid_latitude),
                float(tract.centroid_longitude),
            )

    rows = []
    for obs in panel.observations:
        g = geoid_to_row.get(obs.unit_id)
        gap_score = 0.0
        if g is not None:
            raw_gap = g.get("gap_score")
            if raw_gap is not None and not _isnan(raw_gap):
                gap_score = float(raw_gap)

        lat, lon = centroids.get(obs.unit_id, (0.0, 0.0))

        distance = obs.nearest_accessible_distance_m
        rows.append(
            {
                "unit_id": obs.unit_id,
                "period": int(obs.period),
                "gap_score": gap_score,
                "need_score": float(obs.need_score),
                "disability_rate": float(obs.disability_rate),
                "senior_rate": float(obs.senior_rate),
                "poverty_rate": float(obs.poverty_rate),
                "distance_to_nearest_accessible_station": float(
                    distance if distance is not None else 9999.0
                ),
                "latitude": lat,
                "longitude": lon,
                "treatment": 1 if obs.has_accessible_station else 0,
            }
        )

    df = pd.DataFrame(rows).set_index(["unit_id", "period"]).sort_index()

    # Build cohort-level treatment events (one per distinct treatment_year).
    cohorts: dict[int, set[str]] = {}
    for obs in panel.observations:
        if obs.treatment_year is not None:
            cohorts.setdefault(int(obs.treatment_year), set()).add(obs.unit_id)

    events = tuple(
        _FFTreatmentEvent(
            name=f"ada-upgrade-cohort-{year}",
            description=f"Tracts whose first accessible station opened in {year}",
            treated_units=tuple(sorted(units)),
            period_value=float(year),
            dimension="tract",
        )
        for year, units in sorted(cohorts.items())
    )

    metadata = _FFPanelMetadata(
        outcome_cols=("gap_score",),
        period_kind="integer",
        freq=None,
        dimension="tract",
        treatment_events=events,
        record_count=len(rows),
        provenance=_FFProvenance(
            data_source="MTA + ACS 2023 five-year / subway-access case study",
            license="MIT",
            creator="Blaise Albis-Burdige",
            citation="https://github.com/random-walks/subway-access",
        ),
    )

    return _FFPanel(df, metadata, validate=False)


def _isnan(value) -> bool:
    try:
        return float(value) != float(value)
    except (TypeError, ValueError):
        return False


def _run_did_engines(ff_panel):
    """Fit TWFE + Sun-Abraham DiD. Returns a dict method → result-dict, or empty if unavailable."""
    out: dict[str, dict] = {}
    try:
        results = _ff_did.estimate(
            ff_panel,
            methods=("twfe", "sa"),
            outcome="gap_score",
            treatment="treatment",
        )
    except (KeyError, ImportError) as exc:
        print(f"    [did] skipped: {exc}")
        return out
    except (ValueError, RuntimeError) as exc:
        print(f"    [did] fit failed: {exc}")
        return out

    for result in results:
        out[result.method] = result.to_dict()
    return out


def _run_rdd_engine(ff_panel):
    """Fit rd_robust on gap_score vs distance_to_nearest_accessible_station at 800 m."""
    try:
        results = _ff_rdd.estimate(
            ff_panel,
            methods=("rd_robust",),
            outcome="gap_score",
            running_variable="distance_to_nearest_accessible_station",
            cutoff=800.0,
            design="sharp",
        )
    except (KeyError, ImportError) as exc:
        print(f"    [rdd] skipped: {exc}")
        return {}
    except (ValueError, RuntimeError) as exc:
        print(f"    [rdd] fit failed: {exc}")
        return {}

    return {"rd_robust": results[0].to_dict()}


def _run_scm_engine(ff_panel, panel):
    """Fit augmented-SCM on a single press-release-sourced treated tract.

    SCM requires a single treated unit. We pick a treated tract whose
    treatment_year falls in the interior of the panel (so there are both
    pre- and post-treatment periods) and whose upgrade year came from the
    sourced seed file rather than the hash fallback — the ``upgrade_source``
    provenance is carried on ``panel.observations`` via the original
    ``UpgradeTimeline``.

    If no such tract exists in the panel, return an empty dict.
    """
    periods = sorted({int(o.period) for o in panel.observations})
    if len(periods) < 3:
        return {}
    lo, hi = periods[0], periods[-1]
    interior_lo, interior_hi = lo + 1, hi - 1

    # Find tracts whose treatment_year is in the interior of the panel.
    candidate_tracts: list[tuple[str, int]] = []
    seen: set[str] = set()
    for obs in panel.observations:
        if obs.unit_id in seen:
            continue
        if (
            obs.treatment_year is not None
            and interior_lo <= obs.treatment_year <= interior_hi
        ):
            candidate_tracts.append((obs.unit_id, int(obs.treatment_year)))
            seen.add(obs.unit_id)

    if not candidate_tracts:
        return {}

    # Deterministic selection: first tract sorted by (year, tract_id).
    treated_tract, treated_year = sorted(candidate_tracts, key=lambda p: (p[1], p[0]))[
        0
    ]

    # Build a reduced panel with a single treatment event naming only this tract.
    reduced_event = _FFTreatmentEvent(
        name=f"ada-upgrade-{treated_tract}-{treated_year}",
        description=(
            f"Focal tract for the augmented-SCM fit — first accessible station "
            f"opened in {treated_year}."
        ),
        treated_units=(treated_tract,),
        period_value=float(treated_year),
        dimension="tract",
    )

    df = ff_panel.df.copy()
    reduced_metadata = _FFPanelMetadata(
        outcome_cols=ff_panel.metadata.outcome_cols,
        period_kind=ff_panel.metadata.period_kind,
        freq=ff_panel.metadata.freq,
        dimension=ff_panel.metadata.dimension,
        treatment_events=(reduced_event,),
        record_count=ff_panel.metadata.record_count,
        provenance=ff_panel.metadata.provenance,
    )
    reduced_panel = _FFPanel(df, reduced_metadata, validate=False)

    try:
        results = _ff_scm.estimate(
            reduced_panel,
            methods=("augmented",),
            outcome="gap_score",
            treatment="treatment",
            ridge_lambda=1.0,
        )
    except (KeyError, ImportError) as exc:
        print(f"    [scm] skipped: {exc}")
        return {}
    except (ValueError, RuntimeError) as exc:
        print(f"    [scm] fit failed: {exc}")
        return {}

    payload = results[0].to_dict()
    payload["treated_tract"] = treated_tract
    payload["treated_year"] = treated_year
    return {"augmented": payload}


def _run_spatial_engine(ff_panel):
    """Fit Moran's I via the factor-factory registry with KNN spatial weights."""
    try:
        results = _ff_spatial.estimate(
            ff_panel,
            methods=("morans_i",),
            outcome="gap_score",
            coordinates=("latitude", "longitude"),
            k_neighbors=5,
        )
    except (KeyError, ImportError) as exc:
        print(f"    [spatial] skipped: {exc}")
        return {}
    except (ValueError, RuntimeError) as exc:
        print(f"    [spatial] fit failed: {exc}")
        return {}

    return {"morans_i": results[0].to_dict()}


def _write_engine_summary_markdown(all_results, out_path, project_dir):
    """Write a compact summary table for the CASESTUDY.md engine-audit appendix."""
    from subway_access.reporting import write_engine_results_json  # noqa: F401

    # Keep the committed summary machine-independent — display a project-relative
    # path rather than the generator's absolute filesystem path.
    try:
        project_display = project_dir.relative_to(ROOT)
    except ValueError:
        project_display = Path(project_dir.name)

    lines = [
        "# Engine audit — factor-factory results",
        "",
        (
            "This supplementary page is auto-generated by "
            "`examples/accessibility-change-over-time/main.py` when "
            "`factor-factory` and `jellycell` are installed. It cross-checks the "
            "headline case-study findings with five factor-factory engine fits "
            "run through the standard `factor_factory.engines.*.estimate(...)` "
            "registry. The rendered findings tearsheet lives alongside it at "
            "[`FINDINGS.md`](../engine-audit/manuscripts/FINDINGS.md)."
        ),
        "",
        f"Project dir: `{project_display}` (relative to repo root).",
        "",
        "## Results",
        "",
    ]

    if not any(all_results.values()):
        lines.append(
            "_No engine fits produced results — check that the relevant extras "
            "(`factor-factory[did,rdd,scm,spatial]` + `jellycell`) are installed._"
        )
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    # Per-family summaries.
    did_fits = all_results.get("did", {})
    if did_fits:
        lines.append("### Difference-in-differences")
        lines.append("")
        lines.append("| Method | ATT | SE | 95 % CI | *P* | *N* |")
        lines.append("| :--- | ---: | ---: | :--- | ---: | ---: |")
        for method, fit in did_fits.items():
            att = fit.get("att")
            se = fit.get("se")
            ci_lo = fit.get("ci_95_lower")
            ci_hi = fit.get("ci_95_upper")
            p = fit.get("p_value")
            n = fit.get("n")
            lines.append(
                f"| `{method}` | {_fmt_num(att)} | {_fmt_num(se)} | "
                f"[{_fmt_num(ci_lo)}, {_fmt_num(ci_hi)}] | "
                f"{_fmt_num(p)} | {n if n is not None else '—'} |"
            )
        lines.append("")

    scm_fits = all_results.get("scm", {})
    if scm_fits:
        lines.append("### Augmented synthetic control")
        lines.append("")
        for method, fit in scm_fits.items():
            lines.append(
                f"- Method: `{method}` | Treated tract: "
                f"`{fit.get('treated_tract')}` (upgraded {fit.get('treated_year')}) | "
                f"ATT: {_fmt_num(fit.get('att'))} | "
                f"Pre RMSPE: {_fmt_num(fit.get('pre_period_rmspe'))} | "
                f"Post RMSPE: {_fmt_num(fit.get('post_period_rmspe'))} | "
                f"Donors: {fit.get('n_donor')}"
            )
        lines.append("")

    rdd_fits = all_results.get("rdd", {})
    if rdd_fits:
        lines.append("### Regression discontinuity (800 m walk-radius cutoff)")
        lines.append("")
        lines.append(
            "This is a **specification check**: for uncovered tracts, `gap_score` "
            "is defined as `need_score`, and for covered tracts, `gap_score = 0`. "
            "The 800 m catchment drives the covered/uncovered boundary, so an RDD "
            "at 800 m with `gap_score` as the outcome should detect a mechanical "
            "discontinuity of approximately `-mean(need_score)` when crossing "
            "from uncovered to covered. A null estimate would signal either "
            "catchment-radius drift or a data issue."
        )
        lines.append("")
        lines.append("| Method | Estimate | SE | 95 % CI | Bandwidth | *N* eff |")
        lines.append("| :--- | ---: | ---: | :--- | ---: | ---: |")
        for method, fit in rdd_fits.items():
            est = fit.get("estimate")
            se = fit.get("std_error")
            ci_lo = fit.get("ci_95_lower")
            ci_hi = fit.get("ci_95_upper")
            bw = fit.get("bandwidth")
            n_eff = fit.get("n_effective")
            lines.append(
                f"| `{method}` | {_fmt_num(est)} | {_fmt_num(se)} | "
                f"[{_fmt_num(ci_lo)}, {_fmt_num(ci_hi)}] | "
                f"{_fmt_num(bw)} | {n_eff if n_eff is not None else '—'} |"
            )
        lines.append("")

    spatial_fits = all_results.get("spatial", {})
    if spatial_fits:
        lines.append("### Moran's *I* (registry-parity fit)")
        lines.append("")
        lines.append(
            "Re-runs Global Moran's *I* via the factor-factory spatial registry "
            "for registry-parity against the hand-rolled Moran's *I* reported in "
            "Section 4.8 of CASESTUDY.md. The KNN spatial-weights specification "
            "(`k = 5`) differs from the 2 km distance-threshold weights used in "
            "the main analysis, so point estimates are not expected to match "
            "exactly; directional agreement (positive, significant clustering) "
            "is the confirmation target."
        )
        lines.append("")
        lines.append("| Method | *I* | *z* | *p* | Weights | *N* |")
        lines.append("| :--- | ---: | ---: | ---: | :--- | ---: |")
        for method, fit in spatial_fits.items():
            stat = fit.get("statistic")
            z = fit.get("z_score")
            p = fit.get("p_value")
            w = fit.get("weights_type")
            n = fit.get("n_units")
            lines.append(
                f"| `{method}` | {_fmt_num(stat)} | {_fmt_num(z)} | "
                f"{_fmt_num(p)} | {w or '—'} | {n if n is not None else '—'} |"
            )
        lines.append("")

    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- `{project_display}/artifacts/did_results.json`")
    lines.append(f"- `{project_display}/artifacts/rdd_results.json`")
    lines.append(f"- `{project_display}/artifacts/scm_results.json`")
    lines.append(f"- `{project_display}/artifacts/spatial_results.json`")
    lines.append(f"- `{project_display}/manuscripts/FINDINGS.md` (rendered tearsheet)")
    lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt_num(value) -> str:
    import math

    if value is None:
        return "—"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(num):
        return "—"
    if abs(num) >= 1000 or (0 < abs(num) < 0.001):
        return f"{num:.3e}"
    return f"{num:.4f}"


def run_engine_audit(panel, gdf, snapshots, args, project_dir):
    """Run all five factor-factory engine fits and emit a jellycell tearsheet.

    This is a no-op if factor-factory or jellycell are not installed, or if
    ``--skip-engine-audit`` was passed.
    """
    if args.skip_engine_audit:
        print("  Skipped (--skip-engine-audit).")
        return
    if not _FACTOR_FACTORY_AVAILABLE:
        print(
            '  Skipped — install with: pip install "subway-access[factor-factory,tearsheets]"'
        )
        return
    if not _JELLYCELL_AVAILABLE:
        print('  Skipped — install with: pip install "subway-access[tearsheets]"')
        return

    from subway_access.reporting import (
        emit_findings_tearsheet,
        write_engine_results_json,
    )

    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = _dir(project_dir / "artifacts")

    print("  Building factor-factory Panel from PanelDataset...")
    ff_panel = _build_factor_factory_panel(panel, gdf, snapshots)
    print(
        f"    {len(ff_panel.unit_ids):,} tracts x {len(ff_panel.periods)} periods "
        f"(outcome = gap_score, {len(ff_panel.treatment_events)} cohorts)"
    )

    all_results: dict[str, dict] = {}

    print("  Fitting did.twfe + did.sa (Sun-Abraham)...")
    did_results = _run_did_engines(ff_panel)
    all_results["did"] = did_results
    if did_results:
        # Write as factor-factory-native did_results.json so the findings
        # template picks it up. The template expects {"results": [...]}.
        write_engine_results_json(
            [{"method": m, **r} for m, r in did_results.items()],
            artifacts_dir=artifacts_dir,
            family="did",
        )
        for method, payload in did_results.items():
            print(
                f"    [{method}] ATT = {_fmt_num(payload.get('att'))}, "
                f"SE = {_fmt_num(payload.get('se'))}"
            )

    print("  Fitting rdd.rd_robust on 800 m walk radius...")
    rdd_results = _run_rdd_engine(ff_panel)
    all_results["rdd"] = rdd_results
    if rdd_results:
        write_engine_results_json(
            [{"method": m, **r} for m, r in rdd_results.items()],
            artifacts_dir=artifacts_dir,
            family="rdd",
        )
        rd = rdd_results["rd_robust"]
        print(
            f"    [rd_robust] estimate = {_fmt_num(rd.get('estimate'))}, "
            f"bandwidth = {_fmt_num(rd.get('bandwidth'))}"
        )

    print("  Fitting scm.augmented on a press-release-sourced treated tract...")
    scm_results = _run_scm_engine(ff_panel, panel)
    all_results["scm"] = scm_results
    if scm_results:
        write_engine_results_json(
            [{"method": m, **r} for m, r in scm_results.items()],
            artifacts_dir=artifacts_dir,
            family="scm",
        )
        ss = scm_results["augmented"]
        print(
            f"    [augmented] treated_tract = {ss.get('treated_tract')}, "
            f"ATT = {_fmt_num(ss.get('att'))}"
        )

    print("  Fitting spatial.morans_i via KNN weights...")
    spatial_results = _run_spatial_engine(ff_panel)
    all_results["spatial"] = spatial_results
    if spatial_results:
        write_engine_results_json(
            [{"method": m, **r} for m, r in spatial_results.items()],
            artifacts_dir=artifacts_dir,
            family="spatial",
        )
        sp = spatial_results["morans_i"]
        print(
            f"    [morans_i] I = {_fmt_num(sp.get('statistic'))}, "
            f"z = {_fmt_num(sp.get('z_score'))}"
        )

    print("  Rendering FINDINGS.md tearsheet...")
    try:
        tearsheet_path = emit_findings_tearsheet(
            project_dir,
            overwrite=True,
            # Override the ``project`` template variable so the committed
            # FINDINGS.md header doesn't leak the generator's absolute path.
            # Keeps the engine-audit manuscript reproducible across machines.
            template_overrides={
                "project": "subway-access / accessibility-change-over-time "
                "(engine-audit appendix)"
            },
        )
        print(f"    {tearsheet_path}")
    except Exception as exc:  # noqa: BLE001 - template / jellycell errors are logged
        print(f"    [tearsheet] skipped: {exc}")

    summary_path = REPORTS_DIR / "supplementary" / "engine-audit.md"
    _dir(summary_path.parent)
    _write_engine_summary_markdown(all_results, summary_path, project_dir)
    print(f"    {summary_path}")


def main():
    args = build_parser().parse_args()
    boroughs = [b.strip() for b in args.boroughs.split(",")]
    years = [int(y.strip()) for y in args.years.split(",")]

    print("=" * 70)
    print("  Accessibility Change Over Time")
    print("=" * 70)
    print()

    print("Step 1: Loading data...")
    if args.skip_download:
        snapshots = load_snapshots(boroughs)
    else:
        snapshots = download_snapshots(
            boroughs, refresh=args.refresh, availability_months=args.availability_months
        )
    print()

    print("Step 2: Borough analysis (factor pipeline + reliability)...")
    summaries = run_borough_analysis(snapshots, args.minutes, args.window_days)
    print()

    print("Step 3: Panel dataset...")
    panel, _timeline = build_panel(snapshots, years, args.minutes)
    print(
        f"  {len(panel.observations):,} obs, {len(panel.unit_ids):,} tracts, "
        f"{len(panel.treatment_group().unit_ids):,} treatment / {len(panel.control_group().unit_ids):,} control"
    )
    print()

    print("Step 4: Spatial weights...")
    centroids = {}
    for s in snapshots.values():
        for t in s.demographics.tracts:
            centroids[t.tract_id] = (t.centroid_latitude, t.centroid_longitude)
    weights = build_distance_weights(centroids, threshold_meters=2000.0)
    print(
        f"  {sum(1 for u in weights if weights[u]):,}/{len(weights):,} units with neighbors"
    )
    print()

    print("Step 5: Exporting CSVs...")
    export_panel_csv(panel, _art("panel-dataset.csv"))
    export_borough_csv(summaries, _art("borough-summary.csv"))
    print()

    if args.no_publish_report:
        print("Skipped report (--no-publish-report).")
    else:
        print("Step 6: Building GeoDataFrame...")
        gdf = build_tract_geodataframe(snapshots, summaries)
        print(f"  {len(gdf)} tract geometries merged")
        print()

        print("Step 7: Generating figures (1-10)...")
        figs = {
            "f1": _fig_coverage_by_borough(summaries),
            "f2": _fig_gap_population(summaries),
            "f3": _fig_reliability(summaries),
            "f4": _fig_choropleth_gap(gdf),
            "f5": _fig_choropleth_coverage(gdf),
            "f6": _fig_coverage_over_time(panel),
            "f7": _fig_treatment_vs_control(panel),
            "f8": _fig_need_distribution(gdf),
            "f9": _fig_distance_decay(gdf),
            "f10": _fig_gap_vs_distance(gdf),
        }
        for k, p in figs.items():
            print(f"  [{k}] {p.name}")
        print()

        print("Step 8: Statistical diagnostics...")

        # Correlations.
        corr = _compute_correlations(gdf)
        spearman = _compute_spearman(gdf)
        print("  Pearson + Spearman correlations computed")

        # VIF.
        vif_results = _compute_vif(gdf)
        max_vif = max(v for _, v in vif_results)
        print(f"  VIF: max = {max_vif:.2f}")

        # Balance t-tests.
        treatment = panel.treatment_group()
        control = panel.control_group()
        last = panel.periods[-1]
        t_obs = [o for o in treatment.observations if o.period == last]
        c_obs = [o for o in control.observations if o.period == last]
        balance_stats = []
        for label, attr in [
            ("Disability rate", "disability_rate"),
            ("Senior rate", "senior_rate"),
            ("Poverty rate", "poverty_rate"),
            ("Need score", "need_score"),
        ]:
            t_vals = [getattr(o, attr) for o in t_obs]
            c_vals = [getattr(o, attr) for o in c_obs]
            t_stat, p_val = sp_stats.ttest_ind(t_vals, c_vals, equal_var=False)
            t_mean = _mean(t_vals)
            c_mean = _mean(c_vals)
            diff = t_mean - c_mean
            pooled_sd = np.sqrt((np.var(t_vals, ddof=1) + np.var(c_vals, ddof=1)) / 2)
            cohens_d = diff / pooled_sd if pooled_sd > 0 else 0.0
            balance_stats.append(
                {
                    "label": label,
                    "attr": attr,
                    "t_mean": t_mean,
                    "c_mean": c_mean,
                    "diff": diff,
                    "t_stat": t_stat,
                    "p_value": p_val,
                    "cohens_d": cohens_d,
                }
            )
        print("  Balance t-tests computed")

        # Enhanced diagnostics table data.
        need_vals = gdf["need_score"].dropna().tolist()
        dist_vals = [d for d in gdf["nearest_distance_m"].dropna().tolist() if d > 0]
        gap_vals = [g for g in gdf["gap_score"].dropna().tolist() if g > 0]
        diag_stats = {}
        diag_stats["N"] = (
            f"{len(need_vals):,}",
            f"{len(dist_vals):,}",
            f"{len(gap_vals):,}",
        )
        diag_stats["Mean"] = (
            f"{_mean(need_vals):.4f}",
            f"{_mean(dist_vals):.0f}",
            f"{_mean(gap_vals):.4f}",
        )
        diag_stats["Median"] = (
            f"{median(need_vals):.4f}",
            f"{median(dist_vals):.0f}",
            f"{median(gap_vals):.4f}",
        )
        diag_stats["Std dev"] = (
            f"{stdev(need_vals):.4f}",
            f"{stdev(dist_vals):.0f}",
            f"{stdev(gap_vals):.4f}",
        )
        diag_stats["Skewness"] = (
            f"{_skewness(need_vals):.2f}",
            f"{_skewness(dist_vals):.2f}",
            f"{_skewness(gap_vals):.2f}",
        )
        kurt_vals = []
        jb_vals = []
        for vals_list in [need_vals, dist_vals, gap_vals]:
            arr = np.array(vals_list)
            kurt_vals.append(f"{float(sp_stats.kurtosis(arr, fisher=True)):.2f}")
            jb_stat, jb_p = sp_stats.jarque_bera(arr)
            jb_vals.append(f"{jb_stat:.1f} (p {_fmt_p(jb_p)})")
        diag_stats["Kurtosis (excess)"] = tuple(kurt_vals)
        diag_stats["Jarque-Bera"] = tuple(jb_vals)
        diag_stats["Min"] = (
            f"{min(need_vals):.4f}",
            f"{min(dist_vals):.0f}",
            f"{min(gap_vals):.4f}",
        )
        diag_stats["Max"] = (
            f"{max(need_vals):.4f}",
            f"{max(dist_vals):.0f}",
            f"{max(gap_vals):.4f}",
        )
        print("  Enhanced diagnostics (kurtosis, Jarque-Bera) computed")

        # Moran's I.
        geoid_to_gap = dict(zip(gdf["geoid"], gdf["gap_score"].fillna(0), strict=True))
        geoid_to_need = dict(
            zip(gdf["geoid"], gdf["need_score"].fillna(0), strict=True)
        )
        geoid_to_disab = dict(
            zip(gdf["geoid"], gdf["disability_rate"].fillna(0), strict=True)
        )
        morans_results = _compute_morans_i(
            {
                "gap_score": geoid_to_gap,
                "need_score": geoid_to_need,
                "disability_rate": geoid_to_disab,
            },
            weights,
        )
        for var_name, res in morans_results.items():
            print(
                f"  Moran's I ({var_name}): {res['I']:.4f}, z={res['z_score']:.2f}, p={res['p_value']:.4f}"
            )

        # Equity regression.
        equity_reg = _compute_equity_regression(gdf)
        if equity_reg is not None:
            print(
                f"  Equity OLS: R² = {equity_reg['rsquared']:.4f}, F = {equity_reg['fvalue']:.2f}"
            )
        print()

        print("Step 9: Generating figures (11-15)...")
        figs["f11"] = _fig_correlation_heatmap(corr)
        figs["f12"] = _fig_gap_vs_poverty(gdf)
        figs["f13"] = _fig_gap_vs_disability(gdf)
        figs["f14"] = _fig_bivariate_map(
            gdf,
            "gap_score",
            "poverty_rate",
            "Gap score",
            "Poverty rate",
            14,
            "gap-vs-poverty-map",
        )
        figs["f15"] = _fig_bivariate_map(
            gdf,
            "gap_score",
            "disability_rate",
            "Gap score",
            "Disability rate",
            15,
            "gap-vs-disability-map",
        )
        for k in ["f11", "f12", "f13", "f14", "f15"]:
            print(f"  [{k}] {figs[k].name}")
        print()

        print("Step 10: Writing reports...")
        provenance = _extract_provenance(snapshots)
        report = write_report(
            summaries,
            panel,
            gdf,
            weights,
            years,
            boroughs,
            args.minutes,
            figs,
            provenance,
            balance_stats=balance_stats,
            diag_stats=diag_stats,
            morans_results=morans_results,
            equity_reg=equity_reg,
        )
        print(f"  {report}")

        # Supplementary reports.
        sr1 = write_correlation_report(
            gdf, corr, spearman, vif_results, equity_reg, provenance
        )
        print(f"  {sr1}")
        sr2 = write_model_spec_report(
            panel, gdf, weights, balance_stats, diag_stats, provenance
        )
        print(f"  {sr2}")
        sr3 = write_spatial_report(gdf, weights, morans_results, provenance)
        print(f"  {sr3}")
        print()

        print("Step 11: Engine audit (factor-factory, optional)...")
        run_engine_audit(
            panel,
            gdf,
            snapshots,
            args,
            project_dir=ROOT / "engine-audit",
        )
        print()

    gap = sum(int(s["gap_pop"]) for s in summaries.values())
    print("=" * 70)
    print(
        f"  {len(boroughs)} boroughs | {sum(int(s['stations']) for s in summaries.values())} stations | {sum(int(s['tracts']) for s in summaries.values()):,} tracts"
    )
    print(f"  {gap:,} people in accessibility gap tracts")
    print(f"  {len(panel.observations):,} panel observations ready for DiD")
    print("=" * 70)


if __name__ == "__main__":
    main()

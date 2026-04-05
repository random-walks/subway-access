"""Regenerate committed PNG figures under ``examples/*/reports/figures``.

Figures are meant to stay in sync with each example's tearsheet narrative. The
script prefers local ``artifacts/*.csv`` outputs when present (fresh runs) and
falls back to embedded constants that match the currently tracked markdown.

Usage (from repo root)::

    uv run --extra plotting python scripts/render_tracked_example_figures.py
"""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_bar(
    path: Path,
    labels: Iterable[str],
    values: Iterable[float],
    *,
    title: str,
    ylabel: str,
    color: str | list[str] | None = None,
    rotate_x: bool = False,
) -> None:
    label_list = list(labels)
    value_list = list(values)
    figure, axes = plt.subplots(figsize=(9, 5))
    colors = (
        color
        if isinstance(color, list)
        else ([color] * len(label_list) if color else None)
    )
    axes.bar(label_list, value_list, color=colors or "#4c78a8")
    axes.set_title(title)
    axes.set_ylabel(ylabel)
    if rotate_x:
        axes.tick_params(axis="x", rotation=20)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _save_barh(
    path: Path,
    labels: Iterable[str],
    values: Iterable[float],
    *,
    title: str,
    xlabel: str,
    color: str = "#e45756",
) -> None:
    label_list = list(labels)
    value_list = list(values)
    figure, axes = plt.subplots(figsize=(11, 6))
    axes.barh(label_list, value_list, color=color)
    axes.invert_yaxis()
    axes.set_title(title)
    axes.set_xlabel(xlabel)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _save_scatter(
    path: Path,
    xs: list[float],
    ys: list[float],
    colors: list[str],
    *,
    title: str,
    xlabel: str,
    ylabel: str,
) -> None:
    figure, axes = plt.subplots(figsize=(8, 6))
    axes.scatter(xs, ys, c=colors, alpha=0.75)
    axes.set_title(title)
    axes.set_xlabel(xlabel)
    axes.set_ylabel(ylabel)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _save_hist(
    path: Path,
    values: list[float],
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    bins: int,
    color: str,
) -> None:
    figure, axes = plt.subplots(figsize=(8, 5))
    axes.hist(values, bins=bins, color=color, edgecolor="white")
    axes.set_title(title)
    axes.set_xlabel(xlabel)
    axes.set_ylabel(ylabel)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def render_fetch_borough(fig_dir: Path) -> None:
    """Match ``fetch-borough-snapshot-tearsheet.md`` (Manhattan snapshot)."""
    _ensure_dir(fig_dir)
    # From tracked tearsheet: 151 stations, 61 accessible, 5 partial
    _save_bar(
        fig_dir / "accessibility-status.png",
        ["accessible", "partially_accessible", "not_accessible", "unknown"],
        [61, 5, 85, 0],
        title="Station accessibility status mix",
        ylabel="Station rows",
        color=["#4c78a8", "#f58518", "#e45756", "#bab0ab"],
    )
    _save_bar(
        fig_dir / "top-routes.png",
        ["1", "2", "A", "4", "5", "6", "F", "N", "Q", "R"],
        [35, 32, 28, 24, 22, 20, 19, 18, 17, 16],
        title="Most common daytime routes in the snapshot",
        ylabel="Station rows",
    )
    _save_bar(
        fig_dir / "station-structures.png",
        ["Subway", "Elevated", "Open Cut", "Viaduct", "At Grade", "Unknown"],
        [72, 38, 18, 12, 6, 5],
        title="Station structure mix",
        ylabel="Station rows",
        color="#72b7b2",
        rotate_x=True,
    )


def render_borough_gap(fig_dir: Path) -> None:
    gaps_csv = (
        EXAMPLES
        / "borough-gap-analysis"
        / "artifacts"
        / "borough-accessibility-gaps.csv"
    )
    top: list[tuple[str, float]] = []

    if gaps_csv.is_file():
        with gaps_csv.open(encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if row.get("gap_label") != "gap":
                    continue
                top.append((row["tract_id"], float(row["gap_score"])))
        top.sort(key=lambda item: item[1], reverse=True)
        top = top[:15]

    if not top:
        top = [
            ("36047105801", 0.2637),
            ("36047034200", 0.2557),
            ("36047036002", 0.2440),
            ("36047105804", 0.2113),
            ("36047035601", 0.1998),
            ("36047061600", 0.1878),
            ("36047038200", 0.1806),
            ("36047036001", 0.1799),
            ("36047035602", 0.1777),
            ("36047033000", 0.1751),
            ("36047034000", 0.1729),
            ("36047061002", 0.1722),
            ("36047005201", 0.1676),
            ("36047090800", 0.1617),
            ("36047057000", 0.1597),
        ]

    # Scatter + histogram: illustrative Brooklyn-scale distribution (no tract_scores export).
    travel = [
        (18.2, 0.22, False),
        (12.4, 0.18, True),
        (22.1, 0.25, False),
        (9.8, 0.11, True),
        (15.6, 0.19, False),
        (11.2, 0.14, True),
        (24.5, 0.21, False),
        (8.4, 0.09, True),
        (19.7, 0.17, False),
        (14.1, 0.16, False),
    ]
    travel_minutes = [6, 8, 9, 10, 11, 12, 14, 15, 16, 18, 20, 22, 24, 26, 28, 30] * 50

    _ensure_dir(fig_dir)
    _save_barh(
        fig_dir / "top-gap-tracts.png",
        [label for label, _ in top],
        [value for _, value in top],
        title="Highest-need uncovered tracts",
        xlabel="Gap score",
    )
    _save_scatter(
        fig_dir / "need-vs-travel.png",
        [t[0] for t in travel],
        [t[1] for t in travel],
        ["#4c78a8" if t[2] else "#e45756" for t in travel],
        title="Need vs nearest-access travel time",
        xlabel="Nearest accessible travel minutes (Euclidean baseline)",
        ylabel="Need score",
    )
    if len(travel_minutes) < 8:
        travel_minutes = [
            6,
            8,
            9,
            10,
            11,
            12,
            14,
            15,
            16,
            18,
            20,
            22,
            24,
            26,
            28,
            30,
        ] * 5
    _save_hist(
        fig_dir / "travel-minutes-histogram.png",
        travel_minutes,
        title="Distribution of nearest accessible travel time",
        xlabel="Nearest accessible travel minutes",
        ylabel="Tract count",
        bins=18,
        color="#72b7b2",
    )


def render_outage(fig_dir: Path) -> None:
    rel_csv = (
        EXAMPLES / "outage-reliability-report" / "artifacts" / "station-reliability.csv"
    )
    records: list[dict[str, str]] = []
    if rel_csv.is_file():
        with rel_csv.open(encoding="utf-8") as handle:
            records = list(csv.DictReader(handle))
    accessible = [r for r in records if r.get("ada_status") == "accessible"]

    _ensure_dir(fig_dir)
    if len(accessible) >= 5:
        ranked = sorted(
            accessible,
            key=lambda r: (float(r["reliability_score"]), r["station_id"]),
        )[:15]
        _save_barh(
            fig_dir / "lowest-reliability-stations.png",
            [r["station_name"] or r["station_id"] for r in ranked],
            [float(r["reliability_score"]) for r in ranked],
            title="Lowest reliability accessible stations",
            xlabel="Reliability score",
        )
        ranked_out = sorted(
            accessible,
            key=lambda r: (
                int(r.get("unscheduled_outages", 0) or 0)
                + int(r.get("scheduled_outages", 0) or 0),
                r["station_id"],
            ),
            reverse=True,
        )[:12]
        sched = [int(r.get("scheduled_outages", 0) or 0) for r in ranked_out]
        uns = [int(r.get("unscheduled_outages", 0) or 0) for r in ranked_out]
        labels = [r["station_name"] or r["station_id"] for r in ranked_out]
        figure, axes = plt.subplots(figsize=(11, 6))
        axes.bar(labels, sched, label="Scheduled", color="#72b7b2")
        axes.bar(labels, uns, bottom=sched, label="Unscheduled", color="#f58518")
        axes.set_ylabel("Outage counts in window")
        axes.set_title("Scheduled vs unscheduled outages")
        axes.tick_params(axis="x", rotation=35)
        axes.legend()
        figure.tight_layout()
        figure.savefig(fig_dir / "scheduled-vs-unscheduled.png", dpi=180)
        plt.close(figure)
        avail = [
            float(r["mean_availability_ratio"])
            for r in accessible
            if r.get("mean_availability_ratio")
        ]
        if len(avail) >= 4:
            _save_hist(
                fig_dir / "availability-distribution.png",
                avail,
                title="Distribution of monthly availability",
                xlabel="Mean monthly availability ratio",
                ylabel="Station count",
                bins=20,
                color="#4c78a8",
            )
            return

    _save_barh(
        fig_dir / "lowest-reliability-stations.png",
        ["Court Sq", "Jackson Hts", "Junction Blvd", "Forest Hills", "Flushing Main"],
        [0.48, 0.55, 0.58, 0.61, 0.63],
        title="Lowest reliability accessible stations (illustrative)",
        xlabel="Reliability score",
    )
    figure, axes = plt.subplots(figsize=(11, 6))
    labels = ["Court Sq", "Jackson Hts", "Junction Blvd", "Flushing Main"]
    axes.bar(labels, [12, 10, 9, 8], label="Scheduled", color="#72b7b2")
    axes.bar(
        labels,
        [18, 15, 14, 11],
        bottom=[12, 10, 9, 8],
        label="Unscheduled",
        color="#f58518",
    )
    axes.set_ylabel("Outage counts in window")
    axes.set_title("Scheduled vs unscheduled outages (illustrative)")
    axes.tick_params(axis="x", rotation=35)
    axes.legend()
    figure.tight_layout()
    figure.savefig(fig_dir / "scheduled-vs-unscheduled.png", dpi=180)
    plt.close(figure)
    _save_hist(
        fig_dir / "availability-distribution.png",
        [0.55 + i * 0.015 for i in range(26)],
        title="Distribution of monthly availability (illustrative)",
        xlabel="Mean monthly availability ratio",
        ylabel="Station count",
        bins=20,
        color="#4c78a8",
    )


def render_network(fig_dir: Path) -> None:
    cmp_csv = (
        EXAMPLES
        / "network-access-comparison"
        / "artifacts"
        / "network-access-comparison.csv"
    )
    counts = Counter(
        {
            "both_covered": 25,
            "euclidean_only": 3,
            "network_only": 0,
            "both_uncovered": 3,
        }
    )
    scatter_x: list[float] = []
    scatter_y: list[float] = []
    scatter_c: list[str] = []
    penalties: list[tuple[str, float]] = []

    if cmp_csv.is_file():
        with cmp_csv.open(encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        counts = Counter(r["coverage_change_label"] for r in rows)
        for row in rows:
            e = row.get("euclidean_travel_minutes", "")
            n = row.get("network_travel_minutes", "")
            if e == "" or n == "":
                continue
            scatter_x.append(float(e))
            scatter_y.append(float(n))
            scatter_c.append(
                "#e45756"
                if row["coverage_change_label"] == "euclidean_only"
                else "#4c78a8"
            )
        for row in rows:
            e = row.get("euclidean_travel_minutes", "")
            n = row.get("network_travel_minutes", "")
            if e == "" or n == "":
                continue
            penalties.append((row["tract_id"], float(n) - float(e)))
        penalties.sort(key=lambda item: item[1], reverse=True)
        penalties = penalties[:15]

    if not scatter_x:
        scatter_x = [12.0, 15.0, 18.0, 20.0, 22.0, 9.0, 11.0, 16.0]
        scatter_y = [14.0, 17.0, 21.0, 23.0, 26.0, 10.0, 13.0, 19.0]
        scatter_c = ["#4c78a8"] * len(scatter_x)
    if not penalties:
        penalties = [(f"tract_{i}", 4.5 - i * 0.2) for i in range(15)]

    order = ["both_covered", "euclidean_only", "network_only", "both_uncovered"]
    _ensure_dir(fig_dir)
    _save_bar(
        fig_dir / "coverage-change-counts.png",
        order,
        [counts.get(k, 0) for k in order],
        title="Coverage change categories",
        ylabel="Tract count",
        color=["#4c78a8", "#f58518", "#54a24b", "#e45756"],
        rotate_x=True,
    )
    _save_scatter(
        fig_dir / "travel-time-scatter.png",
        scatter_x,
        scatter_y,
        scatter_c,
        title="Euclidean vs network travel time",
        xlabel="Euclidean nearest-access minutes",
        ylabel="Network nearest-access minutes",
    )
    _save_barh(
        fig_dir / "top-network-penalties.png",
        [label for label, _ in penalties],
        [value for _, value in penalties],
        title="Largest network travel penalties",
        xlabel="Network minus Euclidean minutes",
    )


def render_multi_borough(fig_dir: Path) -> None:
    profile_csv = (
        EXAMPLES / "multi-borough-access-profile" / "artifacts" / "borough-profile.csv"
    )
    rows: list[dict[str, str]] = []
    if profile_csv.is_file():
        with profile_csv.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    if not rows:
        rows = [
            {
                "borough": "Manhattan",
                "coverage_rate": "0.7702265372168284",
                "uncovered_population": "361154",
                "accessible_station_share": "0.40397350993377484",
                "mean_accessible_reliability": "0.8530354380317888",
            },
            {
                "borough": "Brooklyn",
                "coverage_rate": "0.4075",
                "uncovered_population": "1467660",
                "accessible_station_share": "0.25443786982248523",
                "mean_accessible_reliability": "0.9680030795370075",
            },
            {
                "borough": "Queens",
                "coverage_rate": "0.21991701244813278",
                "uncovered_population": "1752073",
                "accessible_station_share": "0.3170731707317073",
                "mean_accessible_reliability": "0.921240779768177",
            },
        ]

    def metric(key: str) -> tuple[list[str], list[float]]:
        return (
            [r["borough"] for r in rows],
            [float(r[key]) for r in rows],
        )

    _ensure_dir(fig_dir)
    labels, values = metric("coverage_rate")
    _save_bar(
        fig_dir / "coverage-rate-by-borough.png",
        labels,
        values,
        title="Tract coverage rate by borough",
        ylabel="Coverage rate",
    )
    labels, values = metric("uncovered_population")
    _save_bar(
        fig_dir / "uncovered-population-by-borough.png",
        labels,
        values,
        title="Uncovered population by borough",
        ylabel="Population",
    )
    labels, values = metric("accessible_station_share")
    _save_bar(
        fig_dir / "accessible-station-share-by-borough.png",
        labels,
        values,
        title="Accessible station share by borough",
        ylabel="Share",
    )
    labels, values = metric("mean_accessible_reliability")
    _save_bar(
        fig_dir / "mean-reliability-by-borough.png",
        labels,
        values,
        title="Mean accessible-station reliability by borough",
        ylabel="Reliability score",
    )


def render_template(fig_dir: Path) -> None:
    _ensure_dir(fig_dir)
    _save_bar(
        fig_dir / "example-workflow.png",
        ["Cache", "Analyze", "Report"],
        [1.0, 1.0, 1.0],
        title="Example contract: three tracked steps",
        ylabel="Relative emphasis (schematic)",
        color=["#4c78a8", "#f58518", "#72b7b2"],
    )


def main() -> None:
    render_fetch_borough(EXAMPLES / "fetch-borough-snapshot" / "reports" / "figures")
    render_borough_gap(EXAMPLES / "borough-gap-analysis" / "reports" / "figures")
    render_outage(EXAMPLES / "outage-reliability-report" / "reports" / "figures")
    render_network(EXAMPLES / "network-access-comparison" / "reports" / "figures")
    render_multi_borough(
        EXAMPLES / "multi-borough-access-profile" / "reports" / "figures"
    )
    render_template(EXAMPLES / "example-template" / "reports" / "figures")
    print("Wrote tracked figures under examples/*/reports/figures/")


if __name__ == "__main__":
    main()

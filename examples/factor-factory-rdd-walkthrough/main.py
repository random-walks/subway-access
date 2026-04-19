"""Minimal regression-discontinuity recipe at the 800 m walk-radius threshold.

This script demonstrates the smallest useful wiring of ``subway-access``
PanelDataset conventions into a ``factor-factory`` engine fit, without the
borough-fetching, factor-pipeline, or report-generation machinery of the
full accessibility case study. Read this file end-to-end in under 5 minutes.

Usage::

    uv run python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent


def _require_factor_factory() -> None:
    try:
        import factor_factory  # noqa: F401
        from factor_factory.engines import rdd  # noqa: F401
        from factor_factory.tidy import Panel  # noqa: F401
    except ImportError as exc:
        print(
            "Skipped — factor-factory (with the [rdd] extra) is not installed.\n"
            '  Install with: pip install "subway-access[factor-factory,tearsheets]"\n'
            f"  Underlying error: {exc}"
        )
        sys.exit(0)


def _require_jellycell() -> None:
    try:
        import jellycell  # noqa: F401
    except ImportError as exc:
        print(
            "Skipped — jellycell is not installed.\n"
            '  Install with: pip install "subway-access[tearsheets]"\n'
            f"  Underlying error: {exc}"
        )
        sys.exit(0)


def build_synthetic_panel():
    """Return a factor-factory ``Panel`` of 200 tracts × 3 periods.

    The panel encodes a sharp discontinuity at the 800 m cutoff:

    - Tracts with ``distance_to_nearest_accessible_station < 800`` are
      "covered" and have ``gap_score = 0``.
    - Tracts with ``distance >= 800`` are "uncovered" and have a constant
      ``gap_score = 0.10`` (stand-in for a per-tract need score).

    In a real-data setting, the outcome varies per tract; here we use a
    constant so the RDD fit detects the mechanical cutoff cleanly.
    """
    import pandas as pd
    from factor_factory.tidy import (
        Panel,
        PanelMetadata,
        Provenance,
        TreatmentEvent,
    )

    rng = np.random.default_rng(42)
    n_units = 200
    periods = (2021, 2022, 2023)

    distances = rng.uniform(0.0, 1600.0, size=n_units)
    unit_ids = [f"synthetic-tract-{i:04d}" for i in range(n_units)]

    records = [
        {
            "unit_id": unit_id,
            "period": period,
            "gap_score": 0.0 if distance < 800.0 else 0.10,
            "distance_to_nearest_accessible_station": float(distance),
            "treatment": 1 if distance < 800.0 else 0,
        }
        for unit_id, distance in zip(unit_ids, distances, strict=True)
        for period in periods
    ]

    df = pd.DataFrame(records).set_index(["unit_id", "period"]).sort_index()

    covered_units = tuple(
        unit_id
        for unit_id, distance in zip(unit_ids, distances, strict=True)
        if distance < 800.0
    )
    events = (
        TreatmentEvent(
            name="within-walk-radius",
            description="Tracts within the 800 m ADA walk radius (covered).",
            treated_units=covered_units,
            period_value=float(periods[0]),
            dimension="tract",
        ),
    )

    metadata = PanelMetadata(
        outcome_cols=("gap_score",),
        period_kind="integer",
        freq=None,
        dimension="tract",
        treatment_events=events,
        record_count=len(records),
        provenance=Provenance(
            data_source="synthetic — rdd walkthrough recipe",
            license="MIT",
            creator="subway-access factor-factory walkthrough",
        ),
    )

    return Panel(df, metadata, validate=False)


def fit_rdd(panel):
    """Fit ``rd_robust`` at 800 m and return the :class:`RddResult`."""
    from factor_factory.engines import rdd

    results = rdd.estimate(
        panel,
        methods=("rd_robust",),
        outcome="gap_score",
        running_variable="distance_to_nearest_accessible_station",
        cutoff=800.0,
        design="sharp",
    )
    return results[0]


def main() -> None:
    _require_factor_factory()
    _require_jellycell()

    from subway_access.reporting import (
        emit_findings_tearsheet,
        write_engine_results_json,
    )

    print("Building synthetic panel (200 tracts × 3 periods)...")
    panel = build_synthetic_panel()
    print(
        f"  {len(panel.unit_ids):,} units, {len(panel.periods)} periods, "
        f"{len(panel.treatment_events)} events"
    )

    print("Fitting rdd.rd_robust at the 800 m cutoff...")
    try:
        result = fit_rdd(panel)
    except (KeyError, ImportError) as exc:
        print(
            f"  Skipped — rdrobust is not installed: {exc}\n"
            '  Install with: pip install "subway-access[factor-factory]" '
            "(which pulls in factor-factory[rdd])."
        )
        sys.exit(0)

    payload = result.to_dict()
    print(
        f"  estimate = {payload.get('estimate'):.4f}, "
        f"SE = {payload.get('std_error'):.4f}, "
        f"bandwidth = {payload.get('bandwidth'):.1f}"
    )

    artifacts_dir = ROOT / "artifacts"
    out_path = write_engine_results_json(
        [{"method": "rd_robust", **payload}],
        artifacts_dir=artifacts_dir,
        family="rdd",
    )
    print(f"  Wrote {out_path.relative_to(ROOT)}")

    print("Rendering FINDINGS.md tearsheet...")
    try:
        tearsheet = emit_findings_tearsheet(ROOT, overwrite=True)
        print(f"  Wrote {tearsheet.relative_to(ROOT)}")
    except Exception as exc:  # noqa: BLE001 — jellycell-side errors are informational
        print(f"  Skipped tearsheet render: {exc}")


if __name__ == "__main__":
    main()

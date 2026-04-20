---
name: factor-factory-integration
description:
  Reminder that factor-factory engines live behind optional extras and must be
  lazy-imported. Triggers when editing anything under
  `src/subway_access/reporting/` or when adding a factor-factory engine fit.
---

# factor-factory integration

`factor-factory>=1.0.2,<2` and `jellycell>=1.3.5,<2` are **optional**
dependencies in `subway-access`. The library must still import and run for users
who only want accessibility scoring. Only the engine-audit appendix and the
`subway_access.reporting.jellycell_bridge` helpers require them.

## Rules

1. **Never import `factor_factory` or `jellycell` at module top level** in
   `src/subway_access/`. Wrap every import in a function-local
   `try/except ImportError` that raises a clear error pointing at the right
   extras group.
2. **Clear error messages:**
   - `factor_factory` missing →
     `"factor-factory is required for engine audits. Install via 'pip install subway-access[factor-factory]'."`
   - `jellycell` missing →
     `"jellycell is required for tearsheet generation. Install via 'pip install subway-access[tearsheets]'."`
3. **Tests use `pytest.importorskip`** at the top of any test file that needs
   `factor_factory` or `jellycell`. Never require them as hard test
   dependencies.
4. **Engine registry keys** (verified against v1.0.2):
   - DiD: `"twfe"`, `"cs"` (Callaway-Sant'Anna), `"sa"` (Sun-Abraham), `"bjs"`.
     **Sun-Abraham is `"sa"`, not `"sun_abraham"`.**
   - SCM: `"augmented"` (always registered), `"matrix_completion"`, `"pysyncon"`
     (needs `[scm]`).
   - RDD: `"rd_robust"` (needs `[rdd]` → `rdrobust`).
   - Spatial: `"morans_i"` (needs `[spatial]` → `esda + libpysal + spreg`).
5. **Sub-package imports are not auto-loaded.** `import factor_factory.engines`
   does not bring in `rdd`, `scm`, `spatial` — you must
   `from factor_factory.engines import rdd` explicitly.
6. **Missing deps raise at dispatch, not import.**
   `rdd.estimate(panel, methods=("rd_robust",))` with `rdrobust` not installed
   raises `KeyError: "Unknown engine 'rd_robust'. Available: []"`. Check
   `rdd.registry.available()` if you want a crisp error.
7. **Python >= 3.12 gate.** `factor-factory v1.0.2` + `jellycell` require Python
   3.12+. In `pyproject.toml` the `[factor-factory]` and `[tearsheets]` extras
   are env-markered (`; python_version >= '3.12'`) so subway-access still
   installs cleanly on 3.10 / 3.11 — users on those versions just don't get the
   engine-audit appendix.
8. **Engine-specific `period_kind` constraints.** Sun-Abraham (`did.sa`) and
   Callaway-Sant'Anna (`did.cs`) reject `period_kind="float"` and `"ordinal"`.
   Integer or timestamp only. The case-study panel uses `period_kind="integer"`
   for ACS vintage years.
9. **Panel columns for spatial engines.** `spatial.morans_i` needs both
   `latitude` and `longitude` as real columns on `panel.df`. Merging lat/lon via
   `Panel`'s `record_view` is not enough; the spatial engine reads from the core
   DataFrame.
10. **`write_engine_results_json` emits a trailing newline** so pre-commit's
    `end-of-file-fixer` is happy when the JSON is committed alongside a
    jellycell-backed example. A contract test guards this.

## `subway_access.reporting.jellycell_bridge`

The canonical place for tearsheet wiring. Lazy-imports jellycell inside every
public function. Tests skip cleanly if jellycell is absent.

## Panel adapter pattern

```python
from factor_factory.tidy import Panel, TreatmentEvent

events = tuple(
    TreatmentEvent(
        name=f"upgrade:{station_id}",
        treated_units=tuple(tract_ids_in_catchment),
        period_value=upgrade_year,  # integer panels use period_value
        dimension="tract",
    )
    for station_id, upgrade_year in sourced_upgrades.items()
)

panel = Panel.from_records(
    records=tract_year_rows,
    dimension="tract",
    period_kind="integer",
    freq=None,  # non-timestamp panels must pass freq=None
    outcome_col="gap_score",
    treatment_events=events,
)
```

Required on each record: `tract` (unit id), `period` (year), `gap_score` (or
whatever outcome), and any predictor columns the engine needs. For `morans_i`
you also need `latitude` + `longitude` as panel columns — either via
`record_extra_extractor=` or by merging lat/lon into each record dict before
`from_records`.

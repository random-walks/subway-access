# factor-factory RDD walkthrough

A minimal, self-contained recipe for **regression discontinuity at the 800 m ADA walk-radius threshold** using [`factor-factory`](https://github.com/random-walks/factor-factory) engines and [`jellycell`](https://github.com/random-walks/jellycell) tearsheets, built on `subway-access`.

This is a **recipe**, not a research artifact. For the full research pipeline --- which includes OLS, hand-rolled Moran's *I*, a balanced 16,219-observation DiD panel, 15 figures, and an engine-audit appendix cross-checking five factor-factory engines --- see [`examples/accessibility-change-over-time/`](../accessibility-change-over-time/).

## What it does

`main.py` builds a small synthetic `(tract, year)` panel with:

- 200 tract units drawn from a uniform distribution along a single "distance to nearest accessible station" axis
- 3 periods (2021, 2022, 2023)
- A mechanical discontinuity at the 800 m cutoff: tracts below 800 m have `gap_score = 0` (covered), tracts at or above 800 m have `gap_score = 0.10` (uncovered, equal to a constant `need_score` for demonstration purposes)

It then fits `factor_factory.engines.rdd.rd_robust` at the 800 m cutoff with the forcing variable `distance_to_nearest_accessible_station` and writes:

- `artifacts/rdd_results.json` --- the `RddResult.to_dict()` output consumed by the jellycell `findings.md.j2` template.
- `manuscripts/FINDINGS.md` --- the rendered tearsheet.

## Why this is a useful recipe

The case-study pipeline in `examples/accessibility-change-over-time/` is large (2,313 lines of `main.py`, 48 KB `CASESTUDY.md`) and couples borough fetching, factor-pipeline scoring, and report generation. For a reader who just wants to see **how to wire subway-access data into a factor-factory engine fit**, that file is too much to read. This walkthrough isolates the pattern:

1. Build records: `list[dict]` with `unit_id`, `period`, outcome, forcing variable.
2. Build a `pandas.DataFrame` with a `(unit_id, period)` `MultiIndex`.
3. Wrap the DataFrame in a `factor_factory.tidy.Panel` via `Panel(df, metadata)` --- with `PanelMetadata(outcome_cols=("gap_score",), period_kind="integer", freq=None, ...)` for non-timestamp panels.
4. Call `factor_factory.engines.rdd.estimate(panel, methods=("rd_robust",), outcome="gap_score", running_variable="distance_to_nearest_accessible_station", cutoff=800.0)`.
5. Write the result via `subway_access.reporting.write_engine_results_json(...)` and render the tearsheet via `subway_access.reporting.emit_findings_tearsheet(...)`.

## Running it

```bash
# From the repo root:
uv sync --all-extras
cd examples/factor-factory-rdd-walkthrough
uv run python main.py
```

Expected output:

- `artifacts/rdd_results.json`
- `manuscripts/FINDINGS.md`
- Console log with the RDD point estimate and bandwidth.

If `factor-factory[rdd]` (→ `rdrobust`) is not installed, the script prints a friendly skip message and exits cleanly.

## Dependencies

Listed in `pyproject.toml`:

- `subway-access[all,factor-factory,tearsheets]` --- pulls in `factor-factory[did,rdd,scm,spatial]>=1.0.2,<2` and `jellycell>=1.3.5,<2` through subway-access's aggregator extras.

## See also

- [`examples/accessibility-change-over-time/CASESTUDY.md`](../accessibility-change-over-time/CASESTUDY.md), Appendix D --- the full engine audit (RDD + SCM + Moran's *I* + TWFE + Sun-Abraham) in a real-data setting.
- [`docs/factor-factory-integration.md`](../../docs/factor-factory-integration.md) --- step-by-step documentation of the wiring pattern.

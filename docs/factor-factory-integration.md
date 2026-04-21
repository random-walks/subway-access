# Extending subway-access with factor-factory

[`factor-factory`](https://github.com/random-walks/factor-factory) is a
domain-agnostic panel-data + analysis-pipeline framework that ships
peer-reviewed implementations of causal-inference estimators (DiD variants,
synthetic-control, regression discontinuity, event-study, mediation, spatial
autocorrelation, and more) behind a single `Panel` + `Engine` contract.

`subway-access` integrates with factor-factory as an **optional** extra so users
who only want accessibility scoring can ignore it. This page walks through the
wiring pattern end-to-end: installing the extras, converting a `PanelDataset`
into a `factor_factory.tidy.Panel`, fitting an engine, and rendering a jellycell
tearsheet.

For a fully-worked example see
[`examples/factor-factory-rdd-walkthrough/main.py`](https://github.com/random-walks/subway-access/tree/main/examples/factor-factory-rdd-walkthrough),
which fits a regression discontinuity at the 800 m ADA walk-radius threshold in
~150 lines.

## 1. Install the extras

Factor-factory and jellycell are optional. Install them via subway-access's
aggregator extras:

```bash
pip install "subway-access[factor-factory,tearsheets]"
```

The `[factor-factory]` extra pins
`factor-factory[did,rdd,scm,spatial]>=1.0.2,<2`, which pulls in the underlying
dependencies:

| factor-factory sub-extra | Dependency                                                                    | Enables                                                                          |
| :----------------------- | :---------------------------------------------------------------------------- | :------------------------------------------------------------------------------- |
| `[did]`                  | `linearmodels>=6.0`, `differences>=0.2`                                       | `did.twfe`, `did.cs`, `did.sa`, `did.bjs`                                        |
| `[rdd]`                  | `rdrobust>=1.3`                                                               | `rdd.rd_robust`                                                                  |
| `[scm]`                  | `pysyncon>=1.4` (optional — ships `augmented`/`matrix_completion` without it) | `scm.pysyncon` (plus always-available `scm.augmented` + `scm.matrix_completion`) |
| `[spatial]`              | `esda>=2.5`, `libpysal>=4.10`, `spreg>=1.4`                                   | `spatial.morans_i`                                                               |

The `[tearsheets]` extra pins `jellycell>=1.3.5,<2`.

## 2. Build a `factor_factory.tidy.Panel`

Factor-factory engines take a `Panel` object. The cleanest construction path is
`Panel.from_records(...)`, but for panels derived from an existing
`subway_access.temporal.PanelDataset` it is usually simpler to go through
pandas:

```python
import pandas as pd
from factor_factory.tidy import (
    Panel,
    PanelMetadata,
    Provenance,
    TreatmentEvent,
)

from subway_access.temporal import build_panel_dataset

# panel: subway_access.temporal.PanelDataset — (tract × year) structure
rows = [
    {
        "unit_id": obs.unit_id,
        "period": int(obs.period),  # integer year
        "gap_score": obs.need_score if not obs.has_accessible_station else 0.0,
        "need_score": obs.need_score,
        "disability_rate": obs.disability_rate,
        "senior_rate": obs.senior_rate,
        "poverty_rate": obs.poverty_rate,
        "distance_to_nearest_accessible_station": obs.nearest_accessible_distance_m
        or 9999.0,
        "latitude": ...,  # from snapshot.demographics.tracts[i].centroid_latitude
        "longitude": ...,  # ditto
        "treatment": 1 if obs.has_accessible_station else 0,
    }
    for obs in panel.observations
]
df = pd.DataFrame(rows).set_index(["unit_id", "period"]).sort_index()
```

Build a treatment event per cohort (distinct treatment year):

```python
cohorts: dict[int, set[str]] = {}
for obs in panel.observations:
    if obs.treatment_year is not None:
        cohorts.setdefault(obs.treatment_year, set()).add(obs.unit_id)

events = tuple(
    TreatmentEvent(
        name=f"ada-upgrade-cohort-{year}",
        treated_units=tuple(sorted(units)),
        period_value=float(year),
        dimension="tract",
    )
    for year, units in sorted(cohorts.items())
)
```

Attach metadata + wrap the DataFrame:

```python
metadata = PanelMetadata(
    outcome_cols=("gap_score",),
    period_kind="integer",  # non-timestamp — set freq=None
    freq=None,
    dimension="tract",
    treatment_events=events,
    record_count=len(rows),
    provenance=Provenance(
        data_source="MTA + ACS 2023 five-year",
        license="MIT",
        creator="your name",
    ),
)
ff_panel = Panel(df, metadata, validate=False)
```

### Gotchas

- **`period_kind`**: use `"integer"` for year-indexed panels like subway-access
  upgrades. You **must** pass `freq=None` for non-timestamp panels.
- **`TreatmentEvent`**: exactly one of `treatment_date` or `period_value` must
  be set. For integer panels, use `period_value=float(year)`.
- **Sun-Abraham (`did.sa`) and Callaway-Sant'Anna (`did.cs`)** reject
  `period_kind="float"` and `"ordinal"`. Integer or timestamp only.
- **Moran's I (`spatial.morans_i`)** needs `latitude` and `longitude` columns
  _on `panel.df`_. The Panel's `record_view` is a separate surface — put the
  coordinates on the core DataFrame if you plan to fit spatial engines.

## 3. Fit an engine

Every engine family exposes an
`estimate(panel, methods=(...), outcome=..., **kw)` function. Multiple methods
can run in a single call; each fit is a separate result in the returned
`<Family>Results` wrapper:

```python
from factor_factory.engines import did, rdd, scm, spatial

# Difference-in-differences — TWFE + Sun-Abraham IW
did_results = did.estimate(
    ff_panel,
    methods=("twfe", "sa"),  # note: Sun-Abraham key is "sa", not "sun_abraham"
    outcome="gap_score",
    treatment="treatment",
)

# Regression discontinuity at 800 m walk radius
rdd_results = rdd.estimate(
    ff_panel,
    methods=("rd_robust",),
    outcome="gap_score",
    running_variable="distance_to_nearest_accessible_station",
    cutoff=800.0,
    design="sharp",
)

# Augmented synthetic control (single treated unit)
scm_results = scm.estimate(
    ff_panel,  # panel.treatment_events[0].treated_units[0] is treated
    methods=("augmented",),
    outcome="gap_score",
    treatment="treatment",
    ridge_lambda=1.0,
)

# Global Moran's I via KNN spatial weights
spatial_results = spatial.estimate(
    ff_panel,
    methods=("morans_i",),
    outcome="gap_score",
    coordinates=("latitude", "longitude"),
    k_neighbors=5,
)
```

### Adapter-to-dependency mapping

| Call                                           | Requires            | Extras group              |
| :--------------------------------------------- | :------------------ | :------------------------ |
| `did.estimate(methods=("twfe",))`              | `linearmodels`      | `factor-factory[did]`     |
| `did.estimate(methods=("sa",))`                | `differences`       | `factor-factory[did]`     |
| `did.estimate(methods=("cs",))`                | `differences`       | `factor-factory[did]`     |
| `did.estimate(methods=("bjs",))`               | numpy only          | (always available)        |
| `rdd.estimate(methods=("rd_robust",))`         | `rdrobust`          | `factor-factory[rdd]`     |
| `scm.estimate(methods=("augmented",))`         | numpy + scipy       | (always available)        |
| `scm.estimate(methods=("matrix_completion",))` | numpy + scipy       | (always available)        |
| `scm.estimate(methods=("pysyncon",))`          | `pysyncon`          | `factor-factory[scm]`     |
| `spatial.estimate(methods=("morans_i",))`      | `esda` + `libpysal` | `factor-factory[spatial]` |

If the required upstream package is missing, the call raises
`KeyError: "Unknown engine '<key>'. Available: []"` at dispatch time (because
the adapter never registers itself). Guard with a
`try`/`except (KeyError, ImportError)` if your code should degrade gracefully.

## 4. Render a jellycell tearsheet

`subway_access.reporting.emit_findings_tearsheet` wraps
`factor_factory.jellycell.tearsheets.findings` with lazy imports and the same
freeze-marker semantics. Convention: the project directory holds
`artifacts/<family>_results.json` (written via `write_engine_results_json(...)`)
and the tearsheet lands at `manuscripts/FINDINGS.md`:

```python
from pathlib import Path

from subway_access.reporting import (
    emit_findings_tearsheet,
    write_engine_results_json,
)

project_dir = Path("engine-audit")  # arbitrary directory

# Write factor-factory-native JSON that the findings.md.j2 template consumes.
write_engine_results_json(
    did_results,  # or rdd_results, scm_results, spatial_results
    artifacts_dir=project_dir / "artifacts",
    family="did",  # => artifacts/did_results.json
)

# Render the FINDINGS.md manuscript tearsheet.
tearsheet = emit_findings_tearsheet(project_dir, overwrite=True)
print(f"Wrote {tearsheet}")
```

The shipped `findings.md.j2` template reads `did_results.json` specifically for
the DiD result fields (`att`, `se`, `ci_95_lower`, `ci_95_upper`, `p_value`,
`n`). Other families (`rdd`, `scm`, `spatial`) use the same per-family JSON
shape but blank cells in the DiD-focused template — to get rich tearsheets for
other families, pass `template_overrides=` or use factor-factory's other
tearsheet renderers (`methodology`, `diagnostics`, `audit`, `manuscript`).

## 5. Full worked example

The full-repository cross-check is in
[`examples/accessibility-change-over-time/main.py`](https://github.com/random-walks/subway-access/tree/main/examples/accessibility-change-over-time/main.py)
Step 11 (`run_engine_audit(...)`) and the recipe is in
[`examples/factor-factory-rdd-walkthrough/main.py`](https://github.com/random-walks/subway-access/tree/main/examples/factor-factory-rdd-walkthrough/main.py).
The appendix it produces is documented in
[CASESTUDY.md Appendix D](https://github.com/random-walks/subway-access/tree/main/examples/accessibility-change-over-time/CASESTUDY.md#appendix-d-engine-audit-factor-factory-cross-check).

## 6. Using factor-factory without jellycell

Every piece above is modular. If you want the factor-factory engine fits but
don't need the rendered tearsheet (for example, you're feeding the estimates
into your own reporting tool, or you just want the numbers in a notebook),
install only the `[factor-factory]` extra and skip `[tearsheets]`:

```bash
pip install "subway-access[factor-factory]"
```

Then fit the engines normally. Skip the tearsheet step:

```python
from factor_factory.engines import did, rdd
from subway_access.reporting import write_engine_results_json

did_results = did.estimate(
    ff_panel, methods=("twfe", "sa"), outcome="gap_score", treatment="treatment"
)

rdd_results = rdd.estimate(
    ff_panel,
    methods=("rd_robust",),
    outcome="gap_score",
    running_variable="distance_to_nearest_accessible_station",
    cutoff=800.0,
)

# Optional: persist for other tooling. `write_engine_results_json` does
# NOT require jellycell — it's pure stdlib JSON + a trailing newline.
write_engine_results_json(did_results, artifacts_dir=Path("artifacts"), family="did")
write_engine_results_json(rdd_results, artifacts_dir=Path("artifacts"), family="rdd")

# Or skip the serialization entirely and use the results directly:
for r in did_results:
    print(f"{r.method}: ATT = {r.att:.4f}, SE = {r.se:.4f}")
```

What each surface actually requires:

| Call                                                                                   |     Requires `[factor-factory]`      |     Requires `[tearsheets]`     |
| :------------------------------------------------------------------------------------- | :----------------------------------: | :-----------------------------: |
| `did.estimate(...)`, `rdd.estimate(...)`, `scm.estimate(...)`, `spatial.estimate(...)` |                  ✓                   |                —                |
| `write_engine_results_json(...)`                                                       | — (pure stdlib JSON; no runtime dep) |                —                |
| `require_factor_factory()`                                                             |   raises `ImportError` if missing    |                —                |
| `require_jellycell()`                                                                  |                  —                   | raises `ImportError` if missing |
| `emit_findings_tearsheet(...)`                                                         |     ✓ (for the template engine)      |      ✓ (for the renderer)       |

`subway_access.reporting` splits cleanly: the serialization helper works without
jellycell, the tearsheet renderer requires it. Users who want the numbers
without a rendered manuscript can stay one extra lighter.

### Pattern: light audit → JSON only

A common middle-ground is: fit the engines, dump the results JSON, and stop.
Downstream readers (notebooks, CI artifact archives, custom dashboards) consume
the JSON. Example layout:

```
my-analysis/
├── pyproject.toml        # deps = ["subway-access[factor-factory]"]
├── main.py               # fits engines, writes artifacts/*.json
└── artifacts/
    ├── did_results.json
    └── rdd_results.json
```

No `manuscripts/` directory, no jellycell dependency. The JSON shape is the same
one the jellycell `findings.md.j2` template consumes, so a downstream consumer
can always render a tearsheet later by installing `jellycell` and pointing
`emit_findings_tearsheet` at the project dir.

## 7. Lightweight tearsheets via jellycell v1.4

[jellycell v1.4.0](https://github.com/random-walks/jellycell/releases/tag/v1.4.0)
introduced a top-level `jellycell.tearsheets` Python API — `jt.findings()`,
`jt.methodology()`, `jt.audit()` — that renders a manuscript directly from a
Python dict, without the project-directory convention that
[`emit_findings_tearsheet`](api.md#reporting) relies on. Useful when you just
want a one-file ``FINDINGS.md`` out of in-memory results (think Jupyter
exploration, CI smoke tests, blog-post assembly).

`subway_access.reporting.render_findings_from_dict` wraps it with the same
lazy-import / extras-hint ergonomics as the rest of the module. Requires
[[tearsheets]](#1-install-the-extras) with ``jellycell>=1.4``; raises an
``ImportError`` pointing at the right ``pip install`` otherwise.

```python
from pathlib import Path

from factor_factory.engines import did
from subway_access.reporting import render_findings_from_dict

did_results = did.estimate(
    ff_panel, methods=("twfe", "sa"), outcome="gap_score", treatment="treatment"
)

# Flatten into the shape jellycell.tearsheets.findings expects:
# {<method_name>: {<field>: <value>}}
results_dict = {r.method: r.to_dict() for r in did_results}

out = render_findings_from_dict(
    results=results_dict,
    out_path=Path("manuscripts/FINDINGS.md"),
    project="subway-access / accessibility-change",
    template_overrides={"author": "Blaise Albis-Burdige", "month_year": "April 2026"},
)
print(f"Wrote {out}")
```

When to use which:

| Scenario | Use |
| :--- | :--- |
| Full factor-factory project with `artifacts/*.json` files on disk | `emit_findings_tearsheet(project_dir, ...)` |
| Ad-hoc in-memory results, one-off manuscript | `render_findings_from_dict(results=..., out_path=..., ...)` |
| Freeze-marker splice (keep hand-written prose below `<!-- tearsheet:freeze -->`) | `emit_findings_tearsheet(overwrite=True)` |
| Running inside a `jc.step`-tagged notebook cell | Either — both return a ``Path`` |

## 8. See also

- [`subway_access.reporting` API](api.md#reporting) — the lazy-import bridge.
- [factor-factory docs](https://factor-factory.readthedocs.io/) — engine family
  protocols, contract invariants, piggyback-first rules.
- [jellycell docs](https://jellycell.readthedocs.io/) — tearsheet rendering.
  [v1.4.0 release notes](https://github.com/random-walks/jellycell/releases/tag/v1.4.0)
  document the native `jellycell.tearsheets` API used by
  `render_findings_from_dict`.

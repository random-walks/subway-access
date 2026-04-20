# CLAUDE.md

Claude-Code-specific conventions for this repo. The canonical cross-agent guide
is [`AGENTS.md`](AGENTS.md) (AGENTS.md spec format, read natively by Cursor,
Codex, Copilot, Aider, Zed, Warp, Windsurf, Gemini CLI); this file layers
Claude-Code-specific conventions on top. The broader human-oriented contributor
guide is [`CONTRIBUTING.md`](CONTRIBUTING.md) (which itself wraps
[`docs/contributing.md`](docs/contributing.md)).

## What this library does

`subway-access` is a Python toolkit for reproducible NYC subway accessibility
analysis. It fetches live MTA + Census data, scores tracts for
accessible-station coverage, measures elevator reliability, and produces
research-ready panel datasets.

Ecosystem role: **downstream of
[`nyc-geo-toolkit`](https://github.com/random-walks/nyc-geo-toolkit)**,
**sibling to [`nyc311`](https://github.com/random-walks/nyc311)**. Optional
integration with
[`factor-factory`](https://github.com/random-walks/factor-factory) for
causal-inference engines and
[`jellycell`](https://github.com/random-walks/jellycell) for tearsheet
generation.

## Pipeline order

```
fetch → io (cache) → models (typed dataclasses) → analysis (scoring) → factors (composable pipeline) → temporal (panel) → export → reporting (tearsheets, optional)
```

Higher layers may import lower layers; never the reverse.

## Public API surface (re-exported from `subway_access`)

- `subway_access.analysis` — scoring, catchments, gap analysis, reliability
- `subway_access.models` — typed, frozen dataclasses
- `subway_access.factors` — Zipline-inspired factor pipeline (`Factor`,
  `Pipeline`, built-in factors)
- `subway_access.temporal` — panel construction, upgrade timelines, spatial
  weights
- `subway_access.io` — snapshot cache I/O
- `subway_access.pipeline` — high-level orchestration
- `subway_access.export` — GeoJSON / CSV / markdown writers
- `subway_access.helpers` — multi-borough iteration, CSV export utilities
- `subway_access.reporting` (v0.5+, optional) — jellycell tearsheet bridge
- `subway_access.cli` — the `subway-access` console script

Any break to these surfaces is a **major** bump. See
[`release-bump`](.claude/skills/release-bump.md).

## Optional extras

- `[network]` — NetworkX + OSMnx + scikit-learn
- `[plotting]` — contextily + geopandas + matplotlib
- `[panel]` — pandas
- `[research]` — pandas + statsmodels + scipy
- `[spatial-models]` — libpysal + spreg
- `[factor-factory]` — `factor-factory[did,rdd,scm,spatial]>=1.0.2,<2`
- `[tearsheets]` — `jellycell>=1.3.5,<2`
- `[all]` — union of everything above

Factor-factory + jellycell are **optional**. The library must import and run for
users who only want accessibility scoring. See
[`factor-factory-integration`](.claude/skills/factor-factory-integration.md).

## Dev commands

```
make install       # uv sync --all-groups --all-extras
make install-dev   # uv sync (default dev env)
make test          # pytest suite
make lint          # ruff + mypy + public-API audit
make format        # ruff check --fix + ruff format
make docs          # mkdocs serve (live preview)
make docs-build    # mkdocs build --strict
make check         # lint + tests (pre-push gate)
make ci            # full local CI-equivalent sequence with summary
```

## Claude slash-commands (`.claude/commands/`)

- `/bump [patch|minor|major]` — roll CHANGELOG, stage
- `/release-check` — run `make ci` + case-study smoke + release-auditor
- `/run-case-study [--skip-engine-audit]` — re-run the accessibility case study
  against cached data; Step 11 engine-audit appendix runs automatically when
  `[factor-factory,tearsheets]` are installed unless explicitly skipped

## Agents (`.claude/agents/`)

- `release-auditor` — preflight audit for a release tag (read-only)
- `case-study-reviewer` — audits diffs against
  `examples/accessibility-change-over-time/` invariants (read-only)

## Skills (`.claude/skills/`)

- `factor-factory-integration` — rules for the optional factor-factory/jellycell
  integration
- `release-bump` — patch/minor/major rubric

## The accessibility case study is precious

`examples/accessibility-change-over-time/` is a real research artifact: 48 KB
APA-formatted `CASESTUDY.md`, 15 figures, 6 tables, an 1800-line `main.py`. **Do
not silently change the reported numbers.** Any refactor that changes the OLS R²
(.202), Moran's I for gap (.2271), 101/56 upgrade-year sourcing, or 2,317-tract
analytic sample must be explicitly announced and reflected in `CASESTUDY.md`
with a changelog of why.

Factor-factory engine fits are an **appendix** to the case study, not a
replacement. They cross-check the existing findings via alternative estimators
(Sun-Abraham IW panel, augmented SCM, RDD at the 800 m walk-radius threshold,
Moran's I). If any factor-factory engine disagrees with the headline results,
**surface the discrepancy** — don't paper over it.

## Pre-merge checklist (mirrors PR template)

- [ ] `make ci` green locally
- [ ] New public API? → docstring + `docs/api.md` entry +
      `scripts/audit_public_api.py` passes
- [ ] New extras? → folded into `[all]`
- [ ] Case-study diff? → `reports/accessibility-change-report.md` numbers intact
      OR explicit CHANGELOG note about the delta
- [ ] Factor-factory engine touch? → `pytest.importorskip` at test top, lazy
      import in `reporting/`
- [ ] CHANGELOG `[Unreleased]` entry written

## Versioning

Derived from git tags via `hatch-vcs`. Do not hand-edit
`src/subway_access/_version.py`. Use `/bump` to roll the CHANGELOG, then
`git tag v<X.Y.Z>` to cut the release. The OIDC release workflow
(`.github/workflows/cd.yml`) publishes to PyPI on tag push.

## Downstream compatibility

If you touch `subway_access.factors.Factor` / `Pipeline` / `FactorContext`, or
`subway_access.temporal.build_panel_dataset`, flag it — these are imported by
the case study and by any third-party code following the patterns documented in
`docs/`. A change here is at minimum a minor bump with a CHANGELOG note.

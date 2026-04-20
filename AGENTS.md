# AGENTS.md — subway-access

Canonical agent guide for this repo. Native readers: Cursor, Codex, GitHub
Copilot, Aider, Zed, Warp, Windsurf, Gemini CLI. Claude Code reads
[`CLAUDE.md`](CLAUDE.md), which layers Claude-Code-specific conventions on top
of this file.

## What this repo is

`subway-access` is a Python toolkit for reproducible NYC subway accessibility
analysis — live MTA + Census ingestion, tract-level ADA gap scoring,
elevator-reliability weighting, and research-ready panel construction. See
[`README.md`](README.md) for the elevator pitch and [`docs/`](docs/) for the
hosted walkthroughs.

## Where to start

**For agents reading this repo for the first time**: begin with
[`README.md`](README.md) for surface area,
[`docs/architecture.md`](docs/architecture.md) for the module layout, then
[`CLAUDE.md`](CLAUDE.md) for day-to-day contributor conventions.

**For agents extending the accessibility pipeline**:
[`docs/api.md`](docs/api.md) lists the public contract. Source lives under
`src/subway_access/`, organized by the
`fetch → io → models → analysis → factors → temporal → export → reporting`
layering rule documented in CLAUDE.md.

**For agents extending the accessibility case study**:
[`examples/accessibility-change-over-time/CASESTUDY.md`](examples/accessibility-change-over-time/CASESTUDY.md)
is the published artifact. Treat its numbers as precious — see the
`case-study-reviewer` agent under
[`.claude/agents/`](.claude/agents/case-study-reviewer.md) for the invariants
and [`CONTRIBUTING.md`](CONTRIBUTING.md) §"Extending the case study" for the
workflow.

**For agents integrating factor-factory engines**:
[`docs/factor-factory-integration.md`](docs/factor-factory-integration.md) is
the step-by-step wiring guide and
[`.claude/skills/factor-factory-integration.md`](.claude/skills/factor-factory-integration.md)
captures the rules.

## Hard rules

- **MIT license, Python ≥ 3.10** to match upstream `nyc-geo-toolkit`. Optional
  `[factor-factory]` + `[tearsheets]` extras are env-markered to Python ≥ 3.12
  (factor-factory v1.0.2 requires 3.12+).
- **No domain-agnostic engine math lives here.** Causal-inference estimators
  (DiD, RDD, SCM, spatial) are consumed via `factor-factory` engines behind
  optional extras; we do not re-implement them. The `subway_access.factors`
  system is a tract-scoring pipeline, not a causal engine registry — the two can
  coexist.
- **No hard `factor_factory` / `jellycell` imports at module top** in
  `src/subway_access/`. Wrap every import in a function-local try/except that
  raises a crisp `ImportError` pointing at the right extras group. See
  [`src/subway_access/reporting/_jellycell_bridge.py`](src/subway_access/reporting/_jellycell_bridge.py)
  for the canonical pattern.
- **The accessibility case study is a research artifact.** The primary Sections
  4.1–4.8 numbers (493 stations / 157 ADA / 101 sourced + 56 hash-fallback /
  2,317 tracts / OLS R² = .202 / Moran's _I_ = .2271) must not drift silently.
  Factor-factory engine fits land as an **appendix** ("Engine audit"), not
  inline in Results.
- **CI is zero-network.** Tests run against cached artifacts; no test makes a
  live HTTP call. Fetching is the user's job at dev time.
- **Examples isolation.** Each example under `examples/` is a self-contained uv
  project. Per-example lockfiles are gitignored — reproducibility lives in each
  example's pinned version ranges in `pyproject.toml`. Publishable jellycell
  outputs (`artifacts/*.json` + `manuscripts/FINDINGS.md`) ARE committed so
  GitHub renders them inline.

## Conventions

- **Imports**: absolute imports in library code
  (`from subway_access.temporal import build_panel_dataset`). Private helpers
  live in underscored modules (`_core.py`, `_base.py`); public surface is the
  subpackage `__init__.py` re-exports.
- **Type hints**: `@dataclass(frozen=True, slots=True)` for all model classes.
  Strict mypy on `src/` + `tests/`. `mypy.overrides` carries
  `ignore_missing_imports = True` for optional extras (`factor_factory.*`,
  `jellycell.*`) so the repo type-checks cleanly whether or not the extras are
  installed.
- **Tests**: pytest-based under `tests/`, layered by module. Tests that depend
  on `factor-factory` / `jellycell` must start with `pytest.importorskip` at the
  top.
- **Docs**: MkDocs Material, served from `docs/`. `make docs` for live preview,
  `make docs-build` for strict CI-equivalent build.

## Dev commands (mirrored in `CLAUDE.md`)

```
make install       # uv sync --all-groups --all-extras
make install-dev   # uv sync (default dev env)
make test          # pytest suite
make lint          # ruff + mypy + public-API audit
make format        # ruff --fix + ruff format
make docs          # mkdocs serve (live preview)
make docs-build    # mkdocs build --strict
make check         # lint + tests (pre-push gate)
make ci            # full local CI-equivalent sequence with summary
```

## Public API surface

Top-level import is intentionally minimal (`__version__` only). Consumers
address the subpackages directly:

| Subpackage                                    | Purpose                                                     |
| :-------------------------------------------- | :---------------------------------------------------------- |
| `subway_access.analysis`                      | Scoring, catchments, gap analysis, reliability              |
| `subway_access.models`                        | Typed, frozen dataclasses for the data model                |
| `subway_access.factors`                       | Zipline-inspired factor pipeline                            |
| `subway_access.temporal`                      | Panel construction, upgrade timelines, spatial weights      |
| `subway_access.io`                            | Snapshot cache I/O + entrance / GTFS loaders                |
| `subway_access.pipeline`                      | High-level orchestration (`fetch_study_area_snapshot`, ...) |
| `subway_access.export`                        | GeoJSON / CSV / markdown writers                            |
| `subway_access.helpers`                       | Multi-borough iteration, CSV export utilities               |
| `subway_access.reporting` _(v0.5+, optional)_ | jellycell tearsheet bridge                                  |
| `subway_access.cli`                           | The `subway-access` console script                          |

Breakages to these surfaces are a **major** version bump; additive changes are
**minor**; bug fixes / docs / internal refactors are **patch**.
`scripts/audit_public_api.py` validates the surface in CI.

## Ecosystem context

`subway-access` is one of three NYC civic-tech OSS projects maintained by
[`random-walks`](https://github.com/random-walks):

- **Upstream**:
  [`nyc-geo-toolkit`](https://github.com/random-walks/nyc-geo-toolkit) —
  geography primitives + tract/borough loaders. Pinned `>=0.3.0,<0.4`.
- **Sibling**: [`nyc311`](https://github.com/random-walks/nyc311) — NYC 311
  complaint / resolution analytics. Independent of `subway-access` but shares
  the `factor-factory` causal-inference layer.
- **Optional integrations**:
  [`factor-factory`](https://github.com/random-walks/factor-factory) for
  causal-inference engines and
  [`jellycell`](https://github.com/random-walks/jellycell) for tearsheet
  rendering, behind the `[factor-factory]` and `[tearsheets]` extras.

## Release workflow

Version is derived from git tags via `hatch-vcs`. Do not hand-edit
`src/subway_access/_version.py`. The flow:

1. `/bump [patch|minor|major]` → rolls the CHANGELOG `[Unreleased]` section into
   a new version block.
2. Human review → `git commit -m "release: v<X.Y.Z>"`.
3. `/release-check` → runs `make ci` + case-study smoke (when cache/ is
   present) + invokes the `release-auditor` agent.
4. `git tag v<X.Y.Z>` + `git push --tags` → the OIDC CD workflow
   (`.github/workflows/cd.yml`) publishes to PyPI on the release event.

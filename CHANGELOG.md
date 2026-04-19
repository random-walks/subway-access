# Changelog

All notable changes to `subway-access` are documented in this file. This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The authoritative release notes are also published on [GitHub Releases](https://github.com/random-walks/subway-access/releases).

## [Unreleased]

### Added

### Changed

### Fixed

### Deprecated

### Security

## [0.5.0] — 2026-04-19

### Added

- Optional `factor-factory>=1.0.2,<2` integration via the new `[factor-factory]` extras group, which pins `factor-factory[did,rdd,scm,spatial]` to pull in the engine-family dependencies (`differences`, `rdrobust`, `esda`, `libpysal`, `spreg`) on demand ([#16](https://github.com/random-walks/subway-access/issues/16)).
- Optional `jellycell>=1.3.5,<2` integration via the new `[tearsheets]` extras group for manuscript-style engine tearsheets.
- `subway_access.reporting` public module with `jellycell_bridge` — lazy-imports jellycell and raises a clear `ImportError` pointing at `pip install subway-access[tearsheets]` when absent.
- Engine-audit appendix in the accessibility case study (`examples/accessibility-change-over-time/CASESTUDY.md`) cross-checking the headline findings with five factor-factory engine fits: `did.twfe`, `did.sa` (Sun-Abraham), `scm.augmented`, `rdd.rd_robust` at the 800 m walk-radius threshold, and `spatial.morans_i` for registry-parity against the existing hand-rolled Moran's *I*.
- New self-contained example `examples/factor-factory-rdd-walkthrough/` — a minimal recipe demonstrating the RDD-at-threshold pattern independent of the full case-study machinery.
- Claude Code infrastructure:
  - `.claude/launch.json`, `.claude/settings.local.json` (extended allowlist).
  - `.claude/agents/release-auditor.md`, `.claude/agents/case-study-reviewer.md`.
  - `.claude/commands/bump.md`, `.claude/commands/release-check.md`, `.claude/commands/run-case-study.md`.
  - `.claude/skills/factor-factory-integration.md`, `.claude/skills/release-bump.md`.
- Top-level `CLAUDE.md` dense one-pager.
- Top-level `CONTRIBUTING.md` wrapper around `docs/contributing.md`.
- `.github/PULL_REQUEST_TEMPLATE.md` with case-study touch checklist.
- `CITATION.cff` for software-record citation.
- `docs/factor-factory-integration.md` walking through the engine-wiring pattern.
- README "Extending with factor-factory" section.

### Changed

- GitHub Actions pin bumps in `ci.yml` + `cd.yml`: `astral-sh/setup-uv` from SHA-pinned v8.0.0 to `v8.1.0` (exact, per factor-factory's learning that v8 has no moving tag), `actions/upload-artifact@v6` to `@v7`. `actions/checkout@v6`, `actions/download-artifact@v8`, `actions/setup-python@v6` already current.
- CI test matrix extended from Ubuntu-only to `ubuntu-latest` + `macos-latest` + `windows-latest` across Python 3.10–3.13.
- `.gitignore`: added `.claude/scheduled_tasks.lock` and jellycell cache manifest paths.

### Fixed

- `mypy.overrides` entries added for `factor_factory.*` and `jellycell.*` so the optional imports in `subway_access.reporting` type-check cleanly when the extras are not installed.

## Prior releases

See [GitHub Releases](https://github.com/random-walks/subway-access/releases) for v0.4.x and earlier.

[unreleased]: https://github.com/random-walks/subway-access/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/random-walks/subway-access/compare/v0.4.1...v0.5.0

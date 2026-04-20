# Contributing to subway-access

Thanks for your interest. This is a small project with a real research artifact
in the repo (the accessibility case study) — the quickest path to a merge is to
understand what's precious and what's flexible.

The full developer guide lives at
[`docs/contributing.md`](docs/contributing.md). This file is a short wrapper
focused on the rules that matter for a first PR.

## Getting set up

```bash
git clone https://github.com/random-walks/subway-access.git
cd subway-access
make install       # uv sync --all-groups --all-extras
make test          # pytest suite
make lint          # ruff + mypy + public-API audit
make docs          # mkdocs serve live preview
```

Editor setup: `ruff` + `mypy` via your IDE's LSP. No other config needed.
Pre-commit hooks: `pre-commit install` picks up `.pre-commit-config.yaml`.

## What we commit to

1. **The public API surface** (re-exported from `subway_access`). Breaking
   changes require a major bump. `scripts/audit_public_api.py` catches removals.
2. **The accessibility case study numbers.**
   `examples/accessibility-change-over-time/reports/accessibility-change-report.md`
   and `CASESTUDY.md` contain real research findings with specific values: 493
   stations / 157 ADA / 101 press-release-sourced + 56 hash-fallback upgrade
   years / 2,317 tracts / OLS R² = .202 / Moran's _I_ = .2271. Don't change
   these silently.
3. **Optional-extras model.** `factor-factory` and `jellycell` are optional. The
   library imports without them. See
   [`.claude/skills/factor-factory-integration.md`](.claude/skills/factor-factory-integration.md).
4. **Zero-network-in-CI policy.** CI runs against cached artifacts. No test may
   make a live HTTP call. Fetching is the user's job at dev time.

## Adding a feature

- New public API → docstring + `docs/api.md` entry +
  `scripts/audit_public_api.py` passes + test.
- New optional dep → new extras group + folded into `[all]` + lazy import at
  call-site + clear error message pointing at the extras group if missing.
- New case-study engine fit → lives in an **appendix** ("Engine audit") of
  `CASESTUDY.md`, not in Sections 4.x. Lazy-imports factor-factory/jellycell. If
  the engine's result disagrees with the headline findings, surface it.
- New example project → own `pyproject.toml` with
  `dependencies = ["subway-access[...]"]`, own `README.md`, own `main.py`,
  tracked `reports/`.

## Extending the case study

The accessibility case study is a research artifact, not just an example. If
your change touches `examples/accessibility-change-over-time/`:

- Read `CASESTUDY.md` first. Treat the Abstract + Sections 3–5 as precious text.
- Append to the engine-audit appendix; don't edit Results Section 4.
- Re-run `main.py --skip-download` and diff
  `reports/accessibility-change-report.md` — the numbers should be unchanged
  unless you explicitly intend to change them, in which case update
  `CASESTUDY.md` prose to match.
- New engine fits → write a short test that runs the engine against a tiny
  fixture panel. Use `pytest.importorskip("factor_factory.engines.<family>")`.

## Pre-merge checklist

Paste this into your PR description:

```
- [ ] `make ci` green locally
- [ ] New public API → docs/api.md entry + audit passes + test
- [ ] New optional extra → folded into [all]
- [ ] Case-study touch → numbers intact OR CHANGELOG notes the delta
- [ ] Factor-factory engine touch → pytest.importorskip + lazy import
- [ ] CHANGELOG [Unreleased] entry written
- [ ] `docs/` touched if user-visible
```

## Commit + PR hygiene

- Conventional-commit subject line: `feat(reporting): ...`, `fix(factors): ...`,
  `docs: ...`, `ci: ...`.
- One concern per PR; bundle a refactor + a behavior change → two PRs.
- If your change adds a factor-factory engine adapter wrapper, link the
  canonical citation (paper DOI or canonical software URL) in the docstring.

## Discussion

Issues and PRs on GitHub. Keep threads async and searchable.

## See also

- [`docs/contributing.md`](docs/contributing.md) — full developer guide (this
  file's wrapper)
- [`CLAUDE.md`](CLAUDE.md) — dense agent-oriented one-pager
- [`.claude/`](.claude/) — slash-commands, skills, agents

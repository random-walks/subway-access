---
name: release-bump
description:
  One-screen rubric for deciding patch vs minor vs major. Triggers when closing
  a PR or about to run /bump.
---

# Release bump rubric

`subway-access` follows a **minimum-bump** policy. Patch bumps are cheap; ship
often.

## Decision tree

```
Did the diff break a public API (removed/renamed a function, class, or module under subway_access.*)?
├── Yes → major
└── No → continue

Did the diff add a new public API, a new CLI subcommand, a new optional extra, or a new example project?
├── Yes → minor
└── No → continue

Is the diff a bug fix, docs edit, internal refactor, dep bump, test addition, CI tweak, or case-study reproducibility fix?
└── Yes → patch
```

## Rules of thumb

- **When in doubt, patch.** You can cut another release tomorrow.
- **The case study is a public artifact.** Changes to
  `examples/accessibility-change-over-time/reports/*` that change reported
  numbers are a **minor** bump (downstream readers may cite them) — pair with a
  CHANGELOG note explaining the numeric delta.
- **Optional-extras additions are minor** (e.g. adding `[factor-factory]`,
  `[tearsheets]`). Removing an extra is major.
- **The `subway_access.factors` API is public** (re-exported from
  `subway_access`). Any break is major.
- **The `subway_access.reporting.jellycell_bridge` API was added in v0.5.0 and
  is public.** Breaking it is major.

## CHANGELOG entry shape

Short. Specific. Link the PR.

```
## [0.5.0] — 2026-04-19

### Added
- Optional factor-factory + jellycell integration (`[factor-factory]`, `[tearsheets]` extras).
  Five engine fits (`rdd.rd_robust`, `scm.augmented`, `spatial.morans_i`, `did.sa`, `did.twfe`)
  emitted as a tearsheet appendix on the accessibility case study (#16).
- Claude Code infrastructure (`.claude/`, `CLAUDE.md`, `CONTRIBUTING.md`).
```

Not:

```
- Added factor-factory stuff
```

## Final step

After `/bump`, review the generated CHANGELOG. Rewrite any thin entries. Then
`git commit` and `git tag`.

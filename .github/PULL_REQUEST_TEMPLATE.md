<!-- subway-access PR template — short, non-bureaucratic. Delete sections that don't apply. -->

## Summary

<!-- 1–3 bullets. What does this PR do and why? -->

## Issue / context

<!-- Closes #<n> if applicable, or a short link to the discussion that motivated this. -->

## Touches the accessibility case study?

<!-- If yes, confirm: -->

- [ ] `reports/accessibility-change-report.md` numbers intact OR intentional
      delta flagged below with an explanation
- [ ] `CASESTUDY.md` narrative preserved (or explicitly updated to match the new
      numbers)
- [ ] Any new engine fit lives in the "Engine audit" appendix, not in Results
      Section 4.x
- [ ] Not applicable

<!-- If numbers changed, list the delta here: -->

## Checklist

- [ ] `make ci` green locally
- [ ] New public API? → docstring + `docs/api.md` entry +
      `scripts/audit_public_api.py` passes
- [ ] New optional-dep extra? → folded into `[all]` + lazy import at call-site +
      clear error pointing at the extras group
- [ ] Factor-factory / jellycell touch? → `pytest.importorskip` in tests, lazy
      import in `src/subway_access/reporting/`
- [ ] CHANGELOG `[Unreleased]` entry written under the right header (Added /
      Changed / Fixed / Deprecated / Security)
- [ ] `docs/` updated if user-visible

## Test plan

<!-- What did you run to convince yourself this works? Cached case-study rerun + pytest is the floor; list any extras. -->

## Citations (for new engine adapters or research prose)

<!-- Paper DOI + upstream package URL -->

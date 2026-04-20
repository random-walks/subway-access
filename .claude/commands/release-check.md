---
description:
  Preflight check before pushing a release tag. Runs `make ci` (lint, build,
  smoke, docs, tests) and invokes the release-auditor agent. Reports the
  verdict.
---

Execute these in order. Stop on first failure; report the offending step.

1. `git status --porcelain` — confirm clean working tree. Fail if dirty.
2. `make ci` — runs lint, build, smoke-dist, docs, tests. Let it finish, capture
   the summary table.
3. `uv run python examples/accessibility-change-over-time/main.py --skip-download`
   — the case study must still run end-to-end against cached artifacts. This is
   an integration smoke test. If
   `examples/accessibility-change-over-time/cache/` does not exist, skip this
   step with a note (a fresh clone has no cache; populating it requires a Census
   Bureau API key + network, which is outside the release-check scope).
4. Invoke the `release-auditor` agent (via Agent tool with
   `subagent_type: release-auditor`) with the target version inferred from the
   latest CHANGELOG heading. Pass through its verdict verbatim.
5. Print a final one-line verdict: `READY to tag v<X.Y.Z>` or
   `NOT READY — <reason>`.

If the case study numbers in `reports/accessibility-change-report.md` changed
after the rerun, stop and surface the diff — do not proceed silently.

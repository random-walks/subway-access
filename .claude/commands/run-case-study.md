---
description:
  Re-run the accessibility case study against cached data. Arg = optional
  `--skip-engine-audit` to disable the factor-factory cross-check step even when
  the `[factor-factory,tearsheets]` extras are installed.
---

Run these in order:

1. Confirm `examples/accessibility-change-over-time/cache/` exists. If it
   doesn't, say so — running without cache requires network + a Census Bureau
   API key, which the user must set up first. Print the relevant `make` targets
   (or the `subway-access fetch-snapshot` CLI) and stop without running the
   pipeline.
2. Run:
   ```
   uv run python examples/accessibility-change-over-time/main.py --skip-download
   ```
   If `$ARGUMENTS` contains `--skip-engine-audit`, pass it through. Otherwise
   let the script auto-detect whether `factor-factory` + `jellycell` are
   installed and run Step 11 (the engine-audit cross-check) conditionally.
3. After the run, print:
   - The diff between `reports/accessibility-change-report.md` before and after
     (via `git diff --stat examples/accessibility-change-over-time/reports/`).
   - A list of newly written files under `reports/figures/` and
     `reports/supplementary/`.
   - If tearsheets were written: the paths under
     `examples/accessibility-change-over-time/engine-audit/manuscripts/` (the
     factor-factory project-dir convention used by Step 11) and
     `engine-audit/artifacts/*_results.json`.
4. If any headline number in the report changed unexpectedly (check the
   "Abstract" paragraph + Section 4 tables + the OLS R² = .202 / Moran's _I_ =
   .2271 invariants guarded by the `case-study-reviewer` agent), flag it — do
   not paper over.

Do NOT run with network unless the user explicitly asks — the cache is
authoritative for reproducibility.

---
description:
  Re-run the accessibility case study against cached data. Arg = optional
  `--with-factor-factory` to also run the engine-audit appendix.
---

Run these in order:

1. Confirm `examples/accessibility-change-over-time/cache/` exists. If it
   doesn't, say so — running without cache requires network + CSU keys, which
   the user must set up first; print the relevant `make` targets and stop.
2. Run:
   ```
   uv run python examples/accessibility-change-over-time/main.py --skip-download
   ```
   If `$ARGUMENTS` contains `--with-factor-factory`, pass it through (the script
   reads it as a flag and runs the engine-audit pass when both `factor-factory`
   and `jellycell` are installed).
3. After the run, print:
   - The diff between `reports/accessibility-change-report.md` before and after
     (via `git diff --stat examples/accessibility-change-over-time/reports/`).
   - A list of newly written files under `reports/figures/` and
     `reports/supplementary/`.
   - If tearsheets were written: the paths under
     `examples/accessibility-change-over-time/casestudy/manuscripts/` (jellycell
     default).
4. If any headline number in the report changed unexpectedly (check the
   "Abstract" paragraph + Section 4 tables), flag it — do not paper over.

Do NOT run with network unless the user explicitly asks — the cache is
authoritative for reproducibility.

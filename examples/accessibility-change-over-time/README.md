<!-- Author: Blaise Albis-Burdige | https://blaiseab.com | Creator of subway-access -->

> **Note from Blaise:** This case study is an example of more advanced statistical analysis using the [subway-access](https://github.com/random-walks/subway-access) library and the NYC open data ecosystem. The central question is almost comical: do accessibility initiatives actually increase equity if the elevator is never running? On a more serious note, the findings highlight a gap in investment follow-through when it comes to ADA infrastructure. Current accessibility classifications may succeed in incentivizing initial capital commitments, but without robust maintenance funding, many stations that are "accessible" on paper are not accessible in practice.

# Accessibility Change Over Time

Research pipeline that analyzes how ADA station upgrades track against neighborhood demographics across all five NYC boroughs.

**[Read the full case study (CASESTUDY.md)](CASESTUDY.md)** for formal methods, APA-formatted results, model diagnostics, and a complete reference list.

---

## TL;DR for researchers

4,717,140 New Yorkers (55.4%) reside in census tracts with no ADA-accessible subway station within 800 m. Only 157 of 493 stations (31.8%) are ADA-accessible (MTA, April 2026). Queens bears the largest absolute gap: 1,752,073 residents at a mean distance of 1,966 m from the nearest accessible station, corroborating Baghestani et al. (2024) who independently identified Queens as the most underserved borough using a gravity-index methodology.

Elevator reliability further erodes nominal coverage. Of the 157 accessible stations, 49 operated below 95% uptime over a 12-month window (May 2025--April 2026). Manhattan's effective tract coverage drops from 77% to 71% under reliability weighting---and Manhattan is the best-performing borough.

An OLS equity regression (*N* = 2,317, *R*² = .202, *F*(3, 2313) = 108.83, *P* < .001) identifies senior population rate as the strongest predictor of gap score (*b* = 0.263, *t* = 15.93, *P* < .001), followed by poverty rate (*b* = 0.164, *t* = 4.99, *P* < .001). Disability rate is not significant when the other two are included (*t* = 0.21, *P* = .84), likely absorbed by its high collinearity with poverty (*r* = .70). Global Moran's *I* confirms significant spatial clustering of gap scores (*I* = .23, *z* = 40.87, *P* < .001), indicating that accessibility deficits concentrate in identifiable geographic corridors rather than distributing randomly.

**Key limitations.** The 800 m Euclidean catchment overstates walking coverage (no street-network routing). ACS 2023 five-year estimates are now three years stale. The DiD panel uses a partially sourced upgrade timeline: 100 of 157 stations (63.7%) have dates traced to MTA press releases, Capital Program records, and news coverage; the remaining 57 use approximate dates because Key Station Program completion records are not publicly available. A FOIL request for the full schedule and an outcome variable (ridership, property values) are needed before strong causal claims can be made. Significant Moran's *I* values mean OLS standard errors are likely underestimated; spatial HAC corrections are recommended.

---

## What this means (plain English)

Two-thirds of NYC subway stations have no elevator or ramp. If you use a wheelchair, push a stroller, or can't do stairs, those stations don't exist for you.

**4.7 million people**---more than the entire population of Los Angeles---live too far from any accessible station to reasonably walk there. Queens is the worst-off borough by far: 1.75 million residents with no accessible station nearby.

It gets worse. Even among the stations that *are* labeled accessible, many have elevators that are broken for weeks or months at a time. Columbus Circle's elevator was down for essentially the entire year. Herald Square---one of the busiest stations in the system---had only 51% uptime. When you account for broken elevators, Manhattan's "77% coverage" drops to 71%, and that's the *best* borough.

The pattern is not random. Neighborhoods with high concentrations of seniors and people living in poverty are disproportionately likely to be in accessibility gap zones. And these gap zones cluster together geographically---entire corridors of the city are systematically underserved, which means targeted investment in those specific corridors would be far more effective than spreading upgrades evenly across the system.

**Bottom line:** labeling a station "accessible" means nothing if the elevator doesn't work. The MTA is spending billions on ADA upgrades, but without matching maintenance investment, those upgrades are a paper promise.

## About this example

This example is part of the [subway-access](https://github.com/random-walks/subway-access) library. It demonstrates:

- **Multi-source data integration** --- MTA station catalog, elevator outage history, ACS demographics, and census tract geometries, all fetched programmatically from public APIs.
- **The `subway_access.factors` pipeline** --- composable factor evaluation (NeedScore, Coverage, GapScore, ReliabilityWeightedCoverage, etc.) over every census tract in a single pass.
- **Temporal panel construction** --- building a balanced tract × year panel dataset for difference-in-differences estimation using `subway_access.temporal`.
- **Spatial analysis** --- distance-based spatial weights, Moran's *I*, and the framework for SAR panel models via `libpysal`.
- **Auto-generated reporting** --- the pipeline produces a full markdown report with 15 figures, 6 tables, and 3 supplementary analyses.

### Project structure

```
accessibility-change-over-time/
├── main.py                        # Entry point --- run this
├── CASESTUDY.md                   # Formal case study (APA style)
├── README.md                      # You are here
├── reports/
│   ├── accessibility-change-report.md   # Auto-generated report
│   ├── figures/                         # All 15 figures (PNG)
│   └── supplementary/
│       ├── correlation-analysis.md      # Pearson/Spearman, VIF, OLS
│       ├── model-specification.md       # DiD/SAR equations, balance tests
│       └── spatial-diagnostics.md       # Moran's I, weights summary
├── artifacts/
│   ├── panel-dataset.csv          # 16,219 tract × year observations
│   └── borough-summary.csv       # Borough-level summary stats
├── casestudy/
│   ├── sections/                  # Case study source sections (00--07)
│   └── combine.sh                # Assembles CASESTUDY.md from sections
└── cache/                         # Cached API responses (gitignored)
```

## Reproducing the analysis

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/)

```bash
# Install dependencies
uv sync

# Run the full pipeline (fetches live data from MTA + Census APIs)
python main.py

# Subset to specific boroughs
python main.py --boroughs Manhattan,Brooklyn

# Reuse cached data (skip API calls)
python main.py --skip-download

# Generate CSVs only, skip figures and report
python main.py --no-publish-report
```

Running `python main.py` regenerates all figures, tables, artifacts, and the auto-generated report from live API data. Cached responses in `cache/` can be reused with `--skip-download` for faster iteration.

### Output artifacts

| Path | Description |
| :--- | :--- |
| `reports/accessibility-change-report.md` | Auto-generated report (15 figures, 6 tables) |
| `reports/supplementary/*.md` | Correlation, model spec, and spatial diagnostics |
| `artifacts/panel-dataset.csv` | Geographic panel dataset (2,317 tracts × 7 periods) |
| `artifacts/borough-summary.csv` | Borough-level summary statistics |
| `reports/figures/figure-{1..15}-*.png` | All figures |

### Rebuilding the case study

The formal case study is assembled from modular sections:

```bash
bash casestudy/combine.sh   # Combines sections/00-07 into CASESTUDY.md
```

## Further reading

- **[Full case study](CASESTUDY.md)** --- formal APA-style write-up with abstract, literature review, methods, results, discussion, and references.
- **[Auto-generated report](reports/accessibility-change-report.md)** --- all tables and figures with brief interpretation.
- **[Correlation analysis](reports/supplementary/correlation-analysis.md)** --- Pearson/Spearman matrices, VIF, OLS equity regression.
- **[Model specification](reports/supplementary/model-specification.md)** --- DiD and SAR panel equations, identifying assumptions, balance tests.
- **[Spatial diagnostics](reports/supplementary/spatial-diagnostics.md)** --- Moran's *I*, spatial weights, clustering interpretation.

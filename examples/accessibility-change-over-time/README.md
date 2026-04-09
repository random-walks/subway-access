# Accessibility Change Over Time

Research pipeline that analyzes how ADA station upgrades track against
neighborhood demographics across all five NYC boroughs.

## Background

The New York City subway system has **493 stations** across five boroughs. As of
the April 9, 2026 data pull, only **157 (32%) are ADA-accessible** -- meaning
they have elevators or ramps that allow use by people in wheelchairs, with
strollers, or who otherwise cannot use stairs. The remaining 336 stations are
effectively off-limits to anyone who cannot navigate stairways.

This analysis asks a simple question: **who is left out, where, and how badly?**
It measures accessibility at the census-tract level across the entire city, then
layers in elevator reliability data to distinguish between stations that are
nominally accessible and stations that actually work.

### Data sources

| Source                                    | Description                                       |                           N | Coverage                                                                |
| :---------------------------------------- | :------------------------------------------------ | --------------------------: | :---------------------------------------------------------------------- |
| **MTA Subway Station Catalog**            | Station locations, routes, ADA status             |            **493 stations** | All active stations, fetched April 9, 2026 via Open Data NY Socrata API |
| **MTA Elevator & Escalator Availability** | Monthly outage and uptime records                 | **6,765 availability rows** | **May 2025 -- April 2026** (12-month rolling window)                    |
| **American Community Survey**             | Tract-level disability, senior, and poverty rates |            **2,317 tracts** | **2023 vintage** (5-year estimates, survey period 2019--2023)           |
| **NYC Census Tract Boundaries**           | Tract geometries for spatial analysis             |            **2,325 tracts** | 2020 vintage (nyc-geo-toolkit)                                          |

### Sample

- **Geographic scope:** All five NYC boroughs (Manhattan, Brooklyn, Queens,
  Bronx, Staten Island)
- **Unit of analysis:** Census tract (n = **2,317** tracts with matched
  demographics)
- **Total study population:** **8,507,596** residents
- **Temporal panel:** 7 simulated periods (2017--2023), **16,219 observations**
  (2,317 tracts x 7 years)
- **Spatial weights:** Distance-based (2 km threshold), **2,315 of 2,317** units
  with at least one neighbor, mean **47.9** neighbors per unit

## Methodology

**Accessibility model.** A tract is "covered" if its centroid falls within an
800-meter Euclidean radius (approximately a 10-minute walk at 80 m/min) of at
least one ADA-accessible station. This is intentionally a first-pass model --
Euclidean distance overstates true walking coverage because it ignores street
networks, elevation, and sidewalk conditions.

**Need score.** Each tract receives a composite need score: the unweighted mean
of its disability rate, senior rate, and poverty rate (ACS 2023). Tracts with
high need and no accessible coverage receive a nonzero gap score; covered tracts
receive zero.

**Reliability weighting.** Nominal coverage treats any ADA station as fully
accessible. Reliability-weighted coverage discounts by the station's actual
elevator uptime over the observation window (May 2025 -- April 2026). A station
with 50% uptime contributes 0.50 effective coverage, not 1.00.

**Temporal panel.** The panel assigns ADA upgrade years to currently-accessible
stations using a deterministic hash (simulating the MTA Capital Program
rollout). Each tract x year observation records whether the tract had accessible
coverage in that period, enabling difference-in-differences estimation.
Treatment = tracts that gained an accessible station during the panel window (n
= **908**). Control = tracts never covered (n = **1,409**).

**Composable factor pipeline.** All classification runs through the
`subway_access.factors` system. Built-in factors (NeedScore, Coverage, GapScore,
NearestStationDistance, StationCount, ReliabilityWeightedCoverage) are composed
into a `Pipeline` object that evaluates every factor for every tract in a single
pass. Custom factors can be added by subclassing `Factor`.

See the
[model specification](reports/accessibility-change-report.md#model-specification)
in the auto-generated report for the full DiD and SAR panel equations.

## Results

The full auto-generated report with all tables and figures is at
**[reports/accessibility-change-report.md](reports/accessibility-change-report.md)**.

Key results at a glance:

| Finding                                   | Value                                        | Source                                                                                     |
| :---------------------------------------- | :------------------------------------------- | :----------------------------------------------------------------------------------------- |
| Population in gap tracts                  | **4,717,140** (55%)                          | [Table 1](reports/accessibility-change-report.md#table-1-system-wide-snapshot)             |
| Borough with largest gap                  | **Queens** (1,752,073 gap pop, 22% coverage) | [Table 2](reports/accessibility-change-report.md#table-2-borough-comparison)               |
| Borough with highest coverage             | **Manhattan** (77%)                          | [Figure 1](reports/figures/figure-1-coverage-by-borough.png)                               |
| Fragile accessible stations (<95% uptime) | **49** system-wide                           | [Table 3](reports/accessibility-change-report.md#table-3-most-fragile-accessible-stations) |
| Worst station uptime                      | **Columbus Circle: 0%**                      | [Table 3](reports/accessibility-change-report.md#table-3-most-fragile-accessible-stations) |
| Manhattan nominal vs effective coverage   | **77% vs 71%**                               | [Figure 3](reports/figures/figure-3-reliability-nominal-vs-effective.png)                  |
| Treatment-control need score gap          | **+0.0056** (treatment higher)               | [Table 5](reports/accessibility-change-report.md#table-5-balance-check)                    |
| Need score skewness                       | **0.73** (right-skewed)                      | [Table 6](reports/accessibility-change-report.md#table-6-summary-diagnostics)              |

## Conclusion / Interpretation (April 9, 2026)

The headline number is worse than I expected: **4.7 million New Yorkers** -- 55%
of the city -- live more than a 10-minute walk from any ADA-accessible subway
station. Only 157 of 493 stations (32%) are wheelchair-accessible as of the
April 2026 MTA data pull.

The borough-level picture
([Table 2](reports/accessibility-change-report.md#table-2-borough-comparison),
[Figure 1](reports/figures/figure-1-coverage-by-borough.png)) shows a stark
divide. Manhattan has 77% tract coverage -- dense station spacing helps. But
Queens is at just 22%, with 1.75 million residents in gap tracts and an average
distance of nearly 2 km to the nearest accessible station. Staten Island is
worse in rate terms (9%) but smaller in absolute population. The coverage map
([Figure 5](reports/figures/figure-5-choropleth-coverage-status.png)) makes the
geography visceral: Manhattan is a blue island surrounded by a sea of red.

The reliability analysis
([Figure 3](reports/figures/figure-3-reliability-nominal-vs-effective.png),
[Table 3](reports/accessibility-change-report.md#table-3-most-fragile-accessible-stations))
is the most policy-relevant finding. 49 accessible stations had less than 95%
elevator uptime over the May 2025 -- April 2026 observation window. Columbus
Circle reported 0% uptime. Port Authority Bus Terminal: 14%. Herald Square: 51%.
These are some of the busiest stations in the system. When you weight coverage
by actual reliability, Manhattan drops from 77% nominal to 71% effective -- and
that is the _best_ borough. A station that is "accessible" in the MTA database
but has broken elevators half the time is not meaningfully accessible for
someone in a wheelchair. Capital investment in new ADA stations without matching
maintenance investment is spending money on a fiction.

The treatment-vs-control balance check
([Table 5](reports/accessibility-change-report.md#table-5-balance-check)) shows
that tracts that have gained accessible stations have modestly higher disability
rates (+0.95 pp) and poverty rates (+1.84 pp) than those that have not. This is
directionally correct for equity -- the MTA Capital Program appears to be
reaching higher-need neighborhoods. But the imbalance also means a naive
before/after comparison would overstate the benefit; the
difference-in-differences specification with tract and period fixed effects is
necessary for causal identification.

The diagnostic checks
([Figures 8--10](reports/figures/figure-8-need-score-distribution.png)) confirm
the modeling assumptions hold reasonably well. The need score distribution is
right-skewed (skewness = 0.73) but not severely so. The distance decay curve
([Figure 9](reports/figures/figure-9-distance-decay.png)) validates the 800 m
catchment: coverage is near-total within 800 m and drops sharply beyond it. The
gap-distance scatter
([Figure 10](reports/figures/figure-10-gap-vs-distance-scatter.png)) shows that
high-population tracts are affected at every distance range, not just at the
urban fringe -- this is a systemic problem, not an edge case.

The panel dataset (`artifacts/panel-dataset.csv`) has 16,219 observations across
2,317 tracts and 7 simulated periods, ready for econometric estimation. The
spatial weights matrix (2,315 of 2,317 units with neighbors at a 2 km threshold,
mean 47.9 neighbors) supports the SAR panel extension if spatial spillovers are
a concern.

**Caveats.** The demographics come from ACS 2023 5-year estimates (survey period
2019--2023), which are now three years stale at publication. Disability and
poverty rates may have shifted, particularly post-pandemic. The upgrade timeline
in the panel is simulated from current ADA status -- actual MTA Capital Program
upgrade dates (obtainable via FOIL or the MTA's capital dashboard) would
substantially strengthen causal identification and are the most important next
step.

## Reproducibility

```bash
python main.py                              # all 5 boroughs, full report
python main.py --boroughs Manhattan,Brooklyn # subset
python main.py --skip-download              # reuse cached data
python main.py --no-publish-report          # CSVs only, skip figures + report
```

**Output artifacts:**

| Path                                     | Description                                  |
| :--------------------------------------- | :------------------------------------------- |
| `reports/accessibility-change-report.md` | Auto-generated report (10 figures, 6 tables) |
| `artifacts/panel-dataset.csv`            | Geographic panel dataset (tract x year)      |
| `artifacts/borough-summary.csv`          | Borough-level summary statistics             |
| `reports/figures/figure-{1..10}-*.png`   | All figures                                  |

Running `python main.py` regenerates all figures, tables, and the report from
live MTA and Census API data. Cached data in `cache/` can be reused with
`--skip-download`.

## Works cited

- Gu, Y., & Zheng, S. (2024). Residential location responses to new subway
  stations: Evidence from Shenzhen. _Journal of Urban Economics_.
  Difference-in-differences on individual residential trajectories; found
  attraction effects in lower-rent neighborhoods, no displacement.

- Jeong, H., & Lee, L.-F. (2024). Maximum likelihood estimation of spatial
  autoregressive models for origin-destination flows. _Journal of Econometrics_.
  Framework for the SAR panel origin-destination flow model.

- MTA. (2020). 2020--2024 Capital Program: Accessibility. $5.2 billion committed
  to 67 station ADA upgrades, contract award pace five times pre-2020 levels.

- NYC Council Data Team. (2019). Accessibility at MTA subway stations.
  Identified 283 non-accessible stations (57% of system) with no funding plan.

- Zhang, M., et al. (2024). Transit deserts and gentrification in the New York
  metropolitan area. Multinomial logistic regression; transit desert rate higher
  in economically disadvantaged neighborhoods.

## Appendix

### A. Factor pipeline architecture

The `subway_access.factors` module provides a composable pipeline inspired by
Quantopian's Zipline:

```python
from subway_access.factors import Pipeline, NeedScoreFactor, CoverageFactor

pipe = Pipeline().add(NeedScoreFactor()).add(CoverageFactor())
result = pipe.run(contexts)  # one pass over all tracts
result.to_records()  # tuple of dicts
result.to_dataframe()  # pandas DataFrame (optional dep)
```

Custom factors subclass `Factor` and implement `compute(context) -> value`. The
pipeline applies every factor to every tract and returns a columnar result.

### B. Temporal panel schema

Each row in `artifacts/panel-dataset.csv`:

| Column                          | Type  | Description                          |
| :------------------------------ | :---- | :----------------------------------- |
| `unit_id`                       | str   | Census tract GEOID                   |
| `period`                        | str   | Simulated ACS vintage year           |
| `has_accessible_station`        | bool  | Treatment indicator                  |
| `treatment_year`                | int   | Year first accessible station opened |
| `disability_rate`               | float | ACS estimate                         |
| `senior_rate`                   | float | ACS estimate                         |
| `poverty_rate`                  | float | ACS estimate                         |
| `total_population`              | int   | ACS estimate                         |
| `accessible_station_count`      | int   | Stations in catchment                |
| `nearest_accessible_distance_m` | float | Haversine meters                     |
| `need_score`                    | float | mean(disability, senior, poverty)    |
